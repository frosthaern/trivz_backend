import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, list[tuple[int, WebSocket]]] = {}  # maybe creat a type out of this stuff

    async def connect(self, room_code: str, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if room_code not in self.rooms:
            self.rooms[room_code] = []
        self.rooms[room_code].append((user_id, websocket))

    async def disconnect(self, room_code: str, user_id: int):
        if room_code not in self.rooms:
            return
        self.rooms[room_code] = [(uid, ws) for uid, ws in self.rooms[room_code] if uid != user_id]
        if not self.rooms[room_code]:
            del self.rooms[room_code]
        logger.info(f"User {user_id} disconnected from room {room_code}")

    # need to do something for the type of dict you are sending
    async def broadcast(self, room_code: str, event: dict[Any, Any]):
        if room_code not in self.rooms:
            return
        disconnected: list[int] = []
        for user_id, websocket in self.rooms[room_code]:
            try:
                await websocket.send_json(event)
            except Exception:
                logger.warning(f"Failed to send to user {user_id}, marking for removal")
                disconnected.append(user_id)
        for user_id in disconnected:
            await self.disconnect(room_code, user_id)

    async def send_to_user(self, room_code: str, user_id: int, event: dict[Any, Any]):
        if room_code not in self.rooms:
            return
        for uid, websocket in self.rooms[room_code]:
            if uid == user_id:
                try:
                    await websocket.send_json(event)
                except Exception:
                    logger.warning(f"Failed to send to user {user_id}")
                    await self.disconnect(room_code, user_id)
                return

    def get_connected_users(self, room_code: str) -> list[int]:
        if room_code not in self.rooms:
            return []
        return [uid for uid, _ in self.rooms[room_code]]

    def is_user_connected(self, room_code: str, user_id: int) -> bool:
        return user_id in self.get_connected_users(room_code)
