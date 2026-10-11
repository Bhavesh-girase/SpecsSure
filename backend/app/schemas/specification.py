from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ParameterTemplate(BaseModel):
    chemical: List[str] = []
    physical: List[str] = []
    mechanical: List[str] = []
    performance: List[str] = []
    test_methods: List[str] = []
    safety: List[str] = []
    installation: List[str] = []
    certification: Dict[str, Any] = {}

class ProductCategoryRead(BaseModel):
    id: int
    category_name: str
    bis_division: Optional[str] = None
    bis_section_committee: Optional[str] = None
    primary_standard_is: Optional[str] = None
    parameter_template: Dict[str, Any]
    keywords: Optional[str] = None

    class Config:
        from_attributes = True

class AmbiguityDetectionResult(BaseModel):
    term_found: str
    risk_level: str = "warning"
    explanation: str
    suggested_replacement: str
    context_snippet: Optional[str] = None

class ConflictDetectionResult(BaseModel):
    parameter: str
    conflicting_values: List[str]
    severity: str = "critical"
    description: str
