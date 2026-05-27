import os

from dotenv import load_dotenv


def get_secret_key():
    if not load_dotenv():
        raise RuntimeError("Failed to load environment variables")
    return os.getenv("SECRET_KEY", "this secret key is just sot hat it doesn't give errors")


def get_algorithm():
    if not load_dotenv():
        raise RuntimeError("Failed to load environment variables")
    return os.getenv("ALGORITHM", "HS256")


def get_ttl():
    if not load_dotenv():
        raise RuntimeError("Failed to load environment variables")
    return os.getenv("TTL", "30")


def get_database_url():
    if not load_dotenv():
        raise RuntimeError("Failed to load environment variables")
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
