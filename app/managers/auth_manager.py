import logging
from typing import Optional

from fastapi import HTTPException, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import BYPASS_AUTH, GOOGLE_CLIENT_ID
from app.repositories.user_repository import UserRepository
from app.models import User

logger = logging.getLogger(__name__)


class AuthManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_current_user(self, request: Request) -> User:
        if BYPASS_AUTH:
            logger.warning("AUTH BYPASSED: Using dev admin account")
            return await self.get_or_create_default_user()

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer token")

        token = auth_header.split(" ", 1)[1].strip()
        try:
            info = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID or None)
        except Exception as exc:
            logger.warning("Google auth failed: %s", exc)
            raise HTTPException(status_code=401, detail="Invalid Google token") from exc

        email = info.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Google token missing email")

        user = await self.user_repo.get_by_email(email)
        if user is None:
            user = await self.user_repo.create(email=email, name=info.get("name", "Google User"))
        return user

    async def get_or_create_default_user(self) -> User:
        user = await self.user_repo.get_by_email("admin@homelab.local")
        if user is None:
            user = await self.user_repo.create(email="admin@homelab.local", name="Admin")
        return user
