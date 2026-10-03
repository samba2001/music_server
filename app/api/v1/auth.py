import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models import RefreshToken, User
from app.schemas import GoogleAuthRequest, TokenResponse
from app.services.oauth import verify_google_id_token

router = APIRouter(prefix="/auth", tags=["auth"])


def hash_token(raw_token: str) -> str:
    """SHA-256 hash helper to avoid storing raw refresh tokens in the database."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    payload: GoogleAuthRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # 1. Verify Google ID token
    claims = await verify_google_id_token(payload.google_id_token)

    # 2. Get or create user
    user = await db.scalar(select(User).where(User.google_id == claims["google_id"]))
    if user is None:
        user = await db.scalar(select(User).where(User.email == claims["email"]))
    
    if user is None:
        user = User(**claims)
        db.add(user)
    else:
        user.name, user.email, user.google_id = (
            claims["name"],
            claims["email"],
            claims["google_id"],
        )
    
    await db.commit()
    await db.refresh(user)

    # 3. Create Short-lived Access Token
    access_token = create_access_token(str(user.id))
    access_expires_in = int(settings.access_token_expire_minutes * 60)

    # 4. Create Long-lived Refresh Token (30 Days)
    raw_refresh_token = secrets.token_urlsafe(64)
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    # 5. Store Hashed Refresh Token in Database
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh_token),
        expires_at=refresh_expires_at,
    )
    db.add(db_refresh_token)
    await db.commit()

    # 6. Set Cookies
    secure_cookie = settings.environment != "development"

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=access_expires_in,
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=30 * 24 * 3600,
        path="/api/v1/auth/refresh",
    )

    return TokenResponse(access_token=access_token, expires_in=access_expires_in)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    raw_refresh_token = request.cookies.get("refresh_token")
    if not raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token cookie missing",
        )

    hashed_input = hash_token(raw_refresh_token)

    # Fetch token record
    token_record = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hashed_input)
    )

    # TOKEN REUSE DETECTION (SECURITY THREAT)
    # If the token exists but is already revoked, an attacker or old token was used!
    if token_record and token_record.is_revoked:
        # Revoke ALL active sessions for this user across all devices
        user_tokens = await db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == token_record.user_id,
                RefreshToken.is_revoked == False,
            )
        )
        for t in user_tokens:
            t.is_revoked = True
        await db.commit()

        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/auth/refresh")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Security breach detected: Refresh token re-used. All sessions revoked.",
        )

    # Check for invalid or expired token
    now = datetime.now(timezone.utc)
    if not token_record or token_record.expires_at < now:
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/auth/refresh")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # ROTATION: Revoke the current refresh token
    token_record.is_revoked = True

    # Issue NEW Access Token
    new_access_token = create_access_token(str(token_record.user_id))
    access_expires_in = int(settings.access_token_expire_minutes * 60)

    # Issue NEW Refresh Token
    new_raw_refresh_token = secrets.token_urlsafe(64)
    new_refresh_record = RefreshToken(
        user_id=token_record.user_id,
        token_hash=hash_token(new_raw_refresh_token),
        expires_at=now + timedelta(days=30),
    )
    db.add(new_refresh_record)
    await db.commit()

    # Update Cookies
    secure_cookie = settings.environment != "development"

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=access_expires_in,
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=new_raw_refresh_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=30 * 24 * 3600,
        path="/api/v1/auth/refresh",
    )

    return TokenResponse(access_token=new_access_token, expires_in=access_expires_in)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_refresh_token = request.cookies.get("refresh_token")
    if raw_refresh_token:
        hashed_input = hash_token(raw_refresh_token)
        token_record = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hashed_input)
        )
        if token_record:
            token_record.is_revoked = True
            await db.commit()

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")

    return {"message": "Successfully logged out"}