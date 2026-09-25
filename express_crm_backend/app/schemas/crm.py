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

class CustomerStatusUpdateRequest(BaseModel):
    status: str # active, suspended, inactive
    reason: Optional[str] = None

class CreateStaffRequest(BaseModel):
    name: str
    phone: str
    password: str
    email: Optional[str] = None
    role: str # area_manager, crm_operator, finance
    division: Optional[str] = "Dhaka"
    district: Optional[str] = "Gazipur"
    upazila: Optional[str] = "Kaliganj"
    area: Optional[str] = "Kaliganj Bazar"

class StaffResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    role: str
    status: str
    division: Optional[str] = None
    district: Optional[str] = None
    upazila: Optional[str] = None
    area: Optional[str] = None
    createdAt: str

