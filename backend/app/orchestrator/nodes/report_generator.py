import time
import uuid
import json
import logging
from typing import Dict, Any, List

from sqlalchemy import select

from app.orchestrator.state import AnalysisState
from app.orchestrator.nodes._context import get_db_session
from app.models.requirement import AnalysisResult, StandardRelation
from app.models.amendment import Amendment
from app.services.llm_service import llm_service
from app.engine import ontology
from app.engine.std_refs import family_of, base_number

logger = logging.getLogger(__name__)

W_SEM, W_KW, W_DOM, W_GRAPH = 0.40, 0.25, 0.20, 0.15
ABSTAIN_BELOW = 0.35


async def generate_final_report(state: AnalysisState) -> Dict[str, Any]:
    """
    Node 7: Deterministic provenance scoring (every number below is computed, none are constants),
    optional LLM prose polish constrained to the trace, abstention on weak evidence, persistence.
    """
    db = get_db_session()
    start_time = state.get("processing_time_seconds", time.time())
    validated = state.get("validated_standards", [])
    query = state.get("processed_text", "") or state.get("input_text", "")
    comps: Dict[int, Dict[str, float]] = state.get("retrieval_components", {}) or {}
    mentioned = {family_of(m) for m in state.get("mentioned_standards", [])} | {base_number(family_of(m)) for m in state.get("mentioned_standards", [])}
    query_domains = set(ontology.detect_domains(f"{state.get('product_identity', '')} {query}"))
    validated_ids = {s.id for s in validated}

    rels = []
    if validated_ids:
        rels = (await db.execute(select(StandardRelation).where(
            (StandardRelation.from_standard_id.in_(validated_ids)) | (StandardRelation.to_standard_id.in_(validated_ids))))).scalars().all()

    recommended: List[Dict[str, Any]] = []
    for std in validated:
        amendments = (await db.execute(select(Amendment).where(Amendment.standard_id == std.id).order_by(Amendment.amendment_number))).scalars().all()
        amendments_data = [{"id": a.id, "amendment_number": a.amendment_number, "title": a.title,
                            "published_at": a.published_at.isoformat() if a.published_at else None, "summary": a.summary} for a in amendments]
        c = comps.get(std.id, {})
        semantic = round(float(c.get("semantic", 0.0)), 3)
        keyword = round(float(c.get("keyword", 0.0)), 3)
        std_domains = set(ontology.detect_domains(f"{std.title} {std.scope or ''}"))
        domain = 1.0 if (query_domains & std_domains) else (0.5 if not query_domains or not std_domains else 0.1)
        fam = family_of(std.is_number)
        linked = [r for r in rels if (r.from_standard_id == std.id and r.to_standard_id in validated_ids) or
                  (r.to_standard_id == std.id and r.from_standard_id in validated_ids)]
        if fam in mentioned or base_number(fam) in mentioned:
            graph = 1.0
        elif linked:
            graph = 0.7
        else:
            graph = 0.3
        final = round(W_SEM * semantic + W_KW * keyword + W_DOM * domain + W_GRAPH * graph, 3)
        status = std.status.value if hasattr(std.status, "value") else str(std.status)
        trace = [
            f"Dense semantic similarity (cosine) = {semantic:.3f}",
            f"BM25 keyword score (normalised) = {keyword:.3f}",
            f"Domain match = {domain:.2f} (query domains {sorted(query_domains) or '—'}; standard domains {sorted(std_domains) or '—'})",
            f"Graph evidence = {graph:.2f} ({'explicitly cited in the input' if graph == 1.0 else ('linked to ' + str(len(linked)) + ' other recommended standard(s)' if linked else 'no graph link')})",
            f"Registry status: {status}; {len(amendments)} amendment(s) on record",
            f"Cross-encoder rerank score = {c.get('rerank', 0.0):.3f}",
        ]
        nl = await llm_service.generate_recommendation_explanation(query=query[:200], is_number=std.is_number, title=std.title, evidence_points=trace)
        audit = [{"source_type": "bis_catalog_record", "reference": f"Registry record {std.is_number}", "trust_level": "evidence_backed",
                  "direct_url": std.source_url or "https://standards.bis.gov.in"}]
        explanation = {
            "is_number": std.is_number, "title": std.title, "semantic_score": semantic, "keyword_score": keyword,
            "domain_score": domain, "graph_score": graph, "final_applicability_score": final,
            "score_formula_note": "Engineering weights (0.40·semantic + 0.25·keyword + 0.20·domain + 0.15·graph), computed per standard. Decision-support metric, not an official BIS determination.",
            "auditable_trace": trace, "natural_language_summary": nl, "source_evidence": audit,
        }
        recommended.append({
            "id": std.id, "is_number": std.is_number, "title": std.title, "scope": std.scope, "status": status,
            "relevance_score": final, "relevance_reason": nl, "relationship_to_query": "primary_standard",
            "latest_edition": std.edition or "Latest Revision", "amendments": amendments_data, "superseded_by": std.superseded_by,
            "evidence": audit, "explanation": explanation,
        })
    recommended.sort(key=lambda r: -r["relevance_score"])
    top = recommended[0]["relevance_score"] if recommended else 0.0
    abstained = top < ABSTAIN_BELOW
    total_time = round(time.time() - start_time, 2)
    analysis_id = str(uuid.uuid4())
    try:
        db.add(AnalysisResult(
            analysis_uid=analysis_id, input_text=state.get("input_text", ""), input_language=state.get("detected_language", "en"),
            input_filename=state.get("input_filename"), extracted_requirements=state.get("extracted_requirements", []),
            recommended_standards=recommended, allied_standards=state.get("allied_standards", []), spec_health=state.get("spec_health", {}),
            graph_data=state.get("graph_data", {}), certification_info=state.get("certification_info", []),
            full_report=json.dumps({"analysis_id": analysis_id, "abstained": abstained, "retrieval_confidence": state.get("retrieval_confidence")}),
        ))
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to persist analysis record: {e}")
        await db.rollback()
    return {"analysis_id": analysis_id, "recommended_standards": recommended, "processing_time_seconds": total_time,
            "abstained": abstained}
