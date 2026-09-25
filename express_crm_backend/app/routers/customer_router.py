import time
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.category import Category
from app.models.search_request import SearchRequest
from app.models.support_ticket import SupportTicket, TicketReply
from app.schemas.common import ApiResponse, Meta
from app.schemas.product import ProductResponse, VendorMarketplaceItem
from app.schemas.category import CategoryResponse
from app.schemas.support_ticket import CreateTicketRequest, TicketDetailResponse
from app.schemas.search_request import SearchDemandCreateRequest, SearchDemandCreateResponse, SearchDemandItem
from app.services.auth_service import get_optional_user, get_current_user
from app.services.websocket_manager import ws_manager


router = APIRouter(prefix="/customer", tags=["Customer Marketplace & Discovery"])

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

@router.get("/vendors", response_model=ApiResponse[List[VendorMarketplaceItem]])
def get_vendors(
    area: Optional[str] = Query(None, description="Area name e.g. Kaliganj Bazar"),
    category: Optional[str] = Query(None, description="Category filter e.g. Electronics"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Vendor).join(User).filter(User.status == "active")
    if area:
        query = query.filter(Vendor.area_name.ilike(f"%{area}%"))
    if category:
        query = query.filter(Vendor.category.ilike(f"%{category}%"))

    total = query.count()
    vendors = query.offset((page - 1) * limit).limit(limit).all()

    result = []
    for v in vendors:
        prod_count = db.query(Product).filter(Product.vendor_id == v.id, Product.is_available == True).count()
        result.append(
            VendorMarketplaceItem(
                id=v.id,
                name=v.user.name if v.user else v.shop_name,
                shopName=v.shop_name,
                phone=v.user.phone if v.user else "",
                category=v.category,
                area=v.area_name or "Kaliganj Bazar",
                address=v.address,
                distanceKm=0.8,
                productCount=prod_count,
                rating=v.rating,
                walletBalance=v.wallet_balance,
                isVerified=v.is_verified
            )
        )

    totalPages = (total + limit - 1) // limit
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendors fetched successfully",
        data=result,
        meta=Meta(page=page, limit=limit, total=total, totalPages=totalPages)
    )

@router.get("/vendors/{vendor_id}/products", response_model=ApiResponse[List[ProductResponse]])
def get_vendor_products(vendor_id: int, db: Session = Depends(get_db)):
    products = db.query(Product).filter(
        Product.vendor_id == vendor_id,
        Product.is_available == True
    ).all()

    result = [format_product_response(p, p.category_rel.commission_rate if p.category_rel else 2.00) for p in products]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendor products fetched successfully",
        data=result
    )

@router.get("/products/search", response_model=ApiResponse[List[ProductResponse]])
def search_products(
    query: str = Query(..., min_length=1, description="Search keyword"),
    area: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    q = db.query(Product).join(Vendor).filter(Product.is_available == True)
    if area:
        q = q.filter(Vendor.area_name.ilike(f"%{area}%"))
    if category:
        q = q.filter(Product.category.ilike(f"%{category}%"))
    
    search_term = f"%{query}%"
    q = q.filter(
        (Product.name.ilike(search_term)) |
        (Product.description.ilike(search_term)) |
        (Product.tags.ilike(search_term))
    )

    total = q.count()
    products = q.offset((page - 1) * limit).limit(limit).all()

    result = [format_product_response(p, p.category_rel.commission_rate if p.category_rel else 2.00) for p in products]
    totalPages = (total + limit - 1) // limit

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Products search results",
        data=result,
        meta=Meta(page=page, limit=limit, total=total, totalPages=totalPages)
    )

