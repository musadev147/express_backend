from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(String(50), primary_key=True, index=True) # e.g. call_172545990001
    caller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    caller_role = Column(String(50), nullable=False)
    caller_phone = Column(String(20), nullable=False)
    caller_name = Column(String(150), nullable=True)
    
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_phone = Column(String(20), nullable=False)
    receiver_name = Column(String(150), nullable=True)
    receiver_shop_name = Column(String(200), nullable=True)
    receiver_area = Column(String(150), nullable=True)
    
    product_name = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="dialing")
    duration_seconds = Column(Integer, default=0)
    invoice_id = Column(String(50), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)

    caller = relationship("User", foreign_keys=[caller_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    invoice = relationship("Invoice", foreign_keys=[invoice_id])
