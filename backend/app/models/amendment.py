from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class Amendment(Base):
    __tablename__ = "amendments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    standard_id = Column(Integer, ForeignKey("standards.id", ondelete="CASCADE"), nullable=False, index=True)
    amendment_number = Column(Integer, nullable=False)
    title = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    effective_from = Column(DateTime, nullable=True)
    changed_clauses = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    source_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    standard = relationship("Standard", back_populates="amendments")
