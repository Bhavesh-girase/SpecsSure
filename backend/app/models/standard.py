from sqlalchemy import Column, String, Integer, Text, DateTime, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.session import Base
from app.config import settings

# Attempt to import pgvector Vector, or fallback to JSON/Text for non-pgvector environments
try:
    from pgvector.sqlalchemy import Vector
    VectorType = Vector(settings.EMBEDDING_DIMENSION)
except Exception:
    VectorType = JSON

class StandardStatus(str, enum.Enum):
    CURRENT = "current"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"
    UNDER_REVIEW = "under_review"
    FUTURE_EFFECTIVE = "future_effective"
    SOURCE_UNAVAILABLE = "source_unavailable"

class Standard(Base):
    __tablename__ = "standards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    is_number = Column(String(200), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    scope = Column(Text, nullable=True)
    status = Column(SQLEnum(StandardStatus), default=StandardStatus.CURRENT, index=True)
    edition = Column(String(20), nullable=True)
    part_number = Column(String(20), nullable=True)
    division_code = Column(String(200), nullable=True)
    section_committee = Column(String(200), nullable=True)
    publication_date = Column(DateTime, nullable=True)
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    superseded_by = Column(String(50), nullable=True)
    iso_equivalent = Column(String(100), nullable=True)
    source_url = Column(Text, nullable=True)
    source_hash = Column(String(64), nullable=True)
    last_verified_at = Column(DateTime, default=datetime.utcnow)
    embedding = Column(VectorType, nullable=True)
    search_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    amendments = relationship("Amendment", back_populates="standard", cascade="all, delete-orphan")
    outgoing_relations = relationship(
        "StandardRelation", 
        foreign_keys="StandardRelation.from_standard_id", 
        back_populates="from_standard",
        cascade="all, delete-orphan"
    )
    incoming_relations = relationship(
        "StandardRelation", 
        foreign_keys="StandardRelation.to_standard_id", 
        back_populates="to_standard",
        cascade="all, delete-orphan"
    )
