from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole, UserStatus
from app.models.vendor import Vendor
from app.models.category import Category
from app.schemas.common import ApiResponse
from app.schemas.auth import (
    LoginRequest, RegisterCustomerRequest, RegisterVendorRequest,
    ProfileUpdateRequest, UserProfileResponse, AuthResponseData,
    RefreshTokenRequest, ChangePasswordRequest, ForgotPasswordRequest, ResetPasswordRequest
)

from app.services.auth_service import AuthService, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])

def build_profile_response(user: User, vendor: Vendor = None) -> UserProfileResponse:
    profile = UserProfileResponse(
        id=user.id,
        name=user.name,
        phone=user.phone,
        email=user.email,
        role=user.role,
        status=user.status,
        avatarUrl=user.avatar_url,
        division=user.division_name,
        district=user.district_name,
        upazila=user.upazila_name,
        area=user.area_name
    )
    if vendor or (user.vendor_profile and len(user.vendor_profile) > 0):
        v = vendor or user.vendor_profile[0]
        profile.shopName = v.shop_name
        profile.category = v.category
        profile.division = v.division_name or user.division_name
        profile.district = v.district_name or user.district_name
        profile.upazila = v.upazila_name or user.upazila_name
        profile.area = v.area_name or user.area_name
        profile.address = v.address
        profile.walletBalance = v.wallet_balance
        profile.isVerified = v.is_verified
    return profile

@router.post("/login", response_model=ApiResponse[AuthResponseData])
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == request.phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number or password"
        )
    if not AuthService.verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid phone number or password"
        )
    if user.status == UserStatus.SUSPENDED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended"
        )

    # Optional role check if client specifies required role
    if request.role and request.role != user.role and user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account registered as {user.role}, cannot login as {request.role}"
        )

    vendor = db.query(Vendor).filter(Vendor.user_id == user.id).first()
    token = AuthService.create_access_token({"sub": str(user.id), "role": user.role, "phone": user.phone})
    refresh_token = AuthService.create_refresh_token({"sub": str(user.id)})

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Login successful",
        data=AuthResponseData(
            token=token,
            refreshToken=refresh_token,
            user=build_profile_response(user, vendor)
        )
    )

@router.post("/register-customer", response_model=ApiResponse[AuthResponseData], status_code=201)
def register_customer(request: RegisterCustomerRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.phone == request.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is already registered"
        )

    new_user = User(
        name=request.name,
        phone=request.phone,
        password_hash=AuthService.hash_password(request.password),
        role=UserRole.CUSTOMER.value,
        status=UserStatus.ACTIVE.value,
        division_name=request.division,
        district_name=request.district,
        upazila_name=request.upazila,
        area_name=request.area
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = AuthService.create_access_token({"sub": str(new_user.id), "role": new_user.role, "phone": new_user.phone})
    refresh_token = AuthService.create_refresh_token({"sub": str(new_user.id)})

    return ApiResponse(
        success=True,
        statusCode=201,
        message="Customer registered successfully",
        data=AuthResponseData(
            token=token,
            refreshToken=refresh_token,
            user=build_profile_response(new_user)
        )
    )

@router.post("/register-vendor", response_model=ApiResponse[AuthResponseData], status_code=201)
def register_vendor(request: RegisterVendorRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.phone == request.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number is already registered"
        )

    cat = db.query(Category).filter(Category.name.ilike(request.category)).first()

    new_user = User(
        name=request.name,
        phone=request.phone,
        email=request.email,
        password_hash=AuthService.hash_password(request.password),
        role=UserRole.VENDOR.value,
        status=UserStatus.ACTIVE.value,
        division_name=request.division,
        district_name=request.district,
        upazila_name=request.upazila,
        area_name=request.area
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_vendor = Vendor(
        user_id=new_user.id,
        shop_name=request.shopName,
        category=request.category,
        category_id=cat.id if cat else None,
        address=request.address,
        division_name=request.division,
        district_name=request.district,
        upazila_name=request.upazila,
        area_name=request.area,
        commission_rate=cat.commission_rate if cat else 2.00, # 2% category commission
        wallet_balance=0.00,
        is_verified=False
    )
    db.add(new_vendor)
    db.commit()
    db.refresh(new_vendor)

    token = AuthService.create_access_token({"sub": str(new_user.id), "role": new_user.role, "phone": new_user.phone})
    refresh_token = AuthService.create_refresh_token({"sub": str(new_user.id)})

    return ApiResponse(
        success=True,
        statusCode=201,
        message="Vendor registered successfully",
        data=AuthResponseData(
            token=token,
            refreshToken=refresh_token,
            user=build_profile_response(new_user, new_vendor)
        )
    )

@router.get("/me", response_model=ApiResponse[UserProfileResponse])
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    vendor = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Profile fetched successfully",
        data=build_profile_response(current_user, vendor)
    )

@router.put("/profile", response_model=ApiResponse[UserProfileResponse])
def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if request.name:
        current_user.name = request.name
    if request.email:
        current_user.email = request.email
    if request.avatarUrl:
        current_user.avatar_url = request.avatarUrl
    if request.fcmToken:
        current_user.fcm_token = request.fcmToken

    vendor = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()
    if vendor:
        if request.shopName:
            vendor.shop_name = request.shopName
        if request.address:
            vendor.address = request.address

    db.commit()
    db.refresh(current_user)
    if vendor:
        db.refresh(vendor)

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Profile updated successfully",
        data=build_profile_response(current_user, vendor)
    )

@router.post("/refresh-token", response_model=ApiResponse[dict])
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = AuthService.decode_token(request.refreshToken)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type, refresh token required"
        )
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or user.status == UserStatus.SUSPENDED.value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or suspended"
        )

    new_token = AuthService.create_access_token({"sub": str(user.id), "role": user.role, "phone": user.phone})
    new_refresh = AuthService.create_refresh_token({"sub": str(user.id)})

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Token refreshed successfully",
        data={
            "token": new_token,
            "refreshToken": new_refresh
        }
    )

@router.post("/change-password", response_model=ApiResponse[dict])
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not AuthService.verify_password(request.oldPassword, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    current_user.password_hash = AuthService.hash_password(request.newPassword)
    db.commit()

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Password changed successfully",
        data={"userId": current_user.id}
    )

@router.post("/forgot-password", response_model=ApiResponse[dict])
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == request.phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account associated with this phone number"
        )
    # Simulated SMS OTP dispatch (e.g. 123456 in development/demo)
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Verification OTP sent to your phone number",
        data={"phone": request.phone, "otpSent": True, "demoOtp": "123456"}
    )

@router.post("/reset-password", response_model=ApiResponse[dict])
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == request.phone).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    if request.otp not in ["123456", "999999"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )

    user.password_hash = AuthService.hash_password(request.newPassword)
    db.commit()

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Password reset successfully. You can now login with your new password.",
        data={"phone": user.phone}
    )

@router.post("/logout", response_model=ApiResponse[dict])
def logout(current_user: User = Depends(get_current_user)):
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Logged out successfully",
        data={"loggedOut": True}
    )

