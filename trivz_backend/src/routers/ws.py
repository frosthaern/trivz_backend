from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ws import manager

# from dependencies import get_current_user_ws  # we'll write this next

router = APIRouter()


@router.websocket("/ws/{room_code}")
async def websocket_endpoint(
    room_code: str,
    websocket: WebSocket,
    # user_id: int = Depends(get_current_user_ws)  # uncomment when auth is ready
):
    user_id = 1  # hardcode for now, replace with auth later
    await manager.connect(room_code, user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # for now just echo back, real handlers come later
            await manager.broadcast(room_code, data)
    except WebSocketDisconnect:
        await manager.disconnect(room_code, user_id)
        await manager.broadcast(room_code, {"event": "user_left", "user_id": user_id})
