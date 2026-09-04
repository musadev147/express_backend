from typing import Optional
from pydantic import BaseModel

class SearchDemandCreateRequest(BaseModel):
    query: str
    area: str
    upazila: Optional[str] = None
    district: Optional[str] = None
    division: Optional[str] = None

class SearchDemandCreateResponse(BaseModel):
    requestId: str
    vendorsNotifiedCount: int

class SearchDemandItem(BaseModel):
    id: str
    product: str
    area: str
    customerPhone: Optional[str] = None
    time: str
    status: str
