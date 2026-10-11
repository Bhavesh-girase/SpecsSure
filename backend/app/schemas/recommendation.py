from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class VerificationAuditTrail(BaseModel):
    source_type: str # bis_gazette, db_record, clause_ref
    reference: str
    verified_at: Optional[str] = None
    trust_level: str = "evidence_backed"
    direct_url: Optional[str] = None

class RecommendationExplanation(BaseModel):
    is_number: str
    title: str
    semantic_score: float
    keyword_score: float
    domain_score: float
    graph_score: float
    final_applicability_score: float
    score_formula_note: str = "Engineered provenance score (0.40*semantic + 0.25*keyword + 0.20*domain + 0.15*graph). Decision-support metric, not official BIS determination."
    auditable_trace: List[str]
    natural_language_summary: str
    source_evidence: List[VerificationAuditTrail] = []
