import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.managers.auth_manager import AuthManager
from app.models import User
from app.schemas import UserOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


async def get_auth_manager(db: AsyncSession = Depends(get_db)) -> AuthManager:
    return AuthManager(db)


@router.post("/google")
async def google_auth(
    request: Request,
    auth_manager: AuthManager = Depends(get_auth_manager),
) -> UserOut:
    user = await auth_manager.get_current_user(request)
    return UserOut.model_validate(user)


@router.get("/users/me")
async def get_me(
    request: Request,
    auth_manager: AuthManager = Depends(get_auth_manager),
) -> UserOut:
    user = await auth_manager.get_current_user(request)
    return UserOut.model_validate(user)
