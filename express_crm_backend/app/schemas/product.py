from typing import List, Optional
from pydantic import BaseModel

class ProductCreateRequest(BaseModel):
    name: str
    category: str = "Electronics"
    categoryId: Optional[int] = None
    description: Optional[str] = None
    price: float
    stock: int = 0
    unit: str = "pcs"
    isAvailable: bool = True
    tags: List[str] = []
    imageUrl: Optional[str] = None

class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    categoryId: Optional[int] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    unit: Optional[str] = None
    isAvailable: Optional[bool] = None
    tags: Optional[List[str]] = None
    imageUrl: Optional[str] = None

class ProductToggleStockRequest(BaseModel):
    isAvailable: bool

class ProductResponse(BaseModel):
    id: int
    vendorId: int
    name: str
    category: str
    categoryId: Optional[int] = None
    commissionRate: Optional[float] = 2.00 # 2% category commission
    description: Optional[str] = None
    price: float
    stock: int
    unit: str
    isAvailable: bool
    tags: List[str] = []
    imageUrl: Optional[str] = None

class VendorMarketplaceItem(BaseModel):
    id: int
    name: str
    shopName: str
    phone: str
    category: str
    area: str
    address: str
    distanceKm: Optional[float] = 0.8
    productCount: int = 0
    rating: float = 4.8
    walletBalance: Optional[float] = None
    isVerified: bool = False
