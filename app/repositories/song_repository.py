from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lyrics, Song, SongArtist


class SongRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, song_id: int) -> Song | None:
        return await self.session.get(Song, song_id)

    async def list(self, q: str | None = None) -> list[Song]:
        if not q:
            result = await self.session.execute(select(Song))
            return list(result.scalars().all())

        like = f"%{q}%"
        result = await self.session.execute(select(Song).where(Song.title.like(like)))
        return list(result.scalars().all())

    async def create(self, *, title: str, duration_seconds: int, youtube_id: str, file_path: str, language: str | None = None) -> Song:
        song = Song(title=title, duration_seconds=duration_seconds, youtube_id=youtube_id, file_path=file_path, language=language)
        self.session.add(song)
        await self.session.flush()
        return song

    async def create_artist_link(self, *, song_id: int, artist_id: int) -> None:
        self.session.add(SongArtist(song_id=song_id, artist_id=artist_id))

    async def create_lyrics(self, *, song_id: int, source: str, synced_lyrics: list[dict[str, Any]] | None, plain_text: str | None) -> Lyrics:
        lyrics = Lyrics(song_id=song_id, source=source, synced_lyrics=synced_lyrics, plain_text=plain_text)
        self.session.add(lyrics)
        await self.session.flush()
        return lyrics

    async def delete(self, song: Song) -> None:
        await self.session.delete(song)
        await self.session.commit()
