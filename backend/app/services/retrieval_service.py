import logging
from typing import List, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import numpy as np

from app.models.standard import Standard, StandardStatus
from app.services.embedding_service import embedding_service
from app.config import settings

logger = logging.getLogger(__name__)

class RetrievalService:
    @staticmethod
    async def dense_retrieve(
        query: str, 
        db: AsyncSession, 
        top_k: int = 50
    ) -> List[Tuple[Standard, float]]:
        """
        Retrieves top_k standards based on dense vector cosine similarity.
        Uses pgvector distance in Postgres or in-memory cosine fallback.
        """
        query_vector = embedding_service.embed_query(query)
        
        # Try native pgvector query first
        try:
            # pgvector cosine distance operator is <=>
            stmt = (
                select(Standard, Standard.embedding.cosine_distance(query_vector).label("distance"))
                .where(Standard.embedding.isnot(None))
                .order_by("distance")
                .limit(top_k)
            )
            result = await db.execute(stmt)
            rows = result.all()
            # Convert cosine distance to cosine similarity: sim = 1 - distance
            return [(row[0], float(1.0 - (row[1] if row[1] is not None else 1.0))) for row in rows]
        except Exception as e:
            logger.debug(f"pgvector query fell back to in-memory cosine comparison: {e}")
            
            # Fallback: load all standards and calculate cosine similarity in python
            stmt = select(Standard)
            result = await db.execute(stmt)
            all_standards = result.scalars().all()
            
            scored_standards = []
            q_vec = np.array(query_vector, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)
            if q_norm == 0:
                q_norm = 1.0

            for std in all_standards:
                if std.embedding is not None:
                    try:
                        emb = np.array(std.embedding, dtype=np.float32)
                        emb_norm = np.linalg.norm(emb)
                        if emb_norm > 0:
                            sim = float(np.dot(q_vec, emb) / (q_norm * emb_norm))
                        else:
                            sim = 0.0
                    except Exception:
                        sim = 0.0
                else:
                    # Basic token overlap if no embedding exists yet
                    words_q = set(query.lower().split())
                    words_std = set((f"{std.is_number} {std.title} {std.scope or ''}").lower().split())
                    sim = len(words_q.intersection(words_std)) / max(len(words_q), 1) * 0.5
                    
                scored_standards.append((std, sim))
                
            scored_standards.sort(key=lambda x: x[1], reverse=True)
            return scored_standards[:top_k]

    @staticmethod
    async def bm25_retrieve(
        query: str, 
        db: AsyncSession, 
        top_k: int = 50
    ) -> List[Tuple[Standard, float]]:
        """
        Retrieves top_k standards based on BM25 keyword matching.
        Uses rank_bm25 or SQL search_text ilike / full text.
        """
        stmt = select(Standard)
        result = await db.execute(stmt)
        all_standards = result.scalars().all()
        
        if not all_standards:
            return []

        # Use rank_bm25 over the standards corpus
        try:
            from rank_bm25 import BM25Okapi
            corpus = [
                (f"{std.is_number} {std.title} {std.scope or ''} {std.division_code or ''} {std.section_committee or ''}").lower().split()
                for std in all_standards
            ]
            bm25 = BM25Okapi(corpus)
            tokenized_query = query.lower().split()
            scores = bm25.get_scores(tokenized_query)
            
            max_score = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0
            
            scored_results = [
                (all_standards[i], float(scores[i] / max_score))
                for i in range(len(all_standards))
                if scores[i] > 0
            ]
            scored_results.sort(key=lambda x: x[1], reverse=True)
            return scored_results[:top_k]
        except Exception as e:
            logger.warning(f"rank_bm25 fallback error: {e}")
            # Fallback simple keyword scoring
            scored = []
            tokens = [t.lower() for t in query.split() if len(t) > 2]
            for std in all_standards:
                text_blob = f"{std.is_number} {std.title} {std.scope or ''}".lower()
                matches = sum(1 for t in tokens if t in text_blob)
                score = matches / max(len(tokens), 1)
                if score > 0:
                    scored.append((std, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]

    @classmethod
    async def hybrid_retrieve(
        cls, 
        query: str, 
        db: AsyncSession, 
        top_k: int = 50,
        dense_weight: float = 0.6,
        bm25_weight: float = 0.4
    ) -> List[Tuple[Standard, float]]:
        """
        Fuses dense semantic search and BM25 keyword search using Reciprocal Rank Fusion (RRF).
        Formula: rrf_score = sum(weight / (k + rank_i)), k=60
        """
        dense_results = await cls.dense_retrieve(query, db, top_k=top_k)
        bm25_results = await cls.bm25_retrieve(query, db, top_k=top_k)
        
        rrf_scores: Dict[int, float] = {}
        standards_map: Dict[int, Standard] = {}
        k = 60.0

        # Dense ranks
        for rank, (std, _) in enumerate(dense_results):
            standards_map[std.id] = std
            rrf_scores[std.id] = rrf_scores.get(std.id, 0.0) + (dense_weight / (k + rank + 1))

        # BM25 ranks
        for rank, (std, _) in enumerate(bm25_results):
            standards_map[std.id] = std
            rrf_scores[std.id] = rrf_scores.get(std.id, 0.0) + (bm25_weight / (k + rank + 1))

        # Normalize scores to 0.0 - 1.0 range
        if rrf_scores:
            max_score = max(rrf_scores.values()) if max(rrf_scores.values()) > 0 else 1.0
            sorted_fused = sorted(
                [(standards_map[std_id], float(score / max_score)) for std_id, score in rrf_scores.items()],
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_fused[:top_k]
        return []

    @classmethod
    async def hybrid_retrieve_detailed(cls, query: str, db: AsyncSession, top_k: int = 50) -> Dict[int, Dict[str, float]]:
        """Per-standard component scores (dense cosine similarity, normalised BM25) used for the provenance formula."""
        dense = await cls.dense_retrieve(query, db, top_k=top_k)
        sparse = await cls.bm25_retrieve(query, db, top_k=top_k)
        comp: Dict[int, Dict[str, float]] = {}
        for std, sc in dense:
            comp.setdefault(std.id, {"semantic": 0.0, "keyword": 0.0})["semantic"] = max(0.0, min(1.0, float(sc)))
        for std, sc in sparse:
            comp.setdefault(std.id, {"semantic": 0.0, "keyword": 0.0})["keyword"] = max(0.0, min(1.0, float(sc)))
        return comp

retrieval_service = RetrievalService()
