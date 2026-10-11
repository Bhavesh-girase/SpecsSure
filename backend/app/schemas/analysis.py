from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.schemas.standard import StandardGraphNode, StandardGraphEdge, AmendmentRead
from app.schemas.recommendation import RecommendationExplanation

class AnalysisRequest(BaseModel):
    text: Optional[str] = Field(default=None, description="Tender or product specification raw text")
    language: Optional[str] = Field(default="auto", description="Input language code ('en', 'hi', or 'auto')")
    product_category: Optional[str] = Field(default=None, description="Optional structured product category")
    max_depth: Optional[int] = Field(default=2, description="Standards graph exploration depth")

class ExtractedRequirement(BaseModel):
    category: str # chemical, physical, mechanical, electrical, performance, testing, safety, general
    parameter: str
    operator: Optional[str] = "=" # >=, <=, =, range
    value: str
    unit: Optional[str] = None
    source_span: Optional[str] = None
    confidence: float = 1.0

class RecommendedStandard(BaseModel):
    id: int
    is_number: str
    title: str
    scope: Optional[str] = None
    status: str = "current" # current, superseded, withdrawn, under_review
    relevance_score: float
    relevance_reason: str
    relationship_to_query: str # direct_product_match, normative_reference, test_method, safety_code
    latest_edition: Optional[str] = None
    amendments: List[AmendmentRead] = []
    superseded_by: Optional[str] = None
    evidence: List[Dict[str, Any]] = []
    explanation: Optional[RecommendationExplanation] = None

class AlliedStandard(BaseModel):
    id: int
    is_number: str
    title: str
    status: str
    relationship_type: str # normative_reference, test_method, safety_requirement, installation_code, terminology
    clause_reference: Optional[str] = None
    parent_is_number: str
    depth: int = 1

class CertificationInfo(BaseModel):
    is_number: str
    standard_title: Optional[str] = None
    is_mandatory: str = "no" # yes, no, conditional
    scheme: Optional[str] = None # BIS ISI Mark, CRS, Hallmarking, ECO Mark
    qco_reference: Optional[str] = None
    issuing_authority: Optional[str] = None
    effective_from: Optional[str] = None
    verification_state: str = "verified_regulation" # verified_regulation, not_found, active_license
    note: Optional[str] = None

class SpecGap(BaseModel):
    gap_type: str # missing_parameter, ambiguous_term, outdated_reference, conflict, missing_normative_test
    severity: str # critical, warning, info
    description: str
    suggestion: str
    affected_standard: Optional[str] = None
    clause_reference: Optional[str] = None

class SpecHealth(BaseModel):
    overall_score: int = Field(default=100, ge=0, le=100)
    completeness_score: int = Field(default=100, ge=0, le=100)
    currency_score: int = Field(default=100, ge=0, le=100)
    clarity_score: int = Field(default=100, ge=0, le=100)
    gaps: List[SpecGap] = []
    summary: str

class GraphData(BaseModel):
    nodes: List[StandardGraphNode] = []
    edges: List[StandardGraphEdge] = []

class AnalysisResponse(BaseModel):
    analysis_id: str
    input_language: str
    detected_language: str
    product_identity: Optional[str] = None
    application_context: Optional[str] = None
    extracted_requirements: List[ExtractedRequirement] = []
    recommended_standards: List[RecommendedStandard] = []
    allied_standards: List[AlliedStandard] = []
    certification_info: List[CertificationInfo] = []
    spec_health: SpecHealth
    graph_data: GraphData
    processing_time_seconds: float
    retrieval_confidence: Optional[float] = None
    abstained: bool = False
    abstention_note: Optional[str] = None
    disclaimer: str = "SpecSure AI recommendation output is intended for procurement decision support and technical verification. Always verify against official Gazette notifications and e-BIS / BIS CARE portal."

class QuickSearchResponse(BaseModel):
    query: str
    results: List[RecommendedStandard]
    total_found: int
    processing_time_seconds: float
