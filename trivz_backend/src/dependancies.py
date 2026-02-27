from collections.abc import Generator

from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
