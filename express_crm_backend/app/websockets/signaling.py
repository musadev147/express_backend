import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["WebSocket Real-Time Signaling"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                message = json.loads(raw_data)
            except Exception:
                continue

            event = message.get("event")
            payload = message.get("data", {})

            if event == "join":
                # e.g. { "event": "join", "data": { "room": "room:vendor:1" } }
                room = payload.get("room")
                if room:
                    ws_manager.join_room(websocket, room)
                    await websocket.send_text(json.dumps({"event": "joined", "data": {"room": room}}))

            elif event == "call:cart_sync":
                # Real-time synchronize cart items during active voice call
                call_id = payload.get("callId")
                items = payload.get("items", [])
                await ws_manager.broadcast_all("call:cart_sync", {
                    "callId": call_id,
                    "items": items
                })

            elif event == "call:accepted":
                call_id = payload.get("callId")
                await ws_manager.broadcast_all("call:accepted", {
                    "callId": call_id,
                    "status": "active"
                })

            elif event == "call:rejected":
                call_id = payload.get("callId")
                await ws_manager.broadcast_all("call:rejected", {
                    "callId": call_id,
                    "status": "rejected"
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
