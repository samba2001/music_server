import logging
from pathlib import Path
from typing import Any

import httpx
import yt_dlp
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import STORAGE_DIR
from app.models import Artist, Song
from app.repositories.song_repository import SongRepository

logger = logging.getLogger(__name__)


class SongManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.song_repo = SongRepository(session)

    async def list_songs(self, q: str | None = None) -> list[Song]:
        return await self.song_repo.list(q)

    async def get_song(self, song_id: int) -> Song:
        song = await self.song_repo.get_by_id(song_id)
        if song is None:
            raise HTTPException(status_code=404, detail="Song not found")
        return song

    async def delete_song(self, song_id: int) -> None:
        song = await self.get_song(song_id)
        await self.song_repo.delete(song)

    async def get_lyrics(self, song_id: int) -> list[dict[str, Any]]:
        song = await self.get_song(song_id)
        return (song.lyrics.synced_lyrics or []) if song.lyrics else []

    async def save_downloaded_song(self, *, title: str, duration_seconds: int, youtube_id: str, file_path: str, artist_name: str, lyrics_payload: list[dict[str, Any]], language: str | None = None) -> Song:
        song = await self.song_repo.create(title=title, duration_seconds=duration_seconds, youtube_id=youtube_id, file_path=file_path, language=language)
        artist = await self.session.get(Artist, 1)
        if artist is None:
            artist = Artist(name=artist_name)
            self.session.add(artist)
            await self.session.flush()
        await self.song_repo.create_artist_link(song_id=song.id, artist_id=artist.id)
        await self.song_repo.create_lyrics(song_id=song.id, source="LRCLIB", synced_lyrics=lyrics_payload, plain_text="\n".join(item.get("text", "") for item in lyrics_payload if isinstance(item, dict)))
        await self.session.commit()
        return song
