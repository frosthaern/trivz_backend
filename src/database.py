from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import get_database_url


class Base(DeclarativeBase):
    pass


async def get_db_connection():
    if not load_dotenv():
        raise RuntimeError("Failed to load environment variables")
    db_url: str = get_database_url()
    return create_async_engine(db_url, echo=True)


async def get_db() -> AsyncGenerator[AsyncSession]:
    engine = await get_db_connection()
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


async def init_db():
    engine = await get_db_connection()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
