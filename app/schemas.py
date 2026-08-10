from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime


class ArtistOut(BaseModel):
    id: int
    name: str
    created_at: datetime


class SongOut(BaseModel):
    id: int
    title: str
    duration_seconds: int
    youtube_id: str
    file_path: str
    language: Optional[str] = None
    created_at: datetime


class LyricsOut(BaseModel):
    id: int
    song_id: int
    source: str
    synced_lyrics: list[dict[str, Any]] | None = None
    plain_text: Optional[str] = None


class PlaylistOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    name: str
    is_template: bool = False
    cloned_from_id: Optional[int] = None
    created_at: datetime


class PlaylistTrackOut(BaseModel):
    playlist_id: int
    song_id: int
    position: int


class DownloadRequestOut(BaseModel):
    id: int
    youtube_url: str
    youtube_id: str
    requested_by_user_id: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime


class DownloadRequestCreate(BaseModel):
    youtube_url: str = Field(..., min_length=1)


class PlaylistCreate(BaseModel):
    name: str = Field(..., min_length=1)


class PlaylistTrackUpdate(BaseModel):
    song_id: int
    position: int


class PlaylistTrackReorderRequest(BaseModel):
    tracks: list[PlaylistTrackUpdate]
