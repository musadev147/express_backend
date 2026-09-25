from typing import Optional, List
from pydantic import BaseModel

class CreateTicketRequest(BaseModel):
    subject: str
    description: str
    category: Optional[str] = "Order Dispute" # Order Dispute, Billing Issue, Technical Issue, General
    priority: Optional[str] = "medium" # low, medium, high, urgent

class AddTicketMessageRequest(BaseModel):
    message: str

class TicketMessageResponse(BaseModel):
    id: int
    ticketId: int
    senderId: int
    senderName: str
    senderRole: str
    isInternalNote: bool
    message: str
    createdAt: str

class TicketDetailResponse(BaseModel):
    id: int
    ticketNumber: str
    creatorId: int
    creatorName: str
    creatorPhone: str
    creatorRole: str
    subject: str
    description: str
    category: Optional[str] = None
    status: str
    priority: str
    createdAt: str
    replies: List[TicketMessageResponse] = []
