from sqlalchemy import Column, String, Integer, Text, DateTime
from datetime import datetime
from app.db.session import Base

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_type = Column(String(50), nullable=False) # bis_gazette, bis_standard_clause, qco_order, tender_doc
    source_url = Column(Text, nullable=True)
    document_hash = Column(String(64), nullable=True)
    page = Column(String(20), nullable=True)
    clause = Column(String(50), nullable=True)
    extracted_text = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow)
    trust_level = Column(String(30), default="evidence_backed") # evidence_backed, inferred, unverified
    created_at = Column(DateTime, default=datetime.utcnow)
