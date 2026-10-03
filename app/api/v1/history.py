from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import ActionType, History, User
from app.models.entities import Song, Author
from app.schemas import HistoryResponse, PlayEventRequest
from app.services.history import collapse_history_events, log_history
router = APIRouter(prefix="/history", tags=["history"])


@router.post("/play-event", response_model=HistoryResponse, status_code=201)
async def play_event(payload: PlayEventRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> History:
    event = await log_history(db, user.id, ActionType.SONG_PLAYED, song_id=payload.song_id, played_till=payload.played_till)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("", response_model=list[HistoryResponse])
async def get_history(
    show_duplicated: bool = Query(default=False, description="Include repeated song plays in the response"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[History]:
    result = await db.scalars(select(History).where(History.user_id == user.id).order_by(desc(History.passed_at)))
    return collapse_history_events(result, show_duplicated=show_duplicated)





@router.get("", response_model=list[HistoryResponse])
async def get_history(
    show_duplicated: bool = Query(
        default=False,
        description="Include repeated song plays in the response",
    ),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
  # Select explicit fields including joined Song and Author columns
  stmt = (
      select(
          History.id,
          History.user_id,
          History.song_id,
          History.playlist_id,
          History.action_type,
          History.played_till,
          History.passed_at,
          Song.name.label("song_name"),
          Author.name.label("author_name"),
      )
      .join(Song, History.song_id == Song.id, isouter=True)  # Left join in case song was deleted
      .join(Author, Song.author_id == Author.id, isouter=True)  # Left join in case author is missing
      .where(History.user_id == user.id)
      .order_by(desc(History.passed_at))
  )

  result = await db.execute(stmt)
  rows = result.mappings().all()

  # If you use collapse_history_events, ensure it handles or passes along dictionaries/rows,
  # or map them directly:
  history_dicts = [dict(row) for row in rows]
  
  return collapse_history_events(history_dicts, show_duplicated=show_duplicated)