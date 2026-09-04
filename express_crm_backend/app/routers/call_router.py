import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.call_log import CallLog
from app.models.invoice import Invoice
from app.schemas.common import ApiResponse
from app.schemas.call import CallInitiateRequest, CallInitiateResponse, CallEndRequest
from app.services.auth_service import get_current_user
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/calls", tags=["Real-time Voice Call & CTI Sessions"])

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
        "productName": request.productName
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
            productName=request.productName
        )
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
