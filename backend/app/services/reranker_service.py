import logging
from typing import List, Tuple
from app.models.standard import Standard
from app.config import settings

logger = logging.getLogger(__name__)

class RerankerService:
    _instance = None
    _reranker = None
    _tried = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RerankerService, cls).__new__(cls)
        return cls._instance

    def _get_reranker(self):
        if self._reranker is None and not self._tried:
            self._tried = True
            if settings.RERANKER_MODEL.lower() in ("none", "off", ""):
                return None
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading CrossEncoder reranker: {settings.RERANKER_MODEL}")
                self._reranker = CrossEncoder(settings.RERANKER_MODEL)
                logger.info("CrossEncoder reranker loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not load CrossEncoder reranker ({settings.RERANKER_MODEL}): {e}. Using lightweight scoring fallback.")
                self._reranker = None
        return self._reranker

    def rerank(
        self, 
        query: str, 
        candidates: List[Tuple[Standard, float]], 
        top_k: int = 10
    ) -> List[Tuple[Standard, float]]:
        """
        Reranks retrieved candidate standards using cross-encoder scoring.
        doc_text = '{is_number} - {title} - {scope[:300]}'
        """
        if not candidates:
            return []
        
        reranker = self._get_reranker()
        if reranker is not None:
            try:
                pairs = [
                    (
                        query,
                        f"{std.is_number} - {std.title} - {(std.scope or '')[:300]}"
                    )
                    for std, _ in candidates
                ]
                scores = reranker.predict(pairs)
                
                # Apply sigmoid or min-max normalization if logits
                min_s, max_s = min(scores), max(scores)
                norm_scores = []
                for s in scores:
                    if max_s > min_s:
                        norm_scores.append((s - min_s) / (max_s - min_s))
                    else:
                        norm_scores.append(1.0)

                scored_candidates = [
                    (candidates[i][0], float(norm_scores[i]))
                    for i in range(len(candidates))
                ]
                scored_candidates.sort(key=lambda x: x[1], reverse=True)
                return scored_candidates[:top_k]
            except Exception as e:
                logger.error(f"Error during cross-encoder rerank: {e}")

        # Fallback: combine initial candidate retrieval score with query token overlap boost
        q_tokens = set(query.lower().split())
        rescored = []
        for std, init_score in candidates:
            text_str = f"{std.is_number} {std.title} {std.scope or ''}".lower()
            token_matches = sum(1 for tok in q_tokens if tok in text_str)
            token_ratio = token_matches / max(len(q_tokens), 1)
            # 60% initial score + 40% exact token ratio
            combined = (init_score * 0.6) + (token_ratio * 0.4)
            rescored.append((std, float(min(1.0, combined))))
            
        rescored.sort(key=lambda x: x[1], reverse=True)
        return rescored[:top_k]

reranker_service = RerankerService()
