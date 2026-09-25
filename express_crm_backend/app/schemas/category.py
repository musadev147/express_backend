from typing import Optional
from pydantic import BaseModel

class CategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    commissionRate: float # Default 2.0%
    iconUrl: Optional[str] = None
    isActive: bool = True
    totalProducts: Optional[int] = 0
    totalRevenueEarned: Optional[float] = 0.0

class CreateCategoryRequest(BaseModel):
    name: str
    slug: Optional[str] = None
    commissionRate: float = 2.00 # Default 2%
    iconUrl: Optional[str] = None
    isActive: bool = True

class UpdateCategoryCommissionRequest(BaseModel):
    commissionRate: float # e.g. 2.00
    reason: Optional[str] = None

class UpdateCategoryRequest(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    commissionRate: Optional[float] = None
    iconUrl: Optional[str] = None
    isActive: Optional[bool] = None

