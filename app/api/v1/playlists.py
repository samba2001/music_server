from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import ActionType, Playlist, PlaylistSong, PlaylistType, Song, User
from app.schemas import AddSongRequest, PlaylistCreate, PlaylistResponse
from app.services.downloader import DownloadError
from app.services.history import log_history
from app.services.song_import import get_or_create_youtube_song

router = APIRouter(prefix="/playlists", tags=["playlists"])


async def _playlist(db: AsyncSession, playlist_id: int) -> Playlist:
    playlist = await db.scalar(select(Playlist).options(selectinload(Playlist.songs).selectinload(PlaylistSong.song)).where(Playlist.id == playlist_id))
    if playlist is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist


@router.get("/default", response_model=list[PlaylistResponse])
async def default_playlists(db: AsyncSession = Depends(get_db)) -> list[Playlist]:
    result = await db.scalars(select(Playlist).where(Playlist.playlist_type == PlaylistType.DEFAULT).options(selectinload(Playlist.songs).selectinload(PlaylistSong.song)))
    return list(result)


@router.get("/", response_model=list[PlaylistResponse])
async def user_playlists(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Playlist]:
    result = await db.scalars(
        select(Playlist)
        .where(Playlist.user_id == user.id, Playlist.playlist_type == PlaylistType.USER)
        .options(selectinload(Playlist.songs).selectinload(PlaylistSong.song))
    )
    return list(result)


@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Playlist:
    playlist = await _playlist(db, playlist_id)
    if playlist.playlist_type == PlaylistType.USER and playlist.user_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="You cannot view another user's playlist")
    return playlist


def _require_playlist_edit_access(playlist: Playlist, user: User) -> None:
    if playlist.playlist_type == PlaylistType.DEFAULT:
        if not user.is_admin:
            raise HTTPException(status_code=403, detail="Only admins can change default playlists")
        return
    if playlist.playlist_type == PlaylistType.USER and playlist.user_id == user.id:
        return
    raise HTTPException(status_code=403, detail="Only the playlist owner can change this playlist")


@router.post("/{playlist_id}/clone", response_model=PlaylistResponse, status_code=201)
async def clone_playlist(playlist_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> Playlist:
    source = await _playlist(db, playlist_id)
    clone = Playlist(user_id=user.id, name=source.name, playlist_type=PlaylistType.USER, is_clone=True, clone_id=source.id)
    db.add(clone)
    await db.flush()
    for link in source.songs:
        db.add(PlaylistSong(playlist_id=clone.id, song_id=link.song_id))
    await log_history(db, user.id, ActionType.PLAYLIST_CLONED, playlist_id=clone.id)
    await db.commit()
    return await _playlist(db, clone.id)


@router.post("/{playlist_id}/songs", response_model=PlaylistResponse)
async def add_song(playlist_id: int, payload: AddSongRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> Playlist:
    playlist = await _playlist(db, playlist_id)
    _require_playlist_edit_access(playlist, user)
    if payload.song_id is not None:
        song = await db.scalar(select(Song).where(Song.id == payload.song_id))
        if song is None:
            raise HTTPException(status_code=404, detail="Song not found")
    else:
        if payload.youtube_url is None:
            raise HTTPException(status_code=422, detail="Provide a song_id or youtube_url")
        try:
            song, _ = await get_or_create_youtube_song(db, payload.youtube_url)
        except DownloadError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    song_id = song.id
    existing_link = await db.scalar(select(PlaylistSong.id).where(PlaylistSong.playlist_id == playlist_id, PlaylistSong.song_id == song_id))
    if existing_link is not None:
        raise HTTPException(status_code=409, detail="Song already exists in playlist")

    try:
        db.add(PlaylistSong(playlist_id=playlist_id, song_id=song_id))
        await log_history(db, user.id, ActionType.ADD_SONG, song_id=song_id, playlist_id=playlist_id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing_link = await db.scalar(
            select(PlaylistSong.id).where(
                PlaylistSong.playlist_id == playlist_id,
                PlaylistSong.song_id == song_id,
            )
        )
        if existing_link is not None:
            raise HTTPException(status_code=409, detail="Song already exists in playlist")
        raise
    return await _playlist(db, playlist_id)


@router.post("/", response_model=PlaylistResponse, status_code=201)
async def create_playlist(payload: PlaylistCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> Playlist:
    p_type = payload.playlist_type or PlaylistType.USER
    if p_type == PlaylistType.DEFAULT and not user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can create default playlists")
    owner_id = None if p_type == PlaylistType.DEFAULT else user.id

    # Treat zero or falsy clone_id as not provided (clients may send 0)
    clone_id = int(payload.clone_id) if payload.clone_id else None
    is_clone = payload.is_clone if payload.is_clone is not None else (clone_id is not None)

    # validate clone_id if provided and positive
    if clone_id is not None:
        src = await db.scalar(select(Playlist.id).where(Playlist.id == clone_id))
        if src is None:
            raise HTTPException(status_code=404, detail="Source playlist for clone not found")

    playlist = Playlist(user_id=owner_id, name=payload.name, playlist_type=p_type, is_clone=is_clone, clone_id=clone_id)
    db.add(playlist)
    await db.commit()
    await db.refresh(playlist)
    return await _playlist(db, playlist.id)


@router.delete("/{playlist_id}/songs/{song_id}", status_code=204)
async def remove_song(playlist_id: int, song_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    playlist = await _playlist(db, playlist_id)
    _require_playlist_edit_access(playlist, user)
    result = await db.execute(delete(PlaylistSong).where(PlaylistSong.playlist_id == playlist_id, PlaylistSong.song_id == song_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Song is not in playlist")
    await log_history(db, user.id, ActionType.REMOVE_SONG, song_id=song_id, playlist_id=playlist_id)
    await db.commit()
