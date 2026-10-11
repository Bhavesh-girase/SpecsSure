import logging
from typing import Dict, Any
from app.orchestrator.state import AnalysisState
from app.orchestrator.nodes._context import get_db_session
from app.services.retrieval_service import retrieval_service
from app.services.reranker_service import reranker_service
from app.config import settings

logger = logging.getLogger(__name__)

async def retrieve_standards(state: AnalysisState) -> Dict[str, Any]:
    """
    Node 2: Hybrid Retrieval (Dense + BM25 with Reciprocal Rank Fusion) and Cross-Encoder Reranking.
    """
    db = get_db_session()
    
    # Check if this is a reformulated query retry
    if state.get("needs_requery") and state.get("requery_text"):
        query = state["requery_text"]
    else:
        # Build comprehensive retrieval query
        parts = []
        if state.get("product_identity"):
            parts.append(state["product_identity"])
        if state.get("application"):
            parts.append(state["application"])
        if state.get("mentioned_standards"):
            parts.extend(state["mentioned_standards"])
            
        # Add key requirement terms
        reqs = state.get("extracted_requirements", [])
        for r in reqs[:5]:
            p = r.get("parameter", "")
            v = r.get("value", "")
            u = r.get("unit", "") or ""
            parts.append(f"{p} {v} {u}".strip())
            
        # Also include initial processed text snippet
        clean_snippet = state.get("processed_text", "")[:300]
        parts.append(clean_snippet)
        
        query = " ".join(parts)

    logger.info(f"Executing hybrid retrieval for query: {query[:100]}...")
    
    # 1. Hybrid retrieve candidates (top 50)
    hybrid_candidates = await retrieval_service.hybrid_retrieve(
        query=query, 
        db=db, 
        top_k=settings.TOP_K_DENSE
    )
    
    # 2. Cross-encoder rerank candidates (top 10)
    reranked = reranker_service.rerank(
        query=query,
        candidates=hybrid_candidates,
        top_k=settings.TOP_K_RERANK
    )
    
    # 3. Metadata filtering (status / provenance aware): historical editions and foreign standards are
    #    demoted unless the user explicitly cited them, and only the best edition per family is kept.
    from app.engine.std_refs import parse_citations, family_of, base_number
    cited = {r.family for r in parse_citations(query)} | {base_number(r.family) for r in parse_citations(query)}
    adjusted, best_by_family = [], {}
    for std, score in reranked:
        fam = family_of(std.is_number)
        status = std.status.value if hasattr(std.status, "value") else str(std.status)
        explicitly = fam in cited or base_number(fam) in cited
        if status in ("superseded", "withdrawn") and not explicitly:
            score *= 0.4
        if (std.division_code or "").startswith("Foreign") and not explicitly:
            score *= 0.5
        if fam not in best_by_family or score > best_by_family[fam][1]:
            best_by_family[fam] = (std, score)
    reranked = sorted(best_by_family.values(), key=lambda x: x[1], reverse=True)

    # Calculate confidence score based on top score and margin
    top_score = reranked[0][1] if reranked else 0.0
    second_score = reranked[1][1] if len(reranked) > 1 else 0.0
    confidence = float(top_score * 0.7 + (top_score - second_score) * 0.3)
    confidence = max(0.0, min(1.0, confidence))

    components = await retrieval_service.hybrid_retrieve_detailed(query=query, db=db, top_k=settings.TOP_K_DENSE)
    for std, rr in reranked:
        components.setdefault(std.id, {"semantic": 0.0, "keyword": 0.0})["rerank"] = float(rr)
    return {
        "candidate_standards": reranked,
        "retrieval_confidence": confidence,
        "retrieval_components": components,
        "retrieval_query": query,
    }
