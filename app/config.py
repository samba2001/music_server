import logging
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "media"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./music_server.db")
BYPASS_AUTH = os.getenv("BYPASS_AUTH", "True").lower() in {"1", "true", "yes", "on"}
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s")
