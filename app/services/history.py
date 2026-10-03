from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActionType, History


def collapse_history_events(history: Iterable[History], show_duplicated: bool = False) -> list[History]:
    items = list(history)
    if show_duplicated or not items:
        return items

    seen: set[int] = set()
    condensed: list[History] = []
    for event in items:
        if event.action_type != ActionType.SONG_PLAYED or event.song_id is None:
            condensed.append(event)
            continue
        if event.song_id in seen:
            continue
        condensed.append(event)
        seen.add(event.song_id)
    return condensed


async def log_history(
    db: AsyncSession,
    user_id: int,
    action_type: ActionType,
    *,
    song_id: int | None = None,
    playlist_id: int | None = None,
    played_till: int = 0,
) -> History:
    event = History(user_id=user_id, action_type=action_type, song_id=song_id, playlist_id=playlist_id, played_till=played_till)
    db.add(event)
    await db.flush()
    return event
