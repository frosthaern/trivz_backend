import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from models.user import RefreshToken, User

import bcrypt

SECRET_KEY = os.getenv("SECRET_KEY", "backupsecretkey")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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


def create_refresh_token(
    db: Session, user_id: int, device_info: str | None = None
) -> str:
    raw_token = secrets.token_urlsafe(64)
    token_hash = _hash_token(raw_token)

    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        device_info=device_info,
    )
    db.add(db_token)
    db.commit()
    return raw_token


def verify_refresh_token(db: Session, raw_token: str) -> RefreshToken | None:
    token_hash = _hash_token(raw_token)
    db_token = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )
    return db_token


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    token_hash = _hash_token(raw_token)
    db_token = (
        db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    )
    if db_token:
        db_token.revoked = True
        db.commit()


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(
    db: Session, username: str, email: str, plaintext_password: str
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_pwd=hash_password(plaintext_password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
