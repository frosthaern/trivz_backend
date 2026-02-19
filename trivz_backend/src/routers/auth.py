from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy.orm import Session

from dependancies import get_db
from models.user import User
from schemas.auth import UserOut, UserRegister
from src.services import auth as auth_service


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserRegister, db: Annotated[Session, Depends(get_db)]):
    if auth_service.get_user_by_username(db, payload.username):
        raise HTTPException(status_code=400, detail="Username already exist")
    if auth_service.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email already exists")

    user = auth_service.create_user(
        db, payload.username, payload.email, payload.password
    )
    return user
