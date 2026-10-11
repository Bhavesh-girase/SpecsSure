import logging
from typing import Dict, Any
from app.orchestrator.state import AnalysisState
from app.config import settings

logger = logging.getLogger(__name__)

async def validate_candidates(state: AnalysisState) -> Dict[str, Any]:
    """
    Node 3: Candidate Validation and Query Reformulation Decision.
    """
    candidates = state.get("candidate_standards", [])
    confidence = state.get("retrieval_confidence", 0.0)
    requery_count = state.get("requery_count", 0)

    # Threshold for confident retrieval
    CONFIDENCE_THRESHOLD = 0.30

    if confidence < CONFIDENCE_THRESHOLD and requery_count < 2 and len(candidates) > 0:
        # Reformulate query to broaden retrieval
        logger.info(f"Low confidence ({confidence:.2f}), triggering query reformulation (attempt {requery_count + 1})...")
        product = state.get("product_identity", "")
        app = state.get("application", "")
        reformulated = f"{product} standard specifications BIS testing code {app}"
        
        return {
            "needs_requery": True,
            "requery_text": reformulated,
            "requery_count": requery_count + 1
        }
    
    # Validation passed or maximum retries reached
    validated = [std for std, score in candidates[:settings.TOP_K_FINAL]]
    
    return {
        "needs_requery": False,
        "validated_standards": validated
    }
