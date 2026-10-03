from datetime import datetime
import json
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import ActionType, PlaylistType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AuthorResponse(ORMModel):
    id: int
    name: str
    languages: str
    profile_pic: str | None


class SongResponse(ORMModel):
    id: int
    name: str
    author_id: int | None
    mp3_path: str
    search_params: str
    created_at: datetime


class PlaylistSongResponse(ORMModel):
    id: int
    song_id: int
    added_at: datetime
    song: SongResponse


class PlaylistResponse(ORMModel):
    id: int
    user_id: int | None
    name: str
    playlist_type: PlaylistType
    is_clone: bool
    clone_id: int | None
    created_at: datetime
    songs: list[PlaylistSongResponse] = []

    @model_validator(mode="before")
    @classmethod
    def normalize_clone_id(cls, value: Any) -> Any:
        if isinstance(value, dict):
            clone_id = value.get("clone_id")
            if clone_id in (None, ""):
                value["clone_id"] = None
            elif isinstance(clone_id, str):
                stripped = clone_id.strip()
                if stripped == "":
                    value["clone_id"] = None
                else:
                    try:
                        value["clone_id"] = int(stripped)
                    except ValueError:
                        pass
        elif hasattr(value, "clone_id"):
            clone_id = getattr(value, "clone_id")
            if clone_id in (None, ""):
                value.clone_id = None
            elif isinstance(clone_id, str):
                stripped = clone_id.strip()
                if stripped == "":
                    value.clone_id = None
                else:
                    try:
                        value.clone_id = int(stripped)
                    except ValueError:
                        pass
        return value


class PlaylistCreate(BaseModel):
    name: str = Field(min_length=1)
    playlist_type: PlaylistType | None = None
    is_clone: bool | None = None
    clone_id: int | None = None

    @field_validator("clone_id", mode="before")
    @classmethod
    def normalize_clone_id(cls, value: Any) -> Any:
        if value in (None, ""):
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                return None
            return int(stripped)
        return value


class AddSongRequest(BaseModel):
    song_id: int | None = Field(default=None, gt=0)
    youtube_url: str | None = Field(default=None, min_length=1, max_length=2048)

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value.strip())
        hostname = (parsed.hostname or "").lower()
        allowed_hosts = {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "music.youtube.com",
            "youtu.be",
            "www.youtu.be",
        }
        if parsed.scheme not in {"http", "https"} or hostname not in allowed_hosts:
            raise ValueError("youtube_url must be a valid YouTube URL")
        return value.strip()

    @model_validator(mode="after")
    def require_song_id_or_youtube_url(self) -> "AddSongRequest":
        if (self.song_id is None) == (self.youtube_url is None):
            raise ValueError("Provide exactly one of song_id or youtube_url")
        return self


class GoogleAuthRequest(BaseModel):
    """Accept a raw Google ID token string. Simpler and unambiguous for clients."""

    id_token: str = Field(min_length=1)

    @property
    def google_id_token(self) -> str:
        return self.id_token


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int | None = None


class YouTubeRequest(BaseModel):
    youtube_url: str = Field(min_length=1, max_length=2048)


class PlayEventRequest(BaseModel):
    song_id: int
    played_till: int = Field(default=0, ge=0)


class HistoryResponse(ORMModel):
    id: int
    user_id: int
    song_id: int | None
    playlist_id: int | None
    action_type: ActionType
    played_till: int
    passed_at: datetime
    song_name: str | None = None
    author_name: str | None = None