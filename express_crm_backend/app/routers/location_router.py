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

@router.get("/divisions", response_model=ApiResponse[list])
def get_divisions(db: Session = Depends(get_db)):
    divisions = LocationService.get_divisions(db)
    result = [{"id": d.id, "name": d.name} for d in divisions]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Divisions fetched successfully",
        data=result
    )

@router.get("/districts", response_model=ApiResponse[list])
def get_districts(division_id: int = None, db: Session = Depends(get_db)):
    districts = LocationService.get_districts(db, division_id)
    result = [{"id": d.id, "name": d.name, "divisionId": d.division_id} for d in districts]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Districts fetched successfully",
        data=result
    )

@router.get("/upazilas", response_model=ApiResponse[list])
def get_upazilas(district_id: int = None, db: Session = Depends(get_db)):
    upazilas = LocationService.get_upazilas(db, district_id)
    result = [{"id": u.id, "name": u.name, "districtId": u.district_id} for u in upazilas]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Upazilas fetched successfully",
        data=result
    )

@router.get("/areas", response_model=ApiResponse[list])
def get_areas(upazila_id: int = None, db: Session = Depends(get_db)):
    areas = LocationService.get_areas(db, upazila_id)
    result = [{"id": a.id, "name": a.name, "upazilaId": a.upazila_id, "latitude": a.latitude, "longitude": a.longitude} for a in areas]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Areas fetched successfully",
        data=result
    )

