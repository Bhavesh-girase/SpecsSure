from fastapi import APIRouter, Depends, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
import time

from app.db.session import get_db
from app.services.retrieval_service import retrieval_service
from app.services.reranker_service import reranker_service
from app.schemas.analysis import QuickSearchResponse, RecommendedStandard
from app.schemas.standard import AmendmentRead

router = APIRouter()

@router.post("/search", response_model=QuickSearchResponse, summary="Semantic & hybrid standards search")
async def search_standards(
    query: str = Body(..., embed=True, description="Natural language search query or standard code"),
    top_k: int = Body(10, embed=True, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Direct semantic + BM25 hybrid search with cross-encoder reranking.
    Ideal for search bars and quick lookups.
    """
    start_time = time.time()
    
    # 1. Hybrid retrieve
    candidates = await retrieval_service.hybrid_retrieve(query=query, db=db, top_k=top_k * 2)
    
    # 2. Rerank
    reranked = reranker_service.rerank(query=query, candidates=candidates, top_k=top_k)
    
    results: List[RecommendedStandard] = []
    for std, score in reranked:
        results.append(RecommendedStandard(
            id=std.id,
            is_number=std.is_number,
            title=std.title,
            scope=std.scope,
            status=std.status.value if hasattr(std.status, "value") else str(std.status),
            relevance_score=round(score, 3),
            relevance_reason=f"Matched on semantic context and technical scope with relevance score {score:.2f}.",
            relationship_to_query="direct_product_match",
            latest_edition=std.edition,
            amendments=[],
            superseded_by=std.superseded_by,
            evidence=[]
        ))

    return QuickSearchResponse(
        query=query,
        results=results,
        total_found=len(results),
        processing_time_seconds=round(time.time() - start_time, 3)
    )
