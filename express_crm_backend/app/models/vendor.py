from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    shop_name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    address = Column(Text, nullable=False)
    
    division_id = Column(Integer, ForeignKey("divisions.id", ondelete="SET NULL"), nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="SET NULL"), nullable=True)
    upazila_id = Column(Integer, ForeignKey("upazilas.id", ondelete="SET NULL"), nullable=True)
    area_id = Column(Integer, ForeignKey("areas.id", ondelete="SET NULL"), nullable=True, index=True)
    
    division_name = Column(String(100), nullable=True)
    district_name = Column(String(100), nullable=True)
    upazila_name = Column(String(100), nullable=True)
    area_name = Column(String(150), nullable=True)
    
    commission_rate = Column(Float, default=2.00) # 2% category commission
    nid_number = Column(String(50), nullable=True)
    trade_license = Column(String(100), nullable=True)
    is_verified = Column(Boolean, default=False)
    wallet_balance = Column(Float, default=0.00)
    rating = Column(Float, default=4.8)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="vendor_profile")
    products = relationship("Product", back_populates="vendor", cascade="all, delete-orphan")
    ledger_entries = relationship("VendorWalletLedger", back_populates="vendor", cascade="all, delete-orphan")
