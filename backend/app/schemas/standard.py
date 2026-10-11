from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class AmendmentRead(BaseModel):
    id: int
    amendment_number: int
    title: Optional[str] = None
    published_at: Optional[datetime] = None
    effective_from: Optional[datetime] = None
    changed_clauses: Optional[str] = None
    summary: Optional[str] = None
    source_url: Optional[str] = None

    class Config:
        from_attributes = True

class StandardRelationRead(BaseModel):
    id: int
    to_standard_id: int
    to_is_number: Optional[str] = None
    to_title: Optional[str] = None
    relationship_type: str
    clause_reference: Optional[str] = None
    valid_from: Optional[datetime] = None

    class Config:
        from_attributes = True

class StandardBase(BaseModel):
    is_number: str
    title: str
    scope: Optional[str] = None
    status: str = "current"
    edition: Optional[str] = None
    part_number: Optional[str] = None
    division_code: Optional[str] = None
    section_committee: Optional[str] = None
    publication_date: Optional[datetime] = None
    effective_from: Optional[datetime] = None
    superseded_by: Optional[str] = None
    iso_equivalent: Optional[str] = None
    source_url: Optional[str] = None

class StandardCreate(StandardBase):
    pass

class StandardRead(StandardBase):
    id: int
    last_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    amendments: List[AmendmentRead] = []
    outgoing_relations: List[StandardRelationRead] = []

    class Config:
        from_attributes = True

class StandardGraphNode(BaseModel):
    id: str
    db_id: int
    is_number: str
    label: str
    title: str
    status: str
    division: Optional[str] = None
    node_type: str = "standard" # primary, test_method, safety, allied, superseded
    depth: int = 0
    confidence: Optional[float] = None
    amendments_count: int = 0

class StandardGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship_type: str
    clause_reference: Optional[str] = None
    label: Optional[str] = None

class StandardGraphResponse(BaseModel):
    root_is_number: str
    nodes: List[StandardGraphNode]
    edges: List[StandardGraphEdge]
    total_nodes: int
    total_edges: int
