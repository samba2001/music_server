from datetime import datetime, timezone
from types import SimpleNamespace

from app.models import ActionType, History
from app.schemas import PlaylistCreate, PlaylistResponse
from app.services.history import collapse_history_events


def make_event(event_id: int, song_id: int, played_at: datetime) -> History:
    return History(
        id=event_id,
        user_id=1,
        song_id=song_id,
        playlist_id=None,
        action_type=ActionType.SONG_PLAYED,
        played_till=10,
        passed_at=played_at,
    )


def test_history_defaults_to_deduplicated_song_rows():
    events = [
        make_event(1, 101, datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)),
        make_event(2, 101, datetime(2024, 1, 1, 12, 5, tzinfo=timezone.utc)),
        make_event(3, 102, datetime(2024, 1, 1, 12, 7, tzinfo=timezone.utc)),
        make_event(4, 101, datetime(2024, 1, 1, 12, 9, tzinfo=timezone.utc)),
    ]

    collapsed = collapse_history_events(events)

    assert [event.song_id for event in collapsed] == [101, 102]
    assert len(collapsed) == 2


def test_show_duplicated_true_keeps_every_play_event():
    events = [
        make_event(1, 101, datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)),
        make_event(2, 101, datetime(2024, 1, 1, 12, 5, tzinfo=timezone.utc)),
        make_event(3, 102, datetime(2024, 1, 1, 12, 7, tzinfo=timezone.utc)),
    ]

    expanded = collapse_history_events(events, show_duplicated=True)

    assert [event.song_id for event in expanded] == [101, 101, 102]
    assert len(expanded) == 3


def test_playlist_validation_coerces_blank_clone_ids_to_none():
    payload = PlaylistCreate.model_validate({"name": "Favorites", "clone_id": ""})
    assert payload.clone_id is None

    playlist = SimpleNamespace(
        id=12,
        user_id=1,
        name="Favorites",
        playlist_type="default",
        is_clone=False,
        clone_id="",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        songs=[],
    )

    validated = PlaylistResponse.model_validate(playlist)
    assert validated.clone_id is None
