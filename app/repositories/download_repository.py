from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DownloadRequest


class DownloadRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_youtube_id(self, youtube_id: str) -> DownloadRequest | None:
        result = await self.session.execute(select(DownloadRequest).where(DownloadRequest.youtube_id == youtube_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, request_id: int) -> DownloadRequest | None:
        return await self.session.get(DownloadRequest, request_id)

    async def create(self, *, youtube_url: str, youtube_id: str, requested_by_user_id: int | None) -> DownloadRequest:
        request = DownloadRequest(youtube_url=youtube_url, youtube_id=youtube_id, requested_by_user_id=requested_by_user_id, status="queued")
        self.session.add(request)
        await self.session.flush()
        return request

    async def list(self) -> list[DownloadRequest]:
        result = await self.session.execute(select(DownloadRequest).order_by(DownloadRequest.id.desc()))
        return list(result.scalars().all())

    async def update_status(self, request: DownloadRequest, *, status: str, error_message: str | None = None) -> None:
        request.status = status
        request.error_message = error_message
        await self.session.commit()
