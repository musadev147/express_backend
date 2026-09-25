from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models.category import Category
from app.models.product import Product
from app.models.vendor import Vendor
from app.models.payout import VendorWalletLedger
from app.schemas.invoice import OrderItemInput, InvoiceItemDetail

class CommissionService:
    @staticmethod
    def get_category_rate(db: Session, category_id: Optional[int], category_name: Optional[str] = None) -> float:
        """
        Fetch commission rate for a category. Defaults to 2.00% if not found or inactive.
        """
        if category_id:
            cat = db.query(Category).filter(Category.id == category_id, Category.is_active == True).first()
            if cat:
                return float(cat.commission_rate)
        if category_name:
            cat = db.query(Category).filter(Category.name.ilike(category_name), Category.is_active == True).first()
            if cat:
                return float(cat.commission_rate)
        return float(settings.DEFAULT_COMMISSION_RATE) # Default 2.00%

    @staticmethod
    def calculate_order_commission(
        db: Session,
        items_input: List[OrderItemInput],
        vendor: Optional[Vendor] = None
    ) -> Tuple[List[Dict[str, Any]], float, float]:
        """
        Calculates itemized line totals, category commission snapshots (2%), and total order commission.
        Returns (processed_items_list, subtotal, total_commission).
        """
        processed_items = []
        subtotal = 0.0
        total_commission = 0.0

        for item_in in items_input:
            product = None
            prod_id = item_in.productId if item_in.productId is not None else item_in.id
            if prod_id is not None:
                try:
                    product = db.query(Product).filter(Product.id == int(prod_id)).first()
                except (ValueError, TypeError):
                    product = None

            if product:
                item_name = item_in.name or product.name
                item_price = float(item_in.price) if item_in.price is not None else float(product.price)
                category_id = product.category_id
                category_name = product.category or "General"
                
                # Fetch category commission rate (e.g. 2.00%)
                comm_rate = CommissionService.get_category_rate(db, category_id, category_name)
            else:
                item_name = item_in.name or "Custom Product"
                item_price = float(item_in.price or 0.0)
                category_id = None
                category_name = "General"
                comm_rate = float(settings.DEFAULT_COMMISSION_RATE) # 2.00%


            qty = max(1, item_in.qty)
            line_total = round(item_price * qty, 2)
            item_commission = round(line_total * (comm_rate / 100.0), 2)

            subtotal += line_total
            total_commission += item_commission

            processed_items.append({
                "product_id": product.id if product else None,
                "product_name": item_name,
                "category_id": category_id,
                "category_name": category_name,
                "commission_rate": comm_rate,
                "commission_amount": item_commission,
                "price": item_price,
                "quantity": qty,
                "line_total": line_total
            })

        subtotal = round(subtotal, 2)
        total_commission = round(total_commission, 2)
        return processed_items, subtotal, total_commission

    @staticmethod
    def deduct_vendor_commission(
        db: Session,
        vendor: Vendor,
        invoice_id: str,
        commission_amount: float
    ) -> float:
        """
        Deducts the 2% category commission from the vendor's wallet balance
        and writes an audit record to vendor_wallet_ledger.
        Returns the updated wallet balance.
        """
        if not vendor or commission_amount <= 0:
            return vendor.wallet_balance if vendor else 0.0

        current_balance = float(vendor.wallet_balance or 0.0)
        new_balance = round(current_balance - commission_amount, 2)
        
        vendor.wallet_balance = new_balance
        
        ledger_entry = VendorWalletLedger(
            vendor_id=vendor.id,
            invoice_id=invoice_id,
            transaction_type="commission_debit",
            amount=commission_amount,
            balance_before=current_balance,
            balance_after=new_balance,
            description=f"2% Category platform commission deducted for order {invoice_id}"
        )
        db.add(ledger_entry)
        db.commit()
        db.refresh(vendor)
        return new_balance
