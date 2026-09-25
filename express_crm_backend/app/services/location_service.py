import math
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session, joinedload
from app.models.location import Division, District, Upazila, Area
from app.schemas.location import LocationHierarchyResponse, DivisionItem, DistrictItem, UpazilaItem, AreaItem

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class LocationService:
    @staticmethod
    def get_full_hierarchy(db: Session) -> Dict[str, Any]:
        divisions = db.query(Division).options(
            joinedload(Division.districts)
            .joinedload(District.upazilas)
            .joinedload(Upazila.areas)
        ).all()

        division_items = []
        for div in divisions:
            dist_items = []
            for dist in div.districts:
                up_items = []
                for up in dist.upazilas:
                    ar_items = [
                        AreaItem(id=ar.id, name=ar.name, latitude=ar.latitude, longitude=ar.longitude)
                        for ar in up.areas
                    ]
                    up_items.append(UpazilaItem(id=up.id, name=up.name, areas=ar_items))
                dist_items.append(DistrictItem(id=dist.id, name=dist.name, upazilas=up_items))
            division_items.append(DivisionItem(id=div.id, name=div.name, districts=dist_items))

        return {"divisions": division_items}

    @staticmethod
    def reverse_geocode(db: Session, lat: float, lng: float) -> Dict[str, Any]:
        areas = db.query(Area).join(Upazila).join(District).join(Division).all()
        if not areas:
            return {
                "division": "Dhaka",
                "district": "Gazipur",
                "upazila": "Kaliganj",
                "area": "Kaliganj Bazar",
                "distanceKm": 0.0
            }

        closest_area = None
        min_dist = float("inf")

        for ar in areas:
            if ar.latitude is not None and ar.longitude is not None:
                dist = haversine_distance(lat, lng, ar.latitude, ar.longitude)
                if dist < min_dist:
                    min_dist = dist
                    closest_area = ar

        if not closest_area:
            closest_area = areas[0]
            min_dist = 0.5

        upazila = closest_area.upazila
        district = upazila.district if upazila else None
        division = district.division if district else None

        return {
            "division": division.name if division else "Dhaka",
            "district": district.name if district else "Gazipur",
            "upazila": upazila.name if upazila else "Kaliganj",
            "area": closest_area.name,
            "distanceKm": round(min_dist, 2)
        }

    @staticmethod
    def get_divisions(db: Session) -> List[Division]:
        return db.query(Division).order_by(Division.name.asc()).all()

    @staticmethod
    def get_districts(db: Session, division_id: Optional[int] = None) -> List[District]:
        q = db.query(District)
        if division_id:
            q = q.filter(District.division_id == division_id)
        return q.order_by(District.name.asc()).all()

    @staticmethod
    def get_upazilas(db: Session, district_id: Optional[int] = None) -> List[Upazila]:
        q = db.query(Upazila)
        if district_id:
            q = q.filter(Upazila.district_id == district_id)
        return q.order_by(Upazila.name.asc()).all()

    @staticmethod
    def get_areas(db: Session, upazila_id: Optional[int] = None) -> List[Area]:
        q = db.query(Area)
        if upazila_id:
            q = q.filter(Area.upazila_id == upazila_id)
        return q.order_by(Area.name.asc()).all()

