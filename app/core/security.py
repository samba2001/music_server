from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models import User

ACCESS_TOKEN_COOKIE = "access_token"


def create_access_token(subject: str | int, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JWT access token for the given subject (User ID)."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode = {"sub": str(subject), "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to authenticate requests.

    Extracts and validates the internal JWT access token from either:
    1. 'Authorization: Bearer <token>' header
    2. 'access_token' HTTP-only cookie
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token: Optional[str] = None

    # 1. Try Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()

    # 2. Fallback to access_token HTTP-only cookie
    if not token:
        token = request.cookies.get(ACCESS_TOKEN_COOKIE)

    if not token:
        raise credentials_exception

    # 3. Validate internal JWT token
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id_raw = payload.get("sub")
        if user_id_raw is None:
            raise credentials_exception
        user_id = int(user_id_raw)
    except (JWTError, ValueError):
        raise credentials_exception

    # 4. Retrieve user from database
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_exception

    return user