from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.category import Category
from app.models.invoice import Invoice, InvoiceItem
from app.models.call_log import CallLog
from app.models.search_request import SearchRequest
from app.models.support_ticket import SupportTicket, TicketReply
from app.models.payout import PayoutRequest, VendorWalletLedger
from app.models.location import Division, District, Upazila, Area
from app.schemas.common import ApiResponse, Meta
from app.schemas.category import CategoryResponse, CreateCategoryRequest, UpdateCategoryCommissionRequest
from app.schemas.crm import (
    CrmAnalyticsOverview, DemandHeatmapItem, VerifyKycRequest, VendorStatusUpdateRequest,
    TicketReplyRequest, TicketStatusUpdateRequest, PayoutApprovalRequest,
    CategoryCommissionReportResponse, CategoryCommissionReportItem
)
from app.schemas.location import (
    CreateDivisionRequest, CreateDistrictRequest, CreateUpazilaRequest, CreateAreaRequest
)
from app.services.auth_service import get_current_user, require_roles

router = APIRouter(prefix="/crm", tags=["Web CRM Administration & 360° Management"])

# Guard for CRM staff and super admins
crm_guard = require_roles([
    UserRole.SUPER_ADMIN.value,
    UserRole.AREA_MANAGER.value,
    UserRole.CRM_OPERATOR.value,
    UserRole.FINANCE.value
])

# 1. Analytics & Demand Heatmap
@router.get("/analytics/overview", response_model=ApiResponse[CrmAnalyticsOverview])
def get_analytics_overview(
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    invoices = db.query(Invoice).all()
    total_gmv = sum(inv.total for inv in invoices)
    monthly_rev = sum(inv.commission_amount for inv in invoices) # Total 2% category commission earned
    
    active_vendors = db.query(Vendor).join(User).filter(User.status == "active").count()
    total_customers = db.query(User).filter(User.role == UserRole.CUSTOMER.value).count()
    total_inv_count = len(invoices)
    active_calls = db.query(CallLog).filter(CallLog.status.in_(["dialing", "active"])).count()
    unfulfilled_demands = db.query(SearchRequest).filter(SearchRequest.status == "unfulfilled").count()

    return ApiResponse(
        success=True,
        statusCode=200,
        message="CRM Overview Analytics fetched",
        data=CrmAnalyticsOverview(
            totalGMV=round(total_gmv, 2),
            monthlyRevenue=round(monthly_rev, 2),
            activeVendors=active_vendors,
            totalCustomers=total_customers,
            totalInvoices=total_inv_count,
            activeCallSessions=active_calls,
            unfulfilledSearchDemands=unfulfilled_demands
        )
    )

@router.get("/analytics/demand-heatmap", response_model=ApiResponse[List[DemandHeatmapItem]])
def get_demand_heatmap(
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    # Group search demands by upazila and area
    results = db.query(
        SearchRequest.upazila_name,
        SearchRequest.area_name,
        func.count(SearchRequest.id).label("search_count"),
        func.max(SearchRequest.query_text).label("top_query")
    ).group_by(SearchRequest.upazila_name, SearchRequest.area_name).all()

    items = [
        DemandHeatmapItem(
            upazila=r[0] or "Kaliganj",
            area=r[1],
            searchCount=r[2],
            topQuery=r[3]
        )
        for r in results
    ]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Demand Heatmap data fetched",
        data=items
    )

# 2. Categories & 2% Commission Management
@router.get("/categories", response_model=ApiResponse[List[CategoryResponse]])
def get_all_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    result = []
    for cat in categories:
        prod_count = db.query(Product).filter(Product.category_id == cat.id).count()
        rev = db.query(func.sum(InvoiceItem.commission_amount)).filter(InvoiceItem.category_id == cat.id).scalar() or 0.0
        result.append(
            CategoryResponse(
                id=cat.id,
                name=cat.name,
                slug=cat.slug,
                commissionRate=cat.commission_rate,
                iconUrl=cat.icon_url,
                isActive=cat.is_active,
                totalProducts=prod_count,
                totalRevenueEarned=round(rev, 2)
            )
        )
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Categories fetched",
        data=result
    )

