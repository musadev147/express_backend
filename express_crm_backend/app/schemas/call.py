from typing import Optional
from pydantic import BaseModel

class CallInitiateRequest(BaseModel):
    receiverPhone: str
    receiverName: Optional[str] = None
    receiverShopName: Optional[str] = None
    receiverArea: Optional[str] = None
    productName: Optional[str] = None

class CallInitiateResponse(BaseModel):
    callId: str
    status: str
    callerPhone: str
    receiverPhone: str
    productName: Optional[str] = None

class CallEndRequest(BaseModel):
    durationSeconds: int = 0
    status: str = "completed"
    invoiceId: Optional[str] = None

class CallCartSyncRequest(BaseModel):
    callId: str
    items: list = []

class CallLogResponse(BaseModel):
    id: str
    callerId: int
    callerName: str
    callerPhone: str
    callerRole: str
    receiverId: Optional[int] = None
    receiverName: str
    receiverPhone: str
    receiverShopName: Optional[str] = None
    receiverArea: Optional[str] = None
    productName: Optional[str] = None
    status: str
    durationSeconds: int = 0
    invoiceId: Optional[str] = None
    createdAt: str
    endedAt: Optional[str] = None

