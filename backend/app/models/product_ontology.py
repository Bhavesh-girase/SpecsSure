from sqlalchemy import Column, String, Integer, Text, DateTime, JSON
from datetime import datetime
from app.db.session import Base

class ProductCategory(Base):
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(200), nullable=False, unique=True, index=True)
    bis_division = Column(String(100), nullable=True) # e.g. Civil Engineering Division (CED)
    bis_section_committee = Column(String(50), nullable=True) # e.g. CED 2
    primary_standard_is = Column(String(50), nullable=True) # e.g. IS 269:2015
    parameter_template = Column(JSON, nullable=False)
    keywords = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
