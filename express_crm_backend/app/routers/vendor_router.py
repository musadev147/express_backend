from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.category import Category
from app.models.invoice import Invoice
from app.models.search_request import SearchRequest
from app.models.payout import PayoutRequest, VendorWalletLedger
from app.models.support_ticket import SupportTicket, TicketReply
from app.schemas.common import ApiResponse
from app.schemas.product import (
    ProductCreateRequest, ProductUpdateRequest, ProductToggleStockRequest, ProductResponse
)
from app.schemas.search_request import SearchDemandItem
from app.schemas.payout import PayoutCreateRequest, PayoutResponse, VendorWalletLedgerResponse
from app.schemas.support_ticket import CreateTicketRequest, TicketDetailResponse
from app.services.auth_service import get_current_user, require_roles


router = APIRouter(prefix="/vendor", tags=["Vendor Shop & Inventory"])

def format_product_response(p: Product, cat_rate: float = 2.00) -> ProductResponse:
    tags_list = [t.strip() for t in p.tags.split(",") if t.strip()] if p.tags else []
    return ProductResponse(
        id=p.id,
        vendorId=p.vendor_id,
        name=p.name,
        category=p.category,
        categoryId=p.category_id,
        commissionRate=cat_rate,
        description=p.description,
        price=p.price,
        stock=p.stock,
        unit=p.unit,
        isAvailable=p.is_available,
        tags=tags_list,
        imageUrl=p.image_url
    )

def get_current_vendor(
    current_user: User = Depends(require_roles([UserRole.VENDOR.value, UserRole.SUPER_ADMIN.value])),
    db: Session = Depends(get_db)
) -> Vendor:
    vendor = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()
    if not vendor and current_user.role == UserRole.SUPER_ADMIN.value:
        # Fallback to first vendor for super admin testing
        vendor = db.query(Vendor).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor profile not found for current user"
        )
    return vendor

@router.get("/dashboard-summary", response_model=ApiResponse[dict])
def get_dashboard_summary(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    today = date.today()
    today_invoices = db.query(Invoice).filter(
        Invoice.vendor_id == vendor.id,
        Invoice.created_at >= datetime(today.year, today.month, today.day)
    ).all()
    
    today_sales = sum(inv.total for inv in today_invoices)
    total_invoices_count = db.query(Invoice).filter(Invoice.vendor_id == vendor.id).count()
    total_products_count = db.query(Product).filter(Product.vendor_id == vendor.id).count()
    
    unfulfilled_demands = db.query(SearchRequest).filter(
        SearchRequest.area_name.ilike(f"%{vendor.area_name or ''}%"),
        SearchRequest.status == "unfulfilled"
    ).count()

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendor dashboard summary fetched",
        data={
            "todaySales": round(today_sales, 2),
            "totalInvoices": total_invoices_count,
            "totalProducts": total_products_count,
            "unfulfilledSearchRequests": unfulfilled_demands,
            "walletBalance": round(vendor.wallet_balance, 2)
        }
    )

@router.get("/products", response_model=ApiResponse[List[ProductResponse]])
def get_vendor_catalog(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.vendor_id == vendor.id).all()
    result = [format_product_response(p, p.category_rel.commission_rate if p.category_rel else 2.00) for p in products]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendor catalog fetched",
        data=result
    )

