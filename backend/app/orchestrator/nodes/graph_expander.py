import logging
from typing import Dict, Any
from app.orchestrator.state import AnalysisState
from app.orchestrator.nodes._context import get_db_session
from app.services.graph_service import graph_service
from app.config import settings

logger = logging.getLogger(__name__)

async def expand_standards_graph(state: AnalysisState) -> Dict[str, Any]:
    """
    Node 4: Knowledge Graph BFS expansion from validated standards.
    Traverses normative references, test methods, safety requirements, and allied standards.
    """
    db = get_db_session()
    validated = state.get("validated_standards", [])
    max_depth = state.get("max_depth", settings.GRAPH_MAX_DEPTH)

    if not validated:
        return {
            "graph_data": {"nodes": [], "edges": []},
            "allied_standards": []
        }

    valid_ids = [std.id for std in validated if hasattr(std, "id")]
    expanded = await graph_service.expand_graph(
        standard_ids=valid_ids,
        db=db,
        max_depth=max_depth
    )

    return {
        "graph_data": {
            "nodes": [n.model_dump() for n in expanded["nodes"]],
            "edges": [e.model_dump() for e in expanded["edges"]]
        },
        "allied_standards": expanded["allied_standards"]
    }