@router.post("/categories", response_model=ApiResponse[CategoryResponse], status_code=201)
def create_category(
    request: CreateCategoryRequest,
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    slug = request.slug or request.name.lower().replace(" ", "-")
    existing = db.query(Category).filter((Category.name == request.name) | (Category.slug == slug)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category with this name or slug already exists")

    new_cat = Category(
        name=request.name,
        slug=slug,
        commission_rate=request.commissionRate, # Default 2%
        icon_url=request.iconUrl,
        is_active=request.isActive
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)

    return ApiResponse(
        success=True,
        statusCode=201,
        message="Category created successfully",
        data=CategoryResponse(
            id=new_cat.id,
            name=new_cat.name,
            slug=new_cat.slug,
            commissionRate=new_cat.commission_rate,
            iconUrl=new_cat.icon_url,
            isActive=new_cat.is_active,
            totalProducts=0,
            totalRevenueEarned=0.0
        )
    )

@router.patch("/categories/{id}/commission", response_model=ApiResponse[CategoryResponse])
def update_category_commission(
    id: int,
    request: UpdateCategoryCommissionRequest,
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    cat = db.query(Category).filter(Category.id == id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    cat.commission_rate = request.commissionRate
    db.commit()
    db.refresh(cat)

    prod_count = db.query(Product).filter(Product.category_id == cat.id).count()
    rev = db.query(func.sum(InvoiceItem.commission_amount)).filter(InvoiceItem.category_id == cat.id).scalar() or 0.0

    return ApiResponse(
        success=True,
        statusCode=200,
        message=f"Category '{cat.name}' commission rate updated to {cat.commission_rate}%",
        data=CategoryResponse(
            id=cat.id,
            name=cat.name,
            slug=cat.slug,
            commissionRate=cat.commission_rate,
            iconUrl=cat.icon_url,
            isActive=cat.is_active,
            totalProducts=prod_count,
            totalRevenueEarned=round(rev, 2)
        )
    )

@router.get("/finance/category-commission-report", response_model=ApiResponse[CategoryCommissionReportResponse])
def get_category_commission_report(
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    categories = db.query(Category).all()
    breakdown = []
    grand_total_commission = 0.0

    for cat in categories:
        items = db.query(InvoiceItem).filter(
            (InvoiceItem.category_id == cat.id) | (InvoiceItem.category_name == cat.name)
        ).all()
        
        gmv = sum(i.line_total for i in items)
        earned = sum(i.commission_amount for i in items)
        grand_total_commission += earned

        breakdown.append(
            CategoryCommissionReportItem(
                category=cat.name,
                commissionRate=f"{cat.commission_rate}%",
                totalOrders=len(items),
                gmv=round(gmv, 2),
                commissionEarned=round(earned, 2)
            )
        )

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Category 2% Commission Report fetched",
        data=CategoryCommissionReportResponse(
            totalCommissionEarned=round(grand_total_commission, 2),
            currency="BDT",
            categoryBreakdown=breakdown
        )
    )

# 3. Vendor 360° Management
@router.get("/vendors", response_model=ApiResponse[List[dict]])
def get_crm_vendors(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    q = db.query(Vendor).join(User)
    if search:
        q = q.filter((Vendor.shop_name.ilike(f"%{search}%")) | (User.name.ilike(f"%{search}%")) | (User.phone.ilike(f"%{search}%")))
    if status:
        q = q.filter(User.status == status)
    if category:
        q = q.filter(Vendor.category.ilike(f"%{category}%"))

    total = q.count()
    vendors = q.offset((page - 1) * limit).limit(limit).all()

    result = []
    for v in vendors:
        inv_count = db.query(Invoice).filter(Invoice.vendor_id == v.id).count()
        gmv = db.query(func.sum(Invoice.total)).filter(Invoice.vendor_id == v.id).scalar() or 0.0
        result.append({
            "id": v.id,
            "shopName": v.shop_name,
            "ownerName": v.user.name if v.user else "",
            "phone": v.user.phone if v.user else "",
            "category": v.category,
            "area": v.area_name,
            "status": v.user.status if v.user else "active",
            "isVerified": v.is_verified,
            "walletBalance": v.wallet_balance,
            "totalInvoices": inv_count,
            "totalGMV": round(gmv, 2)
        })

    totalPages = (total + limit - 1) // limit
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendors list fetched",
        data=result,
        meta=Meta(page=page, limit=limit, total=total, totalPages=totalPages)
    )

@router.get("/vendors/{id}", response_model=ApiResponse[dict])
def get_vendor_360(
    id: int,
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    v = db.query(Vendor).filter(Vendor.id == id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")

    products = db.query(Product).filter(Product.vendor_id == v.id).all()
    invoices = db.query(Invoice).filter(Invoice.vendor_id == v.id).order_by(Invoice.created_at.desc()).limit(10).all()
    ledgers = db.query(VendorWalletLedger).filter(VendorWalletLedger.vendor_id == v.id).order_by(VendorWalletLedger.created_at.desc()).limit(10).all()

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendor 360 profile fetched",
        data={
            "vendor": {
                "id": v.id,
                "shopName": v.shop_name,
                "ownerName": v.user.name if v.user else "",
                "phone": v.user.phone if v.user else "",
                "category": v.category,
                "address": v.address,
                "area": v.area_name,
                "walletBalance": v.wallet_balance,
                "isVerified": v.is_verified,
                "nidNumber": v.nid_number,
                "tradeLicense": v.trade_license,
                "status": v.user.status if v.user else "active"
            },
            "productsCount": len(products),
            "recentInvoices": [{"id": i.id, "total": i.total, "commission": i.commission_amount, "date": i.created_at.isoformat() if i.created_at else ""} for i in invoices],
            "walletLedger": [{"id": l.id, "amount": l.amount, "type": l.transaction_type, "desc": l.description} for l in ledgers]
        }
    )

@router.patch("/vendors/{id}/verify-kyc", response_model=ApiResponse[dict])
def verify_vendor_kyc(
    id: int,
    request: VerifyKycRequest,
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    v = db.query(Vendor).filter(Vendor.id == id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    v.is_verified = request.isVerified
    if request.commissionRate is not None:
        v.commission_rate = request.commissionRate
    db.commit()
    db.refresh(v)
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendor KYC status updated successfully",
        data={"vendorId": v.id, "isVerified": v.is_verified, "commissionRate": v.commission_rate}
    )

@router.patch("/vendors/{id}/status", response_model=ApiResponse[dict])
def update_vendor_status(
    id: int,
    request: VendorStatusUpdateRequest,
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    v = db.query(Vendor).filter(Vendor.id == id).first()
    if not v or not v.user:
        raise HTTPException(status_code=404, detail="Vendor not found")
    v.user.status = request.status
    db.commit()
    return ApiResponse(
        success=True,
        statusCode=200,
        message=f"Vendor status changed to {request.status}",
        data={"vendorId": v.id, "status": v.user.status}
    )

# 4. Customer 360° Management
@router.get("/customers", response_model=ApiResponse[List[dict]])
def get_crm_customers(
    search: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    q = db.query(User).filter(User.role == UserRole.CUSTOMER.value)
    if search:
        q = q.filter((User.name.ilike(f"%{search}%")) | (User.phone.ilike(f"%{search}%")))
    if area:
        q = q.filter(User.area_name.ilike(f"%{area}%"))

    total = q.count()
    customers = q.offset((page - 1) * limit).limit(limit).all()

    result = []
    for c in customers:
        inv_count = db.query(Invoice).filter(
            (Invoice.customer_id == c.id) | (Invoice.customer_phone == c.phone)
        ).count()
        ltv = db.query(func.sum(Invoice.total)).filter(
            (Invoice.customer_id == c.id) | (Invoice.customer_phone == c.phone)
        ).scalar() or 0.0

        result.append({
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "area": c.area_name,
            "status": c.status,
            "totalInvoices": inv_count,
            "ltv": round(ltv, 2)
        })

    totalPages = (total + limit - 1) // limit
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Customers list fetched",
        data=result,
        meta=Meta(page=page, limit=limit, total=total, totalPages=totalPages)
    )

@router.get("/customers/{id}", response_model=ApiResponse[dict])
def get_customer_360(
    id: int,
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    c = db.query(User).filter(User.id == id, User.role == UserRole.CUSTOMER.value).first()
    if not c:
        raise HTTPException(status_code=404, detail="Customer not found")

    invoices = db.query(Invoice).filter(
        (Invoice.customer_id == c.id) | (Invoice.customer_phone == c.phone)
    ).order_by(Invoice.created_at.desc()).limit(15).all()

    demands = db.query(SearchRequest).filter(
        (SearchRequest.customer_id == c.id) | (SearchRequest.customer_phone == c.phone)
    ).order_by(SearchRequest.created_at.desc()).limit(10).all()

    tickets = db.query(SupportTicket).filter(
        SupportTicket.creator_id == c.id
    ).order_by(SupportTicket.created_at.desc()).limit(10).all()

    ltv = sum(i.total for i in invoices)

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Customer 360 view fetched",
        data={
            "customer": {
                "id": c.id,
                "name": c.name,
                "phone": c.phone,
                "email": c.email,
                "area": c.area_name,
                "upazila": c.upazila_name,
                "district": c.district_name,
                "division": c.division_name,
                "status": c.status,
                "totalInvoices": len(invoices),
                "ltv": round(ltv, 2)
            },
            "recentInvoices": [{"id": i.id, "total": i.total, "vendor": i.vendor_shop_name, "status": i.status, "date": i.created_at.isoformat() if i.created_at else ""} for i in invoices],
            "searchDemands": [{"id": d.id, "query": d.query_text, "area": d.area_name, "status": d.status} for d in demands],
            "supportTickets": [{"id": t.id, "ticketNumber": t.ticket_number, "subject": t.subject, "status": t.status} for t in tickets]
        }
    )

# 5. Support Tickets & Disputes
@router.get("/tickets", response_model=ApiResponse[List[dict]])
def get_support_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    q = db.query(SupportTicket)
    if status:
        q = q.filter(SupportTicket.status == status)
    if priority:
        q = q.filter(SupportTicket.priority == priority)

    tickets = q.order_by(SupportTicket.created_at.desc()).all()
    result = [
        {
            "id": t.id,
            "ticketNumber": t.ticket_number,
            "subject": t.subject,
            "description": t.description,
            "creatorName": t.creator.name if t.creator else "User",
            "creatorPhone": t.creator.phone if t.creator else "",
            "category": t.category,
            "status": t.status,
            "priority": t.priority,
            "createdAt": t.created_at.isoformat() if t.created_at else ""
        }
        for t in tickets
    ]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Support tickets fetched",
        data=result
    )

@router.post("/tickets/{id}/reply", response_model=ApiResponse[dict], status_code=201)
def reply_support_ticket(
    id: int,
    request: TicketReplyRequest,
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    reply = TicketReply(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        is_internal_note=request.isInternalNote,
        message=request.message
    )
    db.add(reply)
    if ticket.status == "open":
        ticket.status = "in_progress"
    db.commit()

    return ApiResponse(
        success=True,
        statusCode=201,
        message="Ticket reply added",
        data={"ticketId": ticket.id, "message": request.message}
    )

@router.patch("/tickets/{id}/status", response_model=ApiResponse[dict])
def update_ticket_status(
    id: int,
    request: TicketStatusUpdateRequest,
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.status = request.status
    db.commit()
    return ApiResponse(
        success=True,
        statusCode=200,
        message=f"Ticket status changed to {request.status}",
        data={"ticketId": ticket.id, "status": ticket.status}
    )

# 6. Finance & Payout Approvals
@router.get("/payouts", response_model=ApiResponse[List[dict]])
def get_payout_requests(
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    payouts = db.query(PayoutRequest).order_by(PayoutRequest.created_at.desc()).all()
    result = [
        {
            "id": p.id,
            "vendorShop": p.vendor.shop_name if p.vendor else "Vendor",
            "amount": p.amount,
            "paymentMethod": p.payment_method,
            "accountNumber": p.account_number,
            "status": p.status,
            "transactionRef": p.transaction_ref,
            "createdAt": p.created_at.isoformat() if p.created_at else ""
        }
        for p in payouts
    ]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Payout requests fetched",
        data=result
    )

@router.post("/payouts/{id}/approve", response_model=ApiResponse[dict])
def approve_payout(
    id: int,
    request: PayoutApprovalRequest,
    current_user: User = Depends(crm_guard),
    db: Session = Depends(get_db)
):
    p = db.query(PayoutRequest).filter(PayoutRequest.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Payout request not found")

    p.status = "approved"
    p.transaction_ref = request.transactionRef
    p.admin_note = request.adminNote
    p.processed_by = current_user.id
    p.processed_at = datetime.utcnow()
    db.commit()

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Payout approved successfully",
        data={"payoutId": p.id, "status": "approved", "transactionRef": p.transaction_ref}
    )

# 7. Master Location Management
@router.post("/locations/division", response_model=ApiResponse[dict], status_code=201)
def create_division(request: CreateDivisionRequest, current_user: User = Depends(crm_guard), db: Session = Depends(get_db)):
    div = Division(name=request.name)
    db.add(div)
    db.commit()
    db.refresh(div)
    return ApiResponse(success=True, statusCode=201, message="Division created", data={"id": div.id, "name": div.name})

@router.post("/locations/district", response_model=ApiResponse[dict], status_code=201)
def create_district(request: CreateDistrictRequest, current_user: User = Depends(crm_guard), db: Session = Depends(get_db)):
    dist = District(division_id=request.divisionId, name=request.name)
    db.add(dist)
    db.commit()
    db.refresh(dist)
    return ApiResponse(success=True, statusCode=201, message="District created", data={"id": dist.id, "name": dist.name})

@router.post("/locations/upazila", response_model=ApiResponse[dict], status_code=201)
def create_upazila(request: CreateUpazilaRequest, current_user: User = Depends(crm_guard), db: Session = Depends(get_db)):
    up = Upazila(district_id=request.districtId, name=request.name)
    db.add(up)
    db.commit()
    db.refresh(up)
    return ApiResponse(success=True, statusCode=201, message="Upazila created", data={"id": up.id, "name": up.name})

@router.post("/locations/area", response_model=ApiResponse[dict], status_code=201)
def create_area(request: CreateAreaRequest, current_user: User = Depends(crm_guard), db: Session = Depends(get_db)):
    ar = Area(upazila_id=request.upazilaId, name=request.name, latitude=request.latitude, longitude=request.longitude)
    db.add(ar)
    db.commit()
    db.refresh(ar)
    return ApiResponse(success=True, statusCode=201, message="Area created", data={"id": ar.id, "name": ar.name})
