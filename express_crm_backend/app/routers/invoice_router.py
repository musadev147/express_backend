import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.vendor import Vendor
from app.models.invoice import Invoice, InvoiceItem
from app.schemas.common import ApiResponse
from app.schemas.invoice import InvoiceCreateRequest, InvoiceResponse, InvoiceItemDetail
from app.services.auth_service import get_current_user, get_optional_user
from app.services.commission_service import CommissionService
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/invoices", tags=["Invoices, Billing & 2% Category Commission Engine"])

def format_invoice_response(inv: Invoice, vendor_deduction: float = None, updated_balance: float = None) -> InvoiceResponse:
    items_detail = [
        InvoiceItemDetail(
            id=item.id,
            productId=item.product_id,
            name=item.product_name,
            category=item.category_name,
            price=item.price,
            qty=item.quantity,
            lineTotal=item.line_total,
            commissionRate=item.commission_rate,
            commissionAmount=item.commission_amount
        )
        for item in inv.items
    ]
    return InvoiceResponse(
        id=inv.id,
        customerPhone=inv.customer_phone,
        customerName=inv.customer_name,
        vendorPhone=inv.vendor_phone,
        vendorShopName=inv.vendor_shop_name,
        vendorArea=inv.vendor_area,
        items=items_detail,
        subtotal=inv.subtotal,
        discount=inv.discount,
        commissionAmount=inv.commission_amount, # Total 2% category commission
        total=inv.total,
        status=inv.status,
        paymentMethod=inv.payment_method,
        callId=inv.call_id,
        dateTime=inv.created_at.isoformat() if inv.created_at else "",
        pdfDownloadUrl=f"http://localhost:8000/api/v1/invoices/{inv.id}/pdf",
        vendorWalletDeduction=vendor_deduction,
        vendorUpdatedWalletBalance=updated_balance
    )

@router.post("/create", response_model=ApiResponse[InvoiceResponse], status_code=201)
async def create_invoice(
    request: InvoiceCreateRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    # Locate vendor
    vendor = None
    if request.vendorId:
        vendor = db.query(Vendor).filter(Vendor.id == request.vendorId).first()
    elif request.vendorPhone:
        vendor = db.query(Vendor).join(User).filter(User.phone == request.vendorPhone).first()
    elif current_user and current_user.role == UserRole.VENDOR.value:
        vendor = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()

    if not vendor:
        # Fallback to default demo vendor if not found
        vendor = db.query(Vendor).first()
        if not vendor:
            raise HTTPException(status_code=400, detail="No vendor found to associate with invoice")

    # Calculate itemized line totals, 2% category commissions, and grand total
    processed_items, subtotal, total_commission = CommissionService.calculate_order_commission(
        db, request.items, vendor
    )

    discount = max(0.0, request.discount)
    total = round(max(0.0, subtotal - discount), 2)
    inv_id = f"INV-{int(time.time() * 1000) % 1000000}"

    new_invoice = Invoice(
        id=inv_id,
        customer_id=current_user.id if current_user and current_user.role == UserRole.CUSTOMER.value else None,
        customer_name=request.customerName,
        customer_phone=request.customerPhone,
        vendor_id=vendor.id,
        vendor_shop_name=vendor.shop_name,
        vendor_phone=vendor.user.phone if vendor.user else request.vendorPhone or "01711111111",
        vendor_area=vendor.area_name or request.vendorArea or "Kaliganj Bazar",
        subtotal=subtotal,
        discount=discount,
        commission_amount=total_commission, # Total 2% category commission
        total=total,
        status="completed",
        payment_method=request.paymentMethod,
        call_id=request.callId
    )
    db.add(new_invoice)
    db.commit()

    # Save invoice line items with category commission snapshots
    for item_data in processed_items:
        db_item = InvoiceItem(
            invoice_id=inv_id,
            product_id=item_data["product_id"],
            product_name=item_data["product_name"],
            category_id=item_data["category_id"],
            category_name=item_data["category_name"],
            commission_rate=item_data["commission_rate"], # e.g. 2.00%
            commission_amount=item_data["commission_amount"],
            price=item_data["price"],
            quantity=item_data["quantity"],
            line_total=item_data["line_total"]
        )
        db.add(db_item)
    db.commit()
    db.refresh(new_invoice)

    # Automatically deduct 2% platform commission from Vendor's platform wallet
    updated_balance = CommissionService.deduct_vendor_commission(
        db, vendor, inv_id, total_commission
    )

    response_data = format_invoice_response(new_invoice, total_commission, updated_balance)

    # Real-time WebSocket notifications
    # 1. To customer room and vendor room
    if request.callId:
        await ws_manager.broadcast_all("call:invoice_created", {
            "callId": request.callId,
            "invoice": response_data.model_dump()
        })
    # 2. Live feed update to CRM Admin
    await ws_manager.broadcast_to_room("room:crm:super_admin", "crm:order_created", {
        "invoiceId": inv_id,
        "vendorShop": vendor.shop_name,
        "customerName": request.customerName,
        "total": total,
        "commission": total_commission
    })

    return ApiResponse(
        success=True,
        statusCode=201,
        message="Invoice generated successfully with 2% category commission deduction",
        data=response_data
    )

@router.get("", response_model=ApiResponse[List[InvoiceResponse]])
def get_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Invoice)
    if current_user.role == UserRole.CUSTOMER.value:
        query = query.filter(
            (Invoice.customer_id == current_user.id) |
            (Invoice.customer_phone == current_user.phone)
        )
    elif current_user.role == UserRole.VENDOR.value:
        vendor = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()
        if vendor:
            query = query.filter(Invoice.vendor_id == vendor.id)

    invoices = query.order_by(Invoice.created_at.desc()).all()
    result = [format_invoice_response(inv) for inv in invoices]

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Invoices fetched successfully",
        data=result
    )

