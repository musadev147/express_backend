from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.location import LocationHierarchyResponse, ReverseGeocodeRequest, ReverseGeocodeResponse
from app.services.location_service import LocationService

router = APIRouter(prefix="/locations", tags=["Location & Geofencing"])

@router.get("/hierarchy", response_model=ApiResponse[LocationHierarchyResponse])
def get_hierarchy(db: Session = Depends(get_db)):
    data = LocationService.get_full_hierarchy(db)
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Location hierarchy fetched successfully",
        data=LocationHierarchyResponse(**data)
    )

@router.post("/reverse-geocode", response_model=ApiResponse[ReverseGeocodeResponse])
def reverse_geocode(request: ReverseGeocodeRequest, db: Session = Depends(get_db)):
    result = LocationService.reverse_geocode(db, request.latitude, request.longitude)
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Coordinates reverse-geocoded successfully",
        data=ReverseGeocodeResponse(**result)
    )
