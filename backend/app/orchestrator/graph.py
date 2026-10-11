import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.graph import StateGraph, START, END

from app.orchestrator.state import AnalysisState
from app.orchestrator.nodes._context import set_db_session
from app.orchestrator.nodes import (
    detect_and_extract,
    retrieve_standards,
    validate_candidates,
    expand_standards_graph,
    enrich_with_regulations,
    analyze_specification,
    generate_final_report,
)
from app.orchestrator.edges import should_requery

logger = logging.getLogger(__name__)

def build_analysis_graph() -> Any:
    """Builds and compiles the complete SpecSure LangGraph agentic workflow."""
    workflow = StateGraph(AnalysisState)

    # 1. Register Nodes
    workflow.add_node("detect_and_extract", detect_and_extract)
    workflow.add_node("retrieve", retrieve_standards)
    workflow.add_node("validate", validate_candidates)
    workflow.add_node("expand_graph", expand_standards_graph)
    workflow.add_node("enrich_regulatory", enrich_with_regulations)
    workflow.add_node("analyze_spec", analyze_specification)
    workflow.add_node("generate_report", generate_final_report)

    # 2. Register Edges
    workflow.add_edge(START, "detect_and_extract")
    workflow.add_edge("detect_and_extract", "retrieve")
    workflow.add_edge("retrieve", "validate")

    # 3. Conditional Edge from validate (Query Reformulation Retry Loop)
    workflow.add_conditional_edges(
        "validate",
        should_requery,
        {
            "requery": "retrieve",
            "continue": "expand_graph"
        }
    )

    # 4. Downstream Pipeline Edges
    workflow.add_edge("expand_graph", "enrich_regulatory")
    workflow.add_edge("enrich_regulatory", "analyze_spec")
    workflow.add_edge("analyze_spec", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()

# Singleton compiled graph
analysis_graph = build_analysis_graph()

async def run_analysis_pipeline(
    input_text: str,
    input_language: str = "auto",
    filename: Optional[str] = None,
    max_depth: int = 2,
    db: Optional[AsyncSession] = None
) -> Dict[str, Any]:
    """
    Executes the end-to-end SpecSure agentic workflow given user input text or tender document.
    """
    if db is not None:
        set_db_session(db)

    start_time = time.time()
    initial_state: AnalysisState = {
        "input_text": input_text,
        "input_language": input_language,
        "input_filename": filename,
        "max_depth": max_depth,
        "processing_time_seconds": start_time,
        "requery_count": 0,
        "needs_requery": False
    }

    logger.info("Starting SpecSure agentic analysis pipeline...")
    final_state = await analysis_graph.ainvoke(initial_state)
    logger.info(f"SpecSure analysis completed in {time.time() - start_time:.2f}s")
    
    return final_state
