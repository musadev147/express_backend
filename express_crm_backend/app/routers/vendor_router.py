from typing import List
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
from app.schemas.common import ApiResponse
from app.schemas.product import (
    ProductCreateRequest, ProductUpdateRequest, ProductToggleStockRequest, ProductResponse
)
from app.schemas.search_request import SearchDemandItem
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
