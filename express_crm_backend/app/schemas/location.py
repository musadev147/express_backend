from typing import List, Optional
from pydantic import BaseModel

class AreaItem(BaseModel):
    id: int
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class UpazilaItem(BaseModel):
    id: int
    name: str
    areas: List[AreaItem] = []

class DistrictItem(BaseModel):
    id: int
    name: str
    upazilas: List[UpazilaItem] = []

class DivisionItem(BaseModel):
    id: int
    name: str
    districts: List[DistrictItem] = []

class LocationHierarchyResponse(BaseModel):
    divisions: List[DivisionItem] = []

class ReverseGeocodeRequest(BaseModel):
    latitude: float
    longitude: float

class ReverseGeocodeResponse(BaseModel):
    division: str
    district: str
    upazila: str
    area: str
    distanceKm: Optional[float] = 0.0

class CreateDivisionRequest(BaseModel):
    name: str

class CreateDistrictRequest(BaseModel):
    divisionId: int
    name: str

class CreateUpazilaRequest(BaseModel):
    districtId: int
    name: str

class CreateAreaRequest(BaseModel):
    upazilaId: int
    name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class SimpleLocationItem(BaseModel):
    id: int
    name: str
    parentId: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

