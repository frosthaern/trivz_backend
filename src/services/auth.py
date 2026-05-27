import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import RefreshToken, User
from src.services.db import get_db, oauth2_scheme

SECRET_KEY = os.getenv("SECRET_KEY", "backupsecretkey")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token(db: Session, user_id: int, device_info: str | None = None) -> str:
    raw_token = secrets.token_urlsafe(64)
    token_hash = _hash_token(raw_token)

    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        device_info=device_info,
    )
    db.add(db_token)
    db.commit()
    return raw_token


def verify_refresh_token(db: Session, raw_token: str) -> RefreshToken | None:
    token_hash = _hash_token(raw_token)
    stmt = select(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked.is_(False),
        RefreshToken.expires_at > datetime.now(UTC),
    )
    db_token = db.execute(stmt).scalars().first()
    return db_token


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    token_hash = _hash_token(raw_token)
    stmt = select(RefreshToken).filter(RefreshToken.token_hash == token_hash)
    db_token = db.execute(stmt).scalars().first()
    if db_token:
        db_token.revoked = True
        db.commit()


def get_user_by_username(db: Session, username: str) -> User | None:
    stmt = select(User).filter(User.username == username)
    return db.execute(stmt).scalars().first()


def get_user_by_email(db: Session, email: str) -> User | None:
    # return db.query(User).filter(User.email == email).first()
    stmt = select(User).filter(User.email == email)
    return db.execute(stmt).scalars().first()


def create_user(db: Session, username: str, email: str, plaintext_password: str) -> User:
    user = User(
        username=username,
        email=email,
        hashed_pwd=hash_password(plaintext_password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    stmt = select(User).filter(User.id == user_id)
    user = db.execute(stmt).scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    return user


async def get_device_info(request: Request) -> str | None:
    return request.headers.get("device-info")
