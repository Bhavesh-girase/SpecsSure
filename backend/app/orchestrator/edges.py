from typing import Literal
from app.orchestrator.state import AnalysisState

def should_requery(state: AnalysisState) -> Literal["requery", "continue"]:
    """
    Evaluates whether retrieval confidence was inadequate and a query reformulation loop is needed.
    """
    if state.get("needs_requery", False):
        return "requery"
    return "continue"
