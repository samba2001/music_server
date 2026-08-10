import logging
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.managers.auth_manager import AuthManager
from app.managers.song_manager import SongManager
from app.models import User
from app.schemas import LyricsOut, SongOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/songs", tags=["songs"])


async def get_song_manager(db: AsyncSession = Depends(get_db)) -> SongManager:
    return SongManager(db)


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    auth_manager = AuthManager(db)
    return await auth_manager.get_current_user(request)


@router.get("", response_model=list[SongOut])
async def list_songs(q: str | None = None, manager: SongManager = Depends(get_song_manager), user: User = Depends(get_current_user)) -> list[SongOut]:
    songs = await manager.list_songs(q)
    return [SongOut.model_validate(song) for song in songs]


@router.get("/{song_id}", response_model=SongOut)
async def get_song(song_id: int, manager: SongManager = Depends(get_song_manager), user: User = Depends(get_current_user)) -> SongOut:
    song = await manager.get_song(song_id)
    return SongOut.model_validate(song)


@router.get("/{song_id}/lyrics", response_model=LyricsOut)
async def get_song_lyrics(song_id: int, manager: SongManager = Depends(get_song_manager), user: User = Depends(get_current_user)) -> LyricsOut:
    lyrics = await manager.get_lyrics(song_id)
    return LyricsOut(song_id=song_id, synced_lyrics=lyrics, source="LRCLIB")


@router.delete("/{song_id}")
async def delete_song(song_id: int, manager: SongManager = Depends(get_song_manager), user: User = Depends(get_current_user)) -> dict[str, bool]:
    await manager.delete_song(song_id)
    return {"success": True}
