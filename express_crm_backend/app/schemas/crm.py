from typing import List, Optional, Any
from pydantic import BaseModel

class CrmAnalyticsOverview(BaseModel):
    totalGMV: float
    monthlyRevenue: float # 2% platform commission earnings
    activeVendors: int
    totalCustomers: int
    totalInvoices: int
    activeCallSessions: int
    unfulfilledSearchDemands: int

class DemandHeatmapItem(BaseModel):
    upazila: str
    area: str
    searchCount: int
    topQuery: str

class VerifyKycRequest(BaseModel):
    isVerified: bool = True
    commissionRate: Optional[float] = 2.00
    adminNote: Optional[str] = None

class VendorStatusUpdateRequest(BaseModel):
    status: str # active, suspended, pending_approval, inactive
    reason: Optional[str] = None

class TicketReplyRequest(BaseModel):
    message: str
    isInternalNote: bool = False

class TicketStatusUpdateRequest(BaseModel):
    status: str # open, in_progress, resolved, closed
    resolutionSummary: Optional[str] = None

class PayoutApprovalRequest(BaseModel):
    transactionRef: str
    adminNote: Optional[str] = None

class CategoryCommissionReportItem(BaseModel):
    category: str
    commissionRate: str
    totalOrders: int
    gmv: float
    commissionEarned: float

class CategoryCommissionReportResponse(BaseModel):
    totalCommissionEarned: float
    currency: str = "BDT"
    categoryBreakdown: List[CategoryCommissionReportItem] = []
