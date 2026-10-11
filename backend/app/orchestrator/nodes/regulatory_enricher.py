import logging
from typing import Dict, Any
from app.orchestrator.state import AnalysisState
from app.orchestrator.nodes._context import get_db_session
from app.services.regulatory_service import regulatory_service

logger = logging.getLogger(__name__)

async def enrich_with_regulations(state: AnalysisState) -> Dict[str, Any]:
    """
    Node 5: Regulatory and Compulsory Certification Enrichment (QCO, CRS, Mandatory ISI).
    """
    db = get_db_session()
    validated = state.get("validated_standards", [])
    product_desc = state.get("product_identity", "")

    is_numbers = [std.is_number for std in validated if hasattr(std, "is_number")]
    
    cert_info = await regulatory_service.check_certification_requirements(
        is_numbers=is_numbers,
        product_description=product_desc,
        db=db
    )

    return {
        "certification_info": [c.model_dump() for c in cert_info]
    }
