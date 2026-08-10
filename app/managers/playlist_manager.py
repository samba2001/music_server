from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Playlist, PlaylistTrack
from app.repositories.playlist_repository import PlaylistRepository


class PlaylistManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.playlist_repo = PlaylistRepository(session)

    async def list_playlists(self, user_id: int) -> list[Playlist]:
        return await self.playlist_repo.list_for_user(user_id)

    async def create_playlist(self, *, user_id: int, name: str) -> Playlist:
        return await self.playlist_repo.create(user_id=user_id, name=name)

    async def clone_playlist(self, *, playlist_id: int, user_id: int) -> Playlist:
        source = await self.playlist_repo.get_by_id(playlist_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Playlist not found")
        clone = await self.playlist_repo.clone(source=source, user_id=user_id)
        tracks = []
        for track in sorted(source.tracks, key=lambda item: item.position):
            tracks.append({"song_id": track.song_id, "position": track.position})
        for track in tracks:
            await self.playlist_repo.add_track(playlist_id=clone.id, song_id=track["song_id"], position=track["position"])
        await self.session.commit()
        return clone

    async def reorder_tracks(self, *, playlist_id: int, user_id: int, tracks: list[dict]) -> None:
        playlist = await self.playlist_repo.get_by_id(playlist_id)
        if playlist is None:
            raise HTTPException(status_code=404, detail="Playlist not found")
        if playlist.user_id not in {None, user_id}:
            raise HTTPException(status_code=403, detail="Forbidden")
        await self.playlist_repo.reorder_tracks(playlist_id=playlist_id, tracks=tracks)
        await self.session.commit()

    async def delete_playlist(self, *, playlist_id: int, user_id: int) -> None:
        playlist = await self.playlist_repo.get_by_id(playlist_id)
        if playlist is None:
            raise HTTPException(status_code=404, detail="Playlist not found")
        if playlist.user_id not in {None, user_id}:
            raise HTTPException(status_code=403, detail="Forbidden")
        await self.playlist_repo.delete(playlist)
