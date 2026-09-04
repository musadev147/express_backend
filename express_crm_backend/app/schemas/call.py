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
