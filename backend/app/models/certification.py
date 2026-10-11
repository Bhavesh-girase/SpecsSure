from sqlalchemy import Column, String, Integer, Text, DateTime
from datetime import datetime
from app.db.session import Base

class CertificationRecord(Base):
    __tablename__ = "certification_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identifier = Column(String(100), nullable=False, index=True) # CM/L number or registration no
    scheme = Column(String(50), nullable=False) # BIS ISI Mark, CRS, ECO Mark, Hallmarking
    holder_name = Column(String(300), nullable=True) # Manufacturer/Licensee
    product_description = Column(Text, nullable=True)
    model_scope = Column(Text, nullable=True)
    standard_is_numbers = Column(Text, nullable=True)
    status = Column(String(30), default="active") # active, suspended, cancelled, expired
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    verification_source = Column(String(100), nullable=True) # BIS CARE portal / e-BIS
    verified_at = Column(DateTime, nullable=True)
    verification_state = Column(String(30), default="unverified")
    created_at = Column(DateTime, default=datetime.utcnow)
