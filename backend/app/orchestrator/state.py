from typing import TypedDict, List, Dict, Any, Optional, Tuple

class AnalysisState(TypedDict, total=False):
    input_text: str
    input_language: str
    input_filename: Optional[str]
    max_depth: int
    
    # Preprocessing & Language
    processed_text: str
    detected_language: str
    was_translated: bool
    
    # Requirement Extraction
    product_identity: Optional[str]
    application: Optional[str]
    extracted_requirements: List[Dict[str, Any]]
    mentioned_standards: List[str]
    
    # Retrieval & Validation
    candidate_standards: List[Tuple[Any, float]]
    retrieval_confidence: float
    retrieval_components: Dict[int, Dict[str, float]]
    retrieval_query: str
    validated_standards: List[Any]
    needs_requery: bool
    requery_text: Optional[str]
    requery_count: int
    
    # Graph & Regulations
    allied_standards: List[Dict[str, Any]]
    graph_data: Dict[str, Any]
    certification_info: List[Dict[str, Any]]
    
    # Specification Intelligence
    spec_health: Dict[str, Any]
    gaps: List[Dict[str, Any]]
    
    # Explanations & Output
    recommendation_explanations: Dict[str, Any]
    recommended_standards: List[Dict[str, Any]]
    analysis_id: str
    processing_time_seconds: float
    error: Optional[str]
    abstained: bool
