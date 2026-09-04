from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    AREA_MANAGER = "area_manager"
    CRM_OPERATOR = "crm_operator"
    FINANCE = "finance"
    VENDOR = "vendor"
    CUSTOMER = "customer"

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING_APPROVAL = "pending_approval"
    INACTIVE = "inactive"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(150), nullable=False)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default=UserRole.CUSTOMER.value, nullable=False, index=True)
    status = Column(String(50), default=UserStatus.ACTIVE.value, nullable=False)
    avatar_url = Column(Text, nullable=True)
    fcm_token = Column(Text, nullable=True)
    
    # Location reference
    division_name = Column(String(100), nullable=True)
    district_name = Column(String(100), nullable=True)
    upazila_name = Column(String(100), nullable=True)
    area_name = Column(String(150), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
