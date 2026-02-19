import os
from dotenv import load_dotenv

if not load_dotenv():
    raise ValueError("set your keys in .env")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
TTL = 30
