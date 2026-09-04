import json
from typing import Dict, Set, Any
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        # Room -> Set of active WebSockets
        self.rooms: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> Set of rooms it has joined
        self.socket_rooms: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.socket_rooms[websocket] = set()

    def disconnect(self, websocket: WebSocket):
        joined = self.socket_rooms.get(websocket, set())
        for room in joined:
            if room in self.rooms:
                self.rooms[room].discard(websocket)
                if not self.rooms[room]:
                    del self.rooms[room]
        if websocket in self.socket_rooms:
            del self.socket_rooms[websocket]

    def join_room(self, websocket: WebSocket, room: str):
        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(websocket)
        if websocket in self.socket_rooms:
            self.socket_rooms[websocket].add(room)

    def leave_room(self, websocket: WebSocket, room: str):
        if room in self.rooms:
            self.rooms[room].discard(websocket)
            if not self.rooms[room]:
                del self.rooms[room]
        if websocket in self.socket_rooms:
            self.socket_rooms[websocket].discard(room)

    async def broadcast_to_room(self, room: str, event: str, payload: Any):
        if room in self.rooms:
            message = json.dumps({"event": event, "data": payload})
            disconnected = []
            for ws in self.rooms[room]:
                try:
                    await ws.send_text(message)
                except Exception:
                    disconnected.append(ws)
            for ws in disconnected:
                self.disconnect(ws)

    async def broadcast_all(self, event: str, payload: Any):
        message = json.dumps({"event": event, "data": payload})
        disconnected = []
        for ws in self.socket_rooms.keys():
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)

ws_manager = WebSocketManager()
