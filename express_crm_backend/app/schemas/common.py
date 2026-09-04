from typing import Generic, TypeVar, Optional, Any, List
from pydantic import BaseModel

T = TypeVar("T")

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str

class Meta(BaseModel):
    page: Optional[int] = None
    limit: Optional[int] = None
    total: Optional[int] = None
    totalPages: Optional[int] = None

class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    statusCode: int = 200
    message: str = "Operation executed successfully"
    data: Optional[T] = None
    meta: Optional[Meta] = None
    errors: Optional[List[ErrorDetail]] = None
