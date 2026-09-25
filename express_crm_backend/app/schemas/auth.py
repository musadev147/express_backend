from typing import Optional, Any
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    phone: str
    password: str
    role: Optional[str] = None # customer, vendor, super_admin, area_manager, etc.

class RegisterCustomerRequest(BaseModel):
    name: str
    phone: str
    password: str
    division: Optional[str] = "Dhaka"
    district: Optional[str] = "Gazipur"
    upazila: Optional[str] = "Kaliganj"
    area: Optional[str] = "Kaliganj Bazar"

class RegisterVendorRequest(BaseModel):
    name: str
    shopName: str
    phone: str
    email: Optional[str] = None
    password: str
    category: str = "Electronics"
    division: Optional[str] = "Dhaka"
    district: Optional[str] = "Gazipur"
    upazila: Optional[str] = "Kaliganj"
    area: Optional[str] = "Kaliganj Bazar"
    address: str

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    shopName: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    avatarUrl: Optional[str] = None
    fcmToken: Optional[str] = None

class UserProfileResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    role: str
    status: str
    avatarUrl: Optional[str] = None
    
    # Vendor specific details if role is vendor
    shopName: Optional[str] = None
    category: Optional[str] = None
    division: Optional[str] = None
    district: Optional[str] = None
    upazila: Optional[str] = None
    area: Optional[str] = None
    address: Optional[str] = None
    walletBalance: Optional[float] = None
    isVerified: Optional[bool] = None

class RefreshTokenRequest(BaseModel):
    refreshToken: str

class ChangePasswordRequest(BaseModel):
    oldPassword: str
    newPassword: str

class ForgotPasswordRequest(BaseModel):
    phone: str

class ResetPasswordRequest(BaseModel):
    phone: str
    otp: str
    newPassword: str

class AuthResponseData(BaseModel):
    token: str
    refreshToken: str
    user: UserProfileResponse
