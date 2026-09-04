import time
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.vendor import Vendor
from app.models.product import Product
from app.models.category import Category
from app.models.search_request import SearchRequest
from app.schemas.common import ApiResponse, Meta
from app.schemas.product import ProductResponse, VendorMarketplaceItem
from app.schemas.search_request import SearchDemandCreateRequest, SearchDemandCreateResponse
from app.services.auth_service import get_optional_user
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
