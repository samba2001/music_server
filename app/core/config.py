from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Music Server API"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./music_server.db"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    media_root: Path = Path("media/songs")
    google_client_id: str | None = None
    download_timeout_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.media_root.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
