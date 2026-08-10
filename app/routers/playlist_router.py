from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.managers.auth_manager import AuthManager
from app.managers.playlist_manager import PlaylistManager
from app.models import User
from app.schemas import PlaylistCreate, PlaylistOut, PlaylistTrackReorderRequest

router = APIRouter(prefix="/api/v1/playlists", tags=["playlists"])


async def get_playlist_manager(db: AsyncSession = Depends(get_db)) -> PlaylistManager:
    return PlaylistManager(db)


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    auth_manager = AuthManager(db)
    return await auth_manager.get_current_user(request)


@router.get("", response_model=list[PlaylistOut])
async def list_playlists(manager: PlaylistManager = Depends(get_playlist_manager), user: User = Depends(get_current_user)) -> list[PlaylistOut]:
    playlists = await manager.list_playlists(user.id)
    return [PlaylistOut.model_validate(playlist) for playlist in playlists]


@router.post("", response_model=PlaylistOut)
async def create_playlist(payload: PlaylistCreate, manager: PlaylistManager = Depends(get_playlist_manager), user: User = Depends(get_current_user)) -> PlaylistOut:
    playlist = await manager.create_playlist(user_id=user.id, name=payload.name)
    return PlaylistOut.model_validate(playlist)


@router.post("/{playlist_id}/clone", response_model=PlaylistOut)
async def clone_playlist(playlist_id: int, manager: PlaylistManager = Depends(get_playlist_manager), user: User = Depends(get_current_user)) -> PlaylistOut:
    clone = await manager.clone_playlist(playlist_id=playlist_id, user_id=user.id)
    return PlaylistOut.model_validate(clone)


@router.put("/{playlist_id}/tracks")
async def reorder_tracks(playlist_id: int, payload: PlaylistTrackReorderRequest, manager: PlaylistManager = Depends(get_playlist_manager), user: User = Depends(get_current_user)) -> dict[str, bool]:
    await manager.reorder_tracks(playlist_id=playlist_id, user_id=user.id, tracks=[{"song_id": item.song_id, "position": item.position} for item in payload.tracks])
    return {"success": True}


@router.delete("/{playlist_id}")
async def delete_playlist(playlist_id: int, manager: PlaylistManager = Depends(get_playlist_manager), user: User = Depends(get_current_user)) -> dict[str, bool]:
    await manager.delete_playlist(playlist_id=playlist_id, user_id=user.id)
    return {"success": True}
