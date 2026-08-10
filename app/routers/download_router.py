import logging
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.managers.auth_manager import AuthManager
from app.managers.download_manager import DownloadManager
from app.models import User
from app.schemas import DownloadRequestCreate, DownloadRequestOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/requests", tags=["downloads"])


async def get_download_manager(db: AsyncSession = Depends(get_db)) -> DownloadManager:
    return DownloadManager(db)


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    auth_manager = AuthManager(db)
    return await auth_manager.get_current_user(request)


@router.post("/download", response_model=DownloadRequestOut)
async def create_download_request(payload: DownloadRequestCreate, background_tasks: BackgroundTasks, manager: DownloadManager = Depends(get_download_manager), user: User = Depends(get_current_user)) -> DownloadRequestOut:
    request = await manager.create_download_request(youtube_url=payload.youtube_url, user_id=user.id)
    background_tasks.add_task(manager.process_download, request.id)
    return DownloadRequestOut.model_validate(request)


@router.get("", response_model=list[DownloadRequestOut])
async def list_requests(manager: DownloadManager = Depends(get_download_manager), user: User = Depends(get_current_user)) -> list[DownloadRequestOut]:
    requests = await manager.list_requests()
    return [DownloadRequestOut.model_validate(item) for item in requests]


@router.get("/{request_id}", response_model=DownloadRequestOut)
async def get_request(request_id: int, manager: DownloadManager = Depends(get_download_manager), user: User = Depends(get_current_user)) -> DownloadRequestOut:
    request = await manager.get_request(request_id)
    return DownloadRequestOut.model_validate(request)
