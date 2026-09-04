from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(50), primary_key=True, index=True) # e.g. INV-10001
    customer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_name = Column(String(150), nullable=False)
    customer_phone = Column(String(20), nullable=False)
    
    vendor_id = Column(Integer, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False, index=True)
    vendor_shop_name = Column(String(200), nullable=False)
    vendor_phone = Column(String(20), nullable=False)
    vendor_area = Column(String(150), nullable=False)
    
    subtotal = Column(Float, nullable=False)
    discount = Column(Float, default=0.00)
    commission_amount = Column(Float, default=0.00) # Total 2% category-based commission
    total = Column(Float, nullable=False)
    status = Column(String(50), default="completed", index=True)
    payment_method = Column(String(50), default="Cash on Delivery")
    call_id = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    customer = relationship("User", foreign_keys=[customer_id])
    vendor = relationship("Vendor", foreign_keys=[vendor_id])

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_id = Column(String(50), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name = Column(String(255), nullable=False)
    
    # Category and 2% commission snapshot
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    category_name = Column(String(100), nullable=False, default="General")
    commission_rate = Column(Float, nullable=False, default=2.00) # Snapshot at sale time e.g. 2.00%
    commission_amount = Column(Float, nullable=False, default=0.00) # Calculated line commission
    
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    line_total = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")
    category_rel = relationship("Category")