@router.post("/search-requests", response_model=ApiResponse[SearchDemandCreateResponse], status_code=201)
async def create_search_demand_request(
    request: SearchDemandCreateRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    req_id = f"req_{int(time.time() * 1000)}"
    new_req = SearchRequest(
        id=req_id,
        query_text=request.query,
        customer_id=current_user.id if current_user else None,
        customer_phone=current_user.phone if current_user else None,
        division_name=request.division,
        district_name=request.district,
        upazila_name=request.upazila,
        area_name=request.area,
        status="unfulfilled"
    )
    db.add(new_req)
    db.commit()

    # Find number of active vendors in that area
    vendors_in_area = db.query(Vendor).filter(Vendor.area_name.ilike(f"%{request.area}%")).count()

    # Real-time WebSocket broadcast to area vendor room & admin CRM
    payload = {
        "requestId": req_id,
        "query": request.query,
        "area": request.area,
        "time": new_req.created_at.isoformat() if new_req.created_at else ""
    }
    await ws_manager.broadcast_to_room(f"room:area:{request.area}", "demand:new_search", payload)
    await ws_manager.broadcast_to_room("room:crm:super_admin", "demand:new_search", payload)

    return ApiResponse(
        success=True,
        statusCode=201,
        message="Search demand recorded and broadcasted to local vendors",
        data=SearchDemandCreateResponse(
            requestId=req_id,
            vendorsNotifiedCount=max(1, vendors_in_area)
        )
    )

@router.get("/categories", response_model=ApiResponse[List[CategoryResponse]])
def get_customer_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).filter(Category.is_active == True).all()
    result = []
    for cat in categories:
        prod_count = db.query(Product).filter(Product.category_id == cat.id, Product.is_available == True).count()
        result.append(
            CategoryResponse(
                id=cat.id,
                name=cat.name,
                slug=cat.slug,
                commissionRate=cat.commission_rate,
                iconUrl=cat.icon_url,
                isActive=cat.is_active,
                totalProducts=prod_count,
                totalRevenueEarned=0.0
            )
        )
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Categories fetched successfully",
        data=result
    )

@router.get("/vendors/{vendor_id}", response_model=ApiResponse[dict])
def get_vendor_detail(vendor_id: int, db: Session = Depends(get_db)):
    v = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")

    products = db.query(Product).filter(Product.vendor_id == v.id, Product.is_available == True).all()
    
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Vendor details fetched",
        data={
            "id": v.id,
            "shopName": v.shop_name,
            "ownerName": v.user.name if v.user else "",
            "phone": v.user.phone if v.user else "",
            "category": v.category,
            "address": v.address,
            "area": v.area_name or "Kaliganj Bazar",
            "rating": v.rating,
            "isVerified": v.is_verified,
            "productCount": len(products),
            "products": [format_product_response(p, v.commission_rate) for p in products]
        }
    )

@router.get("/products/{product_id}", response_model=ApiResponse[ProductResponse])
def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    comm_rate = prod.category_rel.commission_rate if prod.category_rel else 2.00
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Product detail fetched",
        data=format_product_response(prod, comm_rate)
    )

@router.get("/search-requests/my", response_model=ApiResponse[List[SearchDemandItem]])
def get_my_search_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    reqs = db.query(SearchRequest).filter(
        (SearchRequest.customer_id == current_user.id) |
        (SearchRequest.customer_phone == current_user.phone)
    ).order_by(SearchRequest.created_at.desc()).all()

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
        message="My search demand requests fetched",
        data=result
    )

@router.post("/support-tickets", response_model=ApiResponse[dict], status_code=201)
def create_customer_ticket(
    request: CreateTicketRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket_num = f"TCK-{int(time.time() * 1000) % 100000}"
    ticket = SupportTicket(
        ticket_number=ticket_num,
        creator_id=current_user.id,
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
def get_customer_tickets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tickets = db.query(SupportTicket).filter(
        SupportTicket.creator_id == current_user.id
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
        message="Customer support tickets fetched",
        data=result
    )

@router.post("/vendors/{vendor_id}/reviews", response_model=ApiResponse[dict], status_code=201)
def submit_vendor_review(
    vendor_id: int,
    rating: float = Query(5.0, ge=1.0, le=5.0),
    review: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    v = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Update running average rating
    v.rating = round((float(v.rating or 5.0) * 4.0 + rating) / 5.0, 1)
    db.commit()

    return ApiResponse(
        success=True,
        statusCode=201,
        message="Review submitted successfully",
        data={"vendorId": v.id, "newRating": v.rating}
    )

