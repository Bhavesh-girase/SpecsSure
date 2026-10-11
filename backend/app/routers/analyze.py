import time
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List

from app.db.session import get_db
from app.models.requirement import AnalysisResult
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    QuickSearchResponse,
    RecommendedStandard,
    AlliedStandard,
    CertificationInfo,
    SpecHealth,
    SpecGap,
    GraphData,
    ExtractedRequirement
)
from app.services.document_parser import extract_text_from_file
from app.services.retrieval_service import retrieval_service
from app.services.reranker_service import reranker_service
from app.orchestrator.graph import run_analysis_pipeline

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/analyze", response_model=AnalysisResponse, summary="Analyze tender or specification document")
async def analyze_tender(
    # Multipart Form parameters (for file or form submission)
    file: Optional[UploadFile] = File(None, description="Tender PDF, DOCX, or text file"),
    text: Optional[str] = Form(None, description="Raw tender text or product requirements"),
    language: Optional[str] = Form("auto", description="Language preference ('en', 'hi', 'auto')"),
    max_depth: Optional[int] = Form(2, description="Standards graph exploration depth"),
    # Direct JSON body option if invoked without multipart
    body: Optional[AnalysisRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Main SpecSure AI Recommendation Pipeline:
    1. Language Detection & Indic Technical Translation
    2. Structured Requirement Extraction
    3. Hybrid Retrieval (Dense Vector + BM25 with Reciprocal Rank Fusion)
    4. Cross-Encoder Reranking
    5. Knowledge Graph BFS Expansion (Normative references, test methods, safety)
    6. Regulatory & QCO Enrichment
    7. Specification Health, Parameter Gap, and Ambiguity Detection
    8. Deterministic Provenance Trace & Explainability Generation
    """
    input_text = ""
    filename = None
    input_lang = "auto"
    depth = 2

    # Handle file upload
    if file is not None and file.filename:
        filename = file.filename
        content = await file.read()
        extracted, error = extract_text_from_file(content, filename)
        if error:
            raise HTTPException(status_code=400, detail=f"File parsing error: {error}")
        input_text = extracted
        if language:
            input_lang = language
        if max_depth:
            depth = max_depth
    # Handle form text
    elif text and text.strip():
        input_text = text.strip()
        if language:
            input_lang = language
        if max_depth:
            depth = max_depth
    # Handle JSON request body
    elif body is not None and body.text and body.text.strip():
        input_text = body.text.strip()
        input_lang = body.language or "auto"
        depth = body.max_depth or 2
    else:
        raise HTTPException(
            status_code=400, 
            detail="Either 'text' or 'file' must be provided for analysis."
        )

    if len(input_text.strip()) < 5:
        raise HTTPException(status_code=400, detail="Input text is too short to analyze.")

    # Execute LangGraph Pipeline
    try:
        final_state = await run_analysis_pipeline(
            input_text=input_text,
            input_language=input_lang,
            filename=filename,
            max_depth=depth,
            db=db
        )
    except Exception as e:
        logger.error(f"Analysis pipeline execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {str(e)}")

    # Format response
    spec_health_data = final_state.get("spec_health", {})
    health_obj = SpecHealth(
        overall_score=spec_health_data.get("overall_score", 100),
        completeness_score=spec_health_data.get("completeness_score", 100),
        currency_score=spec_health_data.get("currency_score", 100),
        clarity_score=spec_health_data.get("clarity_score", 100),
        gaps=[SpecGap(**g) if isinstance(g, dict) else g for g in spec_health_data.get("gaps", [])],
        summary=spec_health_data.get("summary", "Analysis completed.")
    )

    graph_data_dict = final_state.get("graph_data", {})
    graph_obj = GraphData(
        nodes=graph_data_dict.get("nodes", []),
        edges=graph_data_dict.get("edges", [])
    )

    allied_list = [
        AlliedStandard(**a) if isinstance(a, dict) else a
        for a in final_state.get("allied_standards", [])
    ]

    cert_list = [
        CertificationInfo(**c) if isinstance(c, dict) else c
        for c in final_state.get("certification_info", [])
    ]

    req_list = [
        ExtractedRequirement(**r) if isinstance(r, dict) else r
        for r in final_state.get("extracted_requirements", [])
    ]

    recommended_list = [
        RecommendedStandard(**r) if isinstance(r, dict) else r
        for r in final_state.get("recommended_standards", [])
    ]

    return AnalysisResponse(
        analysis_id=final_state.get("analysis_id", "live-analysis"),
        input_language=final_state.get("input_language", "en"),
        detected_language=final_state.get("detected_language", "en"),
        product_identity=final_state.get("product_identity"),
        application_context=final_state.get("application"),
        extracted_requirements=req_list,
        recommended_standards=recommended_list,
        allied_standards=allied_list,
        certification_info=cert_list,
        spec_health=health_obj,
        graph_data=graph_obj,
        processing_time_seconds=final_state.get("processing_time_seconds", 0.0),
        retrieval_confidence=final_state.get("retrieval_confidence"),
        abstained=bool(final_state.get("abstained")),
        abstention_note=("Insufficient evidence: no standard reached the minimum applicability score. "
                         "Treat the list as candidates for manual review, not recommendations.") if final_state.get("abstained") else None,
    )

@router.post("/analyze/quick", response_model=QuickSearchResponse, summary="Quick analysis (retrieval only)")
async def quick_analyze(
    query: str = Body(..., embed=True),
    top_k: int = Body(5, embed=True),
    db: AsyncSession = Depends(get_db)
):
    """Fast lookup executing hybrid retrieval and cross-encoder reranking."""
    start_time = time.time()
    candidates = await retrieval_service.hybrid_retrieve(query=query, db=db, top_k=top_k * 2)
    reranked = reranker_service.rerank(query=query, candidates=candidates, top_k=top_k)
    
    results = [
        RecommendedStandard(
            id=std.id,
            is_number=std.is_number,
            title=std.title,
            scope=std.scope,
            status=std.status.value if hasattr(std.status, "value") else str(std.status),
            relevance_score=round(score, 3),
            relevance_reason=f"Top candidate match (score: {score:.2f})",
            relationship_to_query="direct_product_match",
            latest_edition=std.edition,
            amendments=[],
            evidence=[]
        )
        for std, score in reranked
    ]

    return QuickSearchResponse(
        query=query,
        results=results,
        total_found=len(results),
        processing_time_seconds=round(time.time() - start_time, 2)
    )

@router.get("/analyze/{analysis_id}", summary="Get past analysis result")
async def get_analysis_result(analysis_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves a previously computed analysis by its analysis ID."""
    record = (await db.execute(select(AnalysisResult).where(AnalysisResult.analysis_uid == analysis_id))).scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="No analysis record found.")
    
    return {
        "analysis_id": analysis_id,
        "input_text": record.input_text,
        "input_language": record.input_language,
        "input_filename": record.input_filename,
        "extracted_requirements": record.extracted_requirements,
        "recommended_standards": record.recommended_standards,
        "allied_standards": record.allied_standards,
        "spec_health": record.spec_health,
        "graph_data": record.graph_data,
        "certification_info": record.certification_info,
        "created_at": record.created_at.isoformat() if record.created_at else None
    }
