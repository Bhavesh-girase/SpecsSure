import logging
from typing import Dict, Any
from app.orchestrator.state import AnalysisState
from app.orchestrator.nodes._context import get_db_session
from app.services.spec_analyzer import spec_analyzer

logger = logging.getLogger(__name__)

async def analyze_specification(state: AnalysisState) -> Dict[str, Any]:
    """
    Node 6: Specification Health Assessment, Gap Detection, and Ambiguity Identification.
    """
    db = get_db_session()
    
    input_text = state.get("processed_text", "") or state.get("input_text", "")
    extracted_reqs = state.get("extracted_requirements", [])
    product_identity = state.get("product_identity", "")
    validated_standards = state.get("validated_standards", [])

    health = await spec_analyzer.analyze_spec_health(
        input_text=input_text,
        extracted_requirements=extracted_reqs,
        product_identity=product_identity,
        validated_standards=validated_standards,
        db=db
    )

    return {
        "spec_health": health.model_dump(),
        "gaps": [g.model_dump() for g in health.gaps]
    }
