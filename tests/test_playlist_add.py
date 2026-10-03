from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.v1.playlists import add_song, create_playlist
from app.models import Playlist, PlaylistSong, PlaylistType
from app.schemas import AddSongRequest, PlaylistCreate


class StubSession:
    def __init__(self, scalar_results, flush_error=None):
        self.scalar_results = iter(scalar_results)
        self.flush_error = flush_error
        self.added = []

    async def scalar(self, _statement):
        try:
            return next(self.scalar_results)
        except StopIteration:
            return next((item for item in self.added if isinstance(item, Playlist)), None)

    def add(self, instance):
        self.added.append(instance)

    async def flush(self):
        if self.flush_error:
            raise self.flush_error

    async def commit(self):
        for instance in self.added:
            if isinstance(instance, Playlist) and instance.id is None:
                instance.id = 91

    async def rollback(self):
        pass

    async def refresh(self, _instance):
        pass


def default_playlist():
    return SimpleNamespace(
        id=8,
        user_id=None,
        playlist_type=PlaylistType.DEFAULT,
        songs=[],
    )


def user_playlist(owner_id=1):
    return SimpleNamespace(
        id=9,
        user_id=owner_id,
        playlist_type=PlaylistType.USER,
        songs=[],
    )


@pytest.mark.asyncio
async def test_non_admin_cannot_add_song_to_default_playlist():
    with pytest.raises(HTTPException) as exc_info:
        await add_song(
            playlist_id=8,
            payload=AddSongRequest(song_id=14),
            db=StubSession([default_playlist()]),
            user=SimpleNamespace(id=1, is_admin=False),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Only admins can change default playlists"


@pytest.mark.asyncio
async def test_adding_song_already_in_playlist_returns_conflict():
    with pytest.raises(HTTPException) as exc_info:
        await add_song(
            playlist_id=8,
            payload=AddSongRequest(song_id=14),
            db=StubSession([default_playlist(), SimpleNamespace(id=14), 21]),
            user=SimpleNamespace(id=1, is_admin=True),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Song already exists in playlist"


@pytest.mark.asyncio
async def test_concurrent_duplicate_insert_returns_conflict():
    db = StubSession(
        [default_playlist(), SimpleNamespace(id=14), None, 21],
        flush_error=IntegrityError("insert", {}, Exception("duplicate")),
    )

    with pytest.raises(HTTPException) as exc_info:
        await add_song(
            playlist_id=8,
            payload=AddSongRequest(song_id=14),
            db=db,
            user=SimpleNamespace(id=1, is_admin=True),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Song already exists in playlist"


@pytest.mark.asyncio
async def test_youtube_url_adds_imported_song_to_playlist(monkeypatch):
    playlist = user_playlist()

    async def import_song(_db, youtube_url):
        assert youtube_url == "https://youtu.be/example"
        return SimpleNamespace(id=14), True

    monkeypatch.setattr("app.api.v1.playlists.get_or_create_youtube_song", import_song)
    db = StubSession([playlist, None, playlist])

    result = await add_song(
        playlist_id=9,
        payload=AddSongRequest(youtube_url="https://youtu.be/example"),
        db=db,
        user=SimpleNamespace(id=1, is_admin=False),
    )

    assert result is playlist
    assert any(
        isinstance(item, PlaylistSong) and item.playlist_id == 9 and item.song_id == 14
        for item in db.added
    )


@pytest.mark.asyncio
async def test_playlist_creation_assigns_user_as_owner_for_admin_and_non_admin():
    for is_admin in (False, True):
        db = StubSession([])
        playlist = await create_playlist(
            payload=PlaylistCreate(name="My playlist"),
            db=db,
            user=SimpleNamespace(id=3, is_admin=is_admin),
        )

        assert playlist.user_id == 3
        assert playlist.playlist_type == PlaylistType.USER


@pytest.mark.asyncio
async def test_non_admin_cannot_create_default_playlist():
    with pytest.raises(HTTPException) as exc_info:
        await create_playlist(
            payload=PlaylistCreate(name="Public", playlist_type=PlaylistType.DEFAULT),
            db=StubSession([]),
            user=SimpleNamespace(id=3, is_admin=False),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_create_default_playlist():
    db = StubSession([])

    playlist = await create_playlist(
        payload=PlaylistCreate(name="Featured", playlist_type=PlaylistType.DEFAULT),
        db=db,
        user=SimpleNamespace(id=3, is_admin=True),
    )

    assert playlist.user_id is None
    assert playlist.playlist_type == PlaylistType.DEFAULT


def test_add_song_payload_requires_exactly_one_source():
    assert AddSongRequest(song_id=7).song_id == 7
    assert AddSongRequest(youtube_url="https://www.youtube.com/watch?v=abc").youtube_url

    with pytest.raises(ValueError):
        AddSongRequest()
    with pytest.raises(ValueError):
        AddSongRequest(song_id=7, youtube_url="https://youtu.be/abc")
    with pytest.raises(ValueError):
        AddSongRequest(youtube_url="http://127.0.0.1/video")
