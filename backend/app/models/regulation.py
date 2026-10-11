from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from datetime import datetime
from app.db.session import Base

class Regulation(Base):
    __tablename__ = "regulations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(60), nullable=True, index=True)  # stable registry key e.g. QCO-CEMENT-2003
    regulation_type = Column(String(50), nullable=False, index=True) # e.g. QCO, CRS, Mandatory ISI, Hallmarking
    scheme = Column(String(120), nullable=True)  # BIS Standard Mark (Scheme-I), CRS (Scheme-II) ...
    verification_state = Column(String(40), default="curated_unverified")  # source_checked | curated_unverified | simulated
    title = Column(Text, nullable=False)
    issuing_authority = Column(String(200), nullable=True) # e.g. Ministry of Commerce & Industry, BIS, MeitY
    notification_number = Column(String(100), nullable=True)
    product_scope = Column(Text, nullable=True)
    standard_ids = Column(JSON, nullable=True) # list of IS numbers e.g. ["IS 269:2015", "IS 455:2015"]
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    is_mandatory = Column(String(10), default="yes") # yes / no / conditional
    source_url = Column(Text, nullable=True)
    source_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
