from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from src.models import User
from src.services.ws import get_current_user_ws
from src.ws import manager

router = APIRouter()

CurrentUser = Annotated[User, Depends(get_current_user_ws)]


@router.websocket("/ws/{room_code}")
async def websocket_endpoint(
    room_code: str,
    websocket: WebSocket,
    user: CurrentUser,
):
    user_id = user.id
    await manager.connect(room_code, user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # for now just echo back, real handlers come later
            await manager.broadcast(room_code, data)
    except WebSocketDisconnect:
        await manager.disconnect(room_code, user_id)
        await manager.broadcast(room_code, {"event": "user_left", "user_id": user_id})
