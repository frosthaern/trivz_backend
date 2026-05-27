from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.models import User
from src.schemas.user import RefreshRequest, TokenResponse, UserRegister, UserResponse
from src.services import auth as aus
from src.services.auth import get_device_info
from src.services.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register_token", response_model=TokenResponse, status_code=201)
def register_token(
    payload: UserRegister,
    db: Annotated[Session, Depends(get_db)],
    device_info: Annotated[str, Depends(get_device_info)],
):
    user = aus.get_user_by_username(db, payload.username)
    if user is None:
        user = aus.create_user(db, payload.username, payload.email, payload.password)
    access_token = aus.create_access_token(user.id)
    refresh_token = aus.create_refresh_token(db, user.id, device_info=device_info)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]):
    db_token = aus.verify_refresh_token(db, payload.refresh_token)
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    aus.revoke_refresh_token(db, payload.refresh_token)
    new_access = aus.create_access_token(db_token.user_id)
    new_refresh = aus.create_refresh_token(db, db_token.user_id)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout")
def logout(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]):
    aus.revoke_refresh_token(db, payload.refresh_token)
    return {"message": "Logged out Successfully"}


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[User, Depends(aus.get_current_user)]):
    return current_user
