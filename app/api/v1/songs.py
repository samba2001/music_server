import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import ActionType, Song, User
from app.schemas import SongResponse, YouTubeRequest
from app.services.downloader import DownloadError
from app.services.history import log_history
from app.services.song_import import get_or_create_youtube_song
from app.services.streaming import file_chunks, parse_range

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/songs", tags=["songs"])


@router.get("/search", response_model=list[SongResponse])
async def search_songs(q: str = Query(min_length=1), db: AsyncSession = Depends(get_db)) -> list[Song]:
    pattern = f"%{q}%"
    result = await db.scalars(select(Song).where(or_(Song.name.ilike(pattern), Song.search_params.ilike(pattern))).limit(50))
    return list(result)


@router.post("/from-youtube", response_model=SongResponse, status_code=201)
async def song_from_youtube(payload: YouTubeRequest, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)) -> Song:
    logger.info("Starting YouTube import for URL=%s", payload.youtube_url)
    try:
        song, created = await get_or_create_youtube_song(db, payload.youtube_url)
    except DownloadError as exc:
        logger.exception("YouTube import failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not created:
        logger.warning("Duplicate YouTube video blocked: song_id=%s", song.id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Song already exists")

    await db.commit()
    await db.refresh(song)
    logger.info("Song imported successfully: song_id=%s", song.id)
    return song


@router.get("/{song_id}/stream")
async def stream_song(
    song_id: int,
    request: Request,
    range_header: str | None = Header(default=None, alias="Range"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    song = await db.get(Song, song_id)
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    await log_history(db, user.id, ActionType.SONG_PLAYED, song_id=song.id)
    await db.commit()

    path = (settings.media_root / Path(song.mp3_path).name).resolve()
    if not path.is_file() or settings.media_root.resolve() not in path.parents:
        raise HTTPException(status_code=404, detail="Audio file not found")
    file_size = path.stat().st_size
    start, end, response_status = parse_range(range_header, file_size)
    headers = {"Accept-Ranges": "bytes", "Content-Length": str(end - start + 1), "Content-Disposition": f'inline; filename="{path.name}"'}
    if response_status == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    return StreamingResponse(file_chunks(path, start, end), status_code=response_status, media_type="audio/mpeg", headers=headers)