@router.get("/{id}", response_model=ApiResponse[InvoiceResponse])
def get_invoice_by_id(id: str, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Invoice fetched successfully",
        data=format_invoice_response(inv)
    )

@router.get("/{id}/pdf", response_class=HTMLResponse)
def get_invoice_pdf_view(id: str, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    items_rows = ""
    for item in inv.items:
        items_rows += f"""
        <tr>
            <td style="padding:10px; border-bottom:1px solid #eee;">{item.product_name} <br><small style="color:#666;">({item.category_name} - 2% Platform Commission: ৳{item.commission_amount:.2f})</small></td>
            <td style="padding:10px; border-bottom:1px solid #eee; text-align:center;">{item.quantity}</td>
            <td style="padding:10px; border-bottom:1px solid #eee; text-align:right;">৳{item.price:.2f}</td>
            <td style="padding:10px; border-bottom:1px solid #eee; text-align:right; font-weight:bold;">৳{item.line_total:.2f}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Invoice {inv.id} - Express Platform</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background:#f4f6f8; margin:0; padding:20px; }}
            .invoice-card {{ max-width:650px; margin:20px auto; background:#fff; border-radius:12px; padding:30px; box-shadow:0 4px 20px rgba(0,0,0,0.08); }}
            .header {{ display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #6366f1; padding-bottom:15px; margin-bottom:20px; }}
            .brand {{ font-size:24px; font-weight:800; color:#6366f1; }}
            .meta {{ text-align:right; font-size:13px; color:#555; }}
            .party-info {{ display:flex; justify-content:space-between; margin-bottom:25px; font-size:14px; line-height:1.6; }}
            table {{ width:100%; border-collapse:collapse; margin-bottom:20px; }}
            th {{ background:#f8fafc; padding:10px; font-size:13px; text-transform:uppercase; color:#475569; border-bottom:1px solid #cbd5e1; }}
            .totals {{ margin-left:auto; width:260px; font-size:14px; line-height:1.8; }}
            .totals-row {{ display:flex; justify-content:space-between; }}
            .grand-total {{ font-size:18px; font-weight:bold; color:#0f172a; border-top:2px solid #0f172a; padding-top:6px; margin-top:6px; }}
            .footer {{ text-align:center; font-size:12px; color:#94a3b8; margin-top:30px; border-top:1px solid #eee; padding-top:15px; }}
        </style>
    </head>
    <body>
        <div class="invoice-card">
            <div class="header">
                <div>
                    <div class="brand">EXPRESS</div>
                    <div style="font-size:12px; color:#64748b;">Unified Marketplace & In-Call Order</div>
                </div>
                <div class="meta">
                    <strong style="font-size:16px; color:#1e293b;">{inv.id}</strong><br>
                    Date: {inv.created_at.strftime('%d %b %Y, %I:%M %p') if inv.created_at else ''}<br>
                    Status: <span style="color:#10b981; font-weight:bold;">{inv.status.upper()}</span>
                </div>
            </div>

            <div class="party-info">
                <div>
                    <strong style="color:#334155;">Customer:</strong><br>
                    {inv.customer_name}<br>
                    Phone: {inv.customer_phone}
                </div>
                <div style="text-align:right;">
                    <strong style="color:#334155;">Merchant / Shop:</strong><br>
                    {inv.vendor_shop_name}<br>
                    Area: {inv.vendor_area}<br>
                    Phone: {inv.vendor_phone}
                </div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th style="text-align:left;">Product & Category</th>
                        <th style="text-align:center;">Qty</th>
                        <th style="text-align:right;">Price</th>
                        <th style="text-align:right;">Line Total</th>
                    </tr>
                </thead>
                <tbody>
                    {items_rows}
                </tbody>
            </table>

            <div class="totals">
                <div class="totals-row">
                    <span>Subtotal:</span>
                    <span>৳{inv.subtotal:.2f}</span>
                </div>
                <div class="totals-row">
                    <span>Discount:</span>
                    <span>-৳{inv.discount:.2f}</span>
                </div>
                <div class="totals-row" style="color:#6366f1; font-size:13px;">
                    <span>2% Category Commission:</span>
                    <span>৳{inv.commission_amount:.2f}</span>
                </div>
                <div class="totals-row grand-total">
                    <span>Total Payable:</span>
                    <span>৳{inv.total:.2f}</span>
                </div>
            </div>

            <div class="footer">
                Payment Method: <strong>{inv.payment_method}</strong> | Thank you for using Express Platform!
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
