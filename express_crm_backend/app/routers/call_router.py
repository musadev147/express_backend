import time
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.call_log import CallLog
from app.models.invoice import Invoice
from app.schemas.common import ApiResponse
from app.config import settings
from app.schemas.call import CallInitiateRequest, CallInitiateResponse, CallEndRequest, CallCartSyncRequest, CallLogResponse, AgoraConfigResponse
from app.services.auth_service import get_current_user, get_optional_user
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/calls", tags=["Real-time Voice Call & CTI Sessions"])


def format_call_response(c: CallLog) -> CallLogResponse:
    return CallLogResponse(
        id=c.id,
        callerId=c.caller_id,
        callerName=c.caller_name or "Caller",
        callerPhone=c.caller_phone or "",
        callerRole=c.caller_role or "customer",
        receiverId=c.receiver_id,
        receiverName=c.receiver_name or "Receiver",
        receiverPhone=c.receiver_phone or "",
        receiverShopName=c.receiver_shop_name,
        receiverArea=c.receiver_area,
        productName=c.product_name,
        status=c.status,
        durationSeconds=c.duration_seconds or 0,
        invoiceId=c.invoice_id,
        createdAt=c.created_at.isoformat() if c.created_at else "",
        endedAt=c.ended_at.isoformat() if c.ended_at else None
    )

@router.post("/initiate", response_model=ApiResponse[CallInitiateResponse], status_code=201)
async def initiate_call(
    request: CallInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receiver = db.query(User).filter(User.phone == request.receiverPhone).first()
    if not receiver:
        # Create temp receiver user record if not registered yet
        receiver = User(
            name=request.receiverName or "Vendor",
            phone=request.receiverPhone,
            password_hash="temp_hash",
            role=UserRole.VENDOR.value,
            area_name=request.receiverArea
        )
        db.add(receiver)
        db.commit()
        db.refresh(receiver)

    call_id = f"call_{int(time.time() * 1000)}"
    new_call = CallLog(
        id=call_id,
        caller_id=current_user.id,
        caller_role=current_user.role,
        caller_phone=current_user.phone,
        caller_name=current_user.name,
        receiver_id=receiver.id,
        receiver_phone=receiver.phone,
        receiver_name=request.receiverName or receiver.name,
        receiver_shop_name=request.receiverShopName,
        receiver_area=request.receiverArea,
        product_name=request.productName,
        status="dialing"
    )
    db.add(new_call)
    db.commit()

    # Real-time WebSocket signaling to receiver room (ring receiver's phone)
    payload = {
        "callId": call_id,
        "callerId": current_user.id,
        "callerName": current_user.name,
        "callerPhone": current_user.phone,
        "productName": request.productName,
        "channelName": call_id,
        "agoraAppId": settings.AGORA_APP_ID,
        "agoraToken": settings.AGORA_TEMP_TOKEN
    }
    await ws_manager.broadcast_to_room(f"room:vendor:{receiver.id}", "call:incoming", payload)
    await ws_manager.broadcast_to_room(f"room:customer:{receiver.id}", "call:incoming", payload)

    return ApiResponse(
        success=True,
        statusCode=201,
        message="Call session initiated",
        data=CallInitiateResponse(
            callId=call_id,
            status="dialing",
            callerPhone=current_user.phone,
            receiverPhone=request.receiverPhone,
            productName=request.productName,
            channelName=call_id,
            agoraAppId=settings.AGORA_APP_ID,
            agoraToken=settings.AGORA_TEMP_TOKEN
        )
    )

@router.get("/agora-config", response_model=ApiResponse[AgoraConfigResponse])
def get_agora_config(channelName: Optional[str] = "express_call"):
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Agora RTC configuration fetched",
        data=AgoraConfigResponse(
            appId=settings.AGORA_APP_ID,
            token=settings.AGORA_TEMP_TOKEN,
            channelName=channelName or "express_call"
        )
    )

@router.post("/sync-cart", response_model=ApiResponse[dict])

async def sync_cart_rest(
    request: CallCartSyncRequest,
    current_user: User = Depends(get_current_user)
):
    await ws_manager.broadcast_all("call:cart_sync", {
        "callId": request.callId,
        "items": request.items,
        "syncedBy": current_user.name
    })
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Cart synchronized successfully during call",
        data={"callId": request.callId, "itemCount": len(request.items)}
    )

@router.get("/history", response_model=ApiResponse[list])
def get_call_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    calls = db.query(CallLog).filter(
        (CallLog.caller_id == current_user.id) |
        (CallLog.receiver_id == current_user.id) |
        (CallLog.caller_phone == current_user.phone) |
        (CallLog.receiver_phone == current_user.phone)
    ).order_by(CallLog.created_at.desc()).limit(50).all()

    result = [format_call_response(c) for c in calls]
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Call history fetched",
        data=result
    )

@router.get("/{call_id}", response_model=ApiResponse[CallLogResponse])
def get_call_status(call_id: str, db: Session = Depends(get_db)):
    call_log = db.query(CallLog).filter(CallLog.id == call_id).first()
    if not call_log:
        raise HTTPException(status_code=404, detail="Call log not found")
    return ApiResponse(
        success=True,
        statusCode=200,
        message="Call session status fetched",
        data=format_call_response(call_log)
    )

@router.post("/{call_id}/end", response_model=ApiResponse[dict])
async def end_call(
    call_id: str,
    request: CallEndRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    call_log = db.query(CallLog).filter(CallLog.id == call_id).first()
    if not call_log:
        raise HTTPException(status_code=404, detail="Call log not found")

    call_log.status = request.status
    call_log.duration_seconds = request.durationSeconds
    call_log.invoice_id = request.invoiceId
    call_log.ended_at = datetime.utcnow()

    db.commit()

    # Broadcast call end to both parties
    await ws_manager.broadcast_all("call:ended", {
        "callId": call_id,
        "durationSeconds": request.durationSeconds,
        "invoiceId": request.invoiceId
    })

    return ApiResponse(
        success=True,
        statusCode=200,
        message="Call session ended",
        data={
            "callId": call_id,
            "status": request.status,
            "durationSeconds": request.durationSeconds,
            "invoiceId": request.invoiceId
        }
    )

