from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from services import auth as auth_service
from src.dependancies import get_db
from src.models import User
from src.schemas.user import RefreshRequest, TokenOut, UserOut, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserRegister, db: Annotated[Session, Depends(get_db)]):
    if auth_service.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="Username already exist")
    if auth_service.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    user = auth_service.create_user(db, payload.username, payload.email, payload.password)
    return user


@router.post("/token", response_model=TokenOut)
def login(payload: UserRegister, request: Request, db: Annotated[Session, Depends(get_db)]):
    user = auth_service.get_user_by_username(db, payload.username)
    if not user or not auth_service.verify_password(payload.password, user.hashed_pwd):
        raise HTTPException(status_code=401, detail="Invalid credential")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    access_token = auth_service.create_access_token(user.id)
    refresh_token = auth_service.create_refresh_token(db, user.id, device_info=request.headers.get("user-agent"))
    return TokenOut(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]):
    db_token = auth_service.verify_refresh_token(db, payload.refresh_token)
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    auth_service.revoke_refresh_token(db, payload.refresh_token)
    new_access = auth_service.create_access_token(db_token.user_id)
    new_refresh = auth_service.create_refresh_token(db, db_token.user_id)

    return TokenOut(access_token=new_access, refresh_token=new_refresh)


@router.post("/logout")
def logout(payload: RefreshRequest, db: Annotated[Session, Depends(get_db)]):
    auth_service.revoke_refresh_token(db, payload.refresh_token)
    return {"message": "Logged out Successfully"}


@router.get("/me", response_model=UserOut)
def me(current_user: Annotated[User, Depends(auth_service.get_current_user)]):
    return current_user
