from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class StandardRelation(Base):
    __tablename__ = "standard_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_standard_id = Column(Integer, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False, index=True)
    to_standard_id = Column(Integer, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False, index=True)
    # Relationship types: normative_reference, test_method, safety_requirement, installation_code, terminology, allied_product, superseded_by
    relationship_type = Column(String(50), nullable=False, index=True)
    clause_reference = Column(String(100), nullable=True) # e.g. Clause 4.2, Section 5
    evidence_id = Column(Integer, ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    from_standard = relationship("Standard", foreign_keys=[from_standard_id], back_populates="outgoing_relations")
    to_standard = relationship("Standard", foreign_keys=[to_standard_id], back_populates="incoming_relations")

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_uid = Column(String(64), nullable=True, index=True)
    input_text = Column(Text, nullable=False)
    input_language = Column(String(20), default="en")
    input_filename = Column(String(300), nullable=True)
    extracted_requirements = Column(JSON, nullable=True)
    recommended_standards = Column(JSON, nullable=True)
    allied_standards = Column(JSON, nullable=True)
    spec_health = Column(JSON, nullable=True)
    graph_data = Column(JSON, nullable=True)
    certification_info = Column(JSON, nullable=True)
    full_report = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
