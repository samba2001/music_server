from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Playlist, PlaylistTrack


class PlaylistRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(self, user_id: int) -> list[Playlist]:
        result = await self.session.execute(select(Playlist).where((Playlist.user_id.is_(None)) | (Playlist.user_id == user_id)))
        return list(result.scalars().all())

    async def get_by_id(self, playlist_id: int) -> Playlist | None:
        return await self.session.get(Playlist, playlist_id)

    async def create(self, *, user_id: int, name: str) -> Playlist:
        playlist = Playlist(user_id=user_id, name=name)
        self.session.add(playlist)
        await self.session.flush()
        return playlist

    async def clone(self, *, source: Playlist, user_id: int) -> Playlist:
        clone = Playlist(user_id=user_id, name=source.name, cloned_from_id=source.id)
        self.session.add(clone)
        await self.session.flush()
        return clone

    async def add_track(self, *, playlist_id: int, song_id: int, position: int) -> None:
        self.session.add(PlaylistTrack(playlist_id=playlist_id, song_id=song_id, position=position))

    async def reorder_tracks(self, *, playlist_id: int, tracks: list[dict]) -> None:
        for item in tracks:
            result = await self.session.execute(select(PlaylistTrack).where(PlaylistTrack.playlist_id == playlist_id, PlaylistTrack.song_id == item["song_id"]))
            track = result.scalar_one_or_none()
            if track is not None:
                track.position = item["position"]

    async def delete(self, playlist: Playlist) -> None:
        await self.session.delete(playlist)
        await self.session.commit()
