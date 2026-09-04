from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Division(Base):
    __tablename__ = "divisions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)

    districts = relationship("District", back_populates="division", cascade="all, delete-orphan")

class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    division_id = Column(Integer, ForeignKey("divisions.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)

    division = relationship("Division", back_populates="districts")
    upazilas = relationship("Upazila", back_populates="district", cascade="all, delete-orphan")

class Upazila(Base):
    __tablename__ = "upazilas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    district_id = Column(Integer, ForeignKey("districts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)

    district = relationship("District", back_populates="upazilas")
    areas = relationship("Area", back_populates="upazila", cascade="all, delete-orphan")

class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    upazila_id = Column(Integer, ForeignKey("upazilas.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    upazila = relationship("Upazila", back_populates="areas")
