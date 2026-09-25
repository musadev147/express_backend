from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class PayoutCreateRequest(BaseModel):
    amount: float
    paymentMethod: str = "bKash" # bKash, Nagad, Rocket, Bank Transfer
    accountNumber: str
    adminNote: Optional[str] = None

class PayoutResponse(BaseModel):
    id: int
    vendorId: int
    vendorShop: str
    amount: float
    paymentMethod: str
    accountNumber: str
    status: str # pending, approved, rejected
    transactionRef: Optional[str] = None
    adminNote: Optional[str] = None
    createdAt: str
    processedAt: Optional[str] = None

class VendorWalletLedgerResponse(BaseModel):
    id: int
    vendorId: int
    invoiceId: Optional[str] = None
    transactionType: str # commission_debit, payout_debit, refund_credit, topup
    amount: float
    balanceBefore: float
    balanceAfter: float
    description: Optional[str] = None
    createdAt: str

class PayoutRejectRequest(BaseModel):
    adminNote: str
