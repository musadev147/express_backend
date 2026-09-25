from typing import List, Optional, Any
from pydantic import BaseModel

class OrderItemInput(BaseModel):
    id: Optional[Any] = None # can be passed as "1" or 1
    productId: Optional[int] = None
    name: Optional[str] = None
    price: Optional[float] = None
    qty: int = 1


class InvoiceCreateRequest(BaseModel):
    customerPhone: str
    customerName: str
    vendorPhone: Optional[str] = None
    vendorShopName: Optional[str] = None
    vendorArea: Optional[str] = None
    vendorId: Optional[int] = None
    items: List[OrderItemInput]
    discount: float = 0.00
    paymentMethod: str = "Cash on Delivery"
    callId: Optional[str] = None

class InvoiceItemDetail(BaseModel):
    id: Optional[int] = None
    productId: Optional[int] = None
    name: str
    category: str
    price: float
    qty: int
    lineTotal: float
    commissionRate: float = 2.00 # 2% category commission
    commissionAmount: float = 0.00 # Line item commission

class PlatformCommissionDetail(BaseModel):
    rateDescription: str = "2% Category Commission"
    totalCommissionAmount: float
    itemsBreakdown: List[InvoiceItemDetail] = []

class InvoiceResponse(BaseModel):
    id: str
    customerPhone: str
    customerName: str
    vendorPhone: str
    vendorShopName: str
    vendorArea: str
    items: List[InvoiceItemDetail] = []
    subtotal: float
    discount: float
    commissionAmount: float # Total 2% category commission
    total: float
    status: str
    paymentMethod: str
    callId: Optional[str] = None
    dateTime: str
    pdfDownloadUrl: Optional[str] = None
    vendorWalletDeduction: Optional[float] = None
    vendorUpdatedWalletBalance: Optional[float] = None

class InvoiceStatusUpdateRequest(BaseModel):
    status: str # pending, confirmed, completed, cancelled, delivered
    note: Optional[str] = None

class InvoiceCancelRequest(BaseModel):
    reason: Optional[str] = "Customer request / cancellation"

