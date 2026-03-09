from typing import Annotated

from fastapi import Depends, Query, WebSocket, WebSocketException, status
from sqlalchemy.orm import Session

from src.models import User
from src.services.auth import decode_access_token
from src.services.db import get_db


async def get_current_user_ws(
    websocket: WebSocket,
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Query()] = None,
) -> User:
    if token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    user_id = decode_access_token(token)
    if not user_id:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    return user
