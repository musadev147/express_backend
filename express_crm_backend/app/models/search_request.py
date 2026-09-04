from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class SearchRequest(Base):
    __tablename__ = "search_requests"

    id = Column(String(50), primary_key=True, index=True) # e.g. req_1725458000123
    query_text = Column(String(255), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    
    division_name = Column(String(100), nullable=True)
    district_name = Column(String(100), nullable=True)
    upazila_name = Column(String(100), nullable=True)
    area_name = Column(String(150), nullable=False, index=True)
    
    status = Column(String(50), default="unfulfilled")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("User", foreign_keys=[customer_id])