@router.post("/products", response_model=ApiResponse[ProductResponse], status_code=201)
def add_product(
    request: ProductCreateRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    cat = None
    if request.categoryId:
        cat = db.query(Category).filter(Category.id == request.categoryId).first()
    if not cat:
        cat = db.query(Category).filter(Category.name.ilike(request.category)).first()

    tags_str = ",".join(request.tags) if request.tags else ""

    new_prod = Product(
        vendor_id=vendor.id,
        category_id=cat.id if cat else None,
        name=request.name,
        category=cat.name if cat else request.category,
        description=request.description,
        price=request.price,
        stock=request.stock,
        unit=request.unit,
        is_available=request.isAvailable,
        tags=tags_str,
        image_url=request.imageUrl
    )
    db.add(new_prod)
    db.commit()
    db.refresh(new_prod)

    comm_rate = cat.commission_rate if cat else 2.00
    return ApiResponse(
        success=True,
        statusCode=201,
        message="Product created successfully",
        data=format_product_response(new_prod, comm_rate)
    )

@router.put("/products/{id}", response_model=ApiResponse[ProductResponse])
def update_product(
    id: int,
    request: ProductUpdateRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    prod = db.query(Product).filter(Product.id == id, Product.vendor_id == vendor.id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    if request.name is not None:
        prod.name = request.name
    if request.price is not None:
        prod.price = request.price
    if request.stock is not None:
        prod.stock = request.stock
    if request.unit is not None:
        prod.unit = request.unit
    if request.description is not None:
        prod.description = request.description
    if request.isAvailable is not None:
        prod.is_available = request.isAvailable
    if request.tags is not None:
        prod.tags = ",".join(request.tags)
    if request.imageUrl is not None:
        prod.image_url = request.imageUrl
    if request.categoryId is not None:
        cat = db.query(Category).filter(Category.id == request.categoryId).first()
        if cat:
            prod.category_id = cat.id
            prod.category = cat.name

    db.commit()
    db.refresh(prod)
    comm_rate = prod.category_rel.commission_rate if prod.category_rel else 2.00
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Product updated successfully",
        data=format_product_response(prod, comm_rate)
    )

@router.patch("/products/{id}/toggle-stock", response_model=ApiResponse[ProductResponse])
def toggle_stock(
    id: int,
    request: ProductToggleStockRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    prod = db.query(Product).filter(Product.id == id, Product.vendor_id == vendor.id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    prod.is_available = request.isAvailable
    db.commit()
    db.refresh(prod)
    comm_rate = prod.category_rel.commission_rate if prod.category_rel else 2.00
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Product availability toggled",
        data=format_product_response(prod, comm_rate)
    )

@router.delete("/products/{id}", response_model=ApiResponse[dict])
def delete_product(
    id: int,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    prod = db.query(Product).filter(Product.id == id, Product.vendor_id == vendor.id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(prod)
    db.commit()
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Product deleted successfully",
        data={"deletedId": id}
    )

@router.get("/search-requests", response_model=ApiResponse[List[SearchDemandItem]])
def get_area_search_requests(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    reqs = db.query(SearchRequest).filter(
        SearchRequest.area_name.ilike(f"%{vendor.area_name or ''}%")
    ).order_by(SearchRequest.created_at.desc()).limit(50).all()

    result = [
        SearchDemandItem(
            id=r.id,
            product=r.query_text,
            area=r.area_name,
            customerPhone=r.customer_phone,
            time=r.created_at.isoformat() if r.created_at else "",
            status=r.status
        )
        for r in reqs
    ]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Area search requests fetched",
        data=result
    )

@router.post("/payouts/request", response_model=ApiResponse[dict], status_code=201)
def request_payout(
    request: PayoutCreateRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Payout amount must be greater than zero")
    if vendor.wallet_balance < request.amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient wallet balance. Current: ৳{vendor.wallet_balance:.2f}, Requested: ৳{request.amount:.2f}"
        )

    # Debit vendor wallet immediately and record pending payout
    current_balance = float(vendor.wallet_balance)
    new_balance = round(current_balance - request.amount, 2)
    vendor.wallet_balance = new_balance

    payout = PayoutRequest(
        vendor_id=vendor.id,
        amount=request.amount,
        payment_method=request.paymentMethod,
        account_number=request.accountNumber,
        status="pending",
        admin_note=request.adminNote
    )
    db.add(payout)
    db.commit()
    db.refresh(payout)

    ledger_entry = VendorWalletLedger(
        vendor_id=vendor.id,
        invoice_id=None,
        transaction_type="payout_debit",
        amount=request.amount,
        balance_before=current_balance,
        balance_after=new_balance,
        description=f"Withdrawal request #{payout.id} via {request.paymentMethod} ({request.accountNumber})"
    )
    db.add(ledger_entry)
    db.commit()

    return ApiResponse(
        success=True,
        statusCode=201,
        message="Payout request submitted successfully",
        data={
            "payoutId": payout.id,
            "amount": payout.amount,
            "status": payout.status,
            "updatedWalletBalance": vendor.wallet_balance
        }
    )

@router.get("/payouts", response_model=ApiResponse[List[PayoutResponse]])
def get_vendor_payouts(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    payouts = db.query(PayoutRequest).filter(PayoutRequest.vendor_id == vendor.id).order_by(PayoutRequest.created_at.desc()).all()
    result = [
        PayoutResponse(
            id=p.id,
            vendorId=p.vendor_id,
            vendorShop=vendor.shop_name,
            amount=p.amount,
            paymentMethod=p.payment_method,
            accountNumber=p.account_number,
            status=p.status,
            transactionRef=p.transaction_ref,
            adminNote=p.admin_note,
            createdAt=p.created_at.isoformat() if p.created_at else "",
            processedAt=p.processed_at.isoformat() if p.processed_at else None
        )
        for p in payouts
    ]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendor payouts history fetched",
        data=result
    )

@router.get("/wallet-ledger", response_model=ApiResponse[List[VendorWalletLedgerResponse]])
def get_vendor_wallet_ledger(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    ledgers = db.query(VendorWalletLedger).filter(
        VendorWalletLedger.vendor_id == vendor.id
    ).order_by(VendorWalletLedger.created_at.desc()).all()

    result = [
        VendorWalletLedgerResponse(
            id=l.id,
            vendorId=l.vendor_id,
            invoiceId=l.invoice_id,
            transactionType=l.transaction_type,
            amount=l.amount,
            balanceBefore=l.balance_before,
            balanceAfter=l.balance_after,
            description=l.description,
            createdAt=l.created_at.isoformat() if l.created_at else ""
        )
        for l in ledgers
    ]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendor wallet ledger history fetched",
        data=result
    )

@router.get("/invoices", response_model=ApiResponse[List[dict]])
def get_vendor_invoices(
    status: Optional[str] = None,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    q = db.query(Invoice).filter(Invoice.vendor_id == vendor.id)
    if status:
        q = q.filter(Invoice.status == status)
    invoices = q.order_by(Invoice.created_at.desc()).all()

    result = [
        {
            "id": inv.id,
            "customerName": inv.customer_name,
            "customerPhone": inv.customer_phone,
            "subtotal": inv.subtotal,
            "discount": inv.discount,
            "commissionAmount": inv.commission_amount,
            "total": inv.total,
            "status": inv.status,
            "paymentMethod": inv.payment_method,
            "createdAt": inv.created_at.isoformat() if inv.created_at else ""
        }
        for inv in invoices
    ]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendor invoices fetched successfully",
        data=result
    )

@router.get("/profile", response_model=ApiResponse[dict])
def get_vendor_profile(vendor: Vendor = Depends(get_current_vendor)):
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendor profile fetched",
        data={
            "id": vendor.id,
            "userId": vendor.user_id,
            "shopName": vendor.shop_name,
            "ownerName": vendor.user.name if vendor.user else "",
            "phone": vendor.user.phone if vendor.user else "",
            "email": vendor.user.email if vendor.user else "",
            "category": vendor.category,
            "address": vendor.address,
            "division": vendor.division_name,
            "district": vendor.district_name,
            "upazila": vendor.upazila_name,
            "area": vendor.area_name,
            "walletBalance": vendor.wallet_balance,
            "commissionRate": vendor.commission_rate,
            "isVerified": vendor.is_verified,
            "nidNumber": vendor.nid_number,
            "tradeLicense": vendor.trade_license,
            "rating": vendor.rating
        }
    )

@router.put("/profile", response_model=ApiResponse[dict])
def update_vendor_profile(
    request: dict,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    if "shopName" in request:
        vendor.shop_name = request["shopName"]
    if "address" in request:
        vendor.address = request["address"]
    if "nidNumber" in request:
        vendor.nid_number = request["nidNumber"]
    if "tradeLicense" in request:
        vendor.trade_license = request["tradeLicense"]
    if "category" in request:
        vendor.category = request["category"]

    db.commit()
    db.refresh(vendor)

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendor profile updated successfully",
        data={
            "id": vendor.id,
            "shopName": vendor.shop_name,
            "address": vendor.address,
            "nidNumber": vendor.nid_number,
            "tradeLicense": vendor.trade_license
        }
    )

@router.post("/support-tickets", response_model=ApiResponse[dict], status_code=201)
def create_vendor_ticket(
    request: CreateTicketRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: Session = Depends(get_db)
):
    ticket_num = f"TCK-{int(datetime.utcnow().timestamp()) % 100000}"
    ticket = SupportTicket(
        ticket_number=ticket_num,
        creator_id=vendor.user_id,
        subject=request.subject,
        description=request.description,
        category=request.category,
        priority=request.priority,
        status="open"
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ApiResponse(
        success=True,
        statusCode=201,
        message="Support ticket created successfully",
        data={"ticketId": ticket.id, "ticketNumber": ticket.ticket_number, "status": ticket.status}
    )

@router.get("/support-tickets", response_model=ApiResponse[List[dict]])
def get_vendor_tickets(vendor: Vendor = Depends(get_current_vendor), db: Session = Depends(get_db)):
    tickets = db.query(SupportTicket).filter(
        SupportTicket.creator_id == vendor.user_id
    ).order_by(SupportTicket.created_at.desc()).all()

    result = [
        {
            "id": t.id,
            "ticketNumber": t.ticket_number,
            "subject": t.subject,
            "description": t.description,
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
        message="Vendor support tickets fetched",
        data=result
    )

