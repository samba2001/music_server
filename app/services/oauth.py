from typing import Dict

import anyio
from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.core.config import settings


def _verify_sync(id_token_str: str) -> Dict[str, str]:
    try:
        # Verify the token and get the claims (raises ValueError on failure)
        info = google_id_token.verify_oauth2_token(id_token_str, google_requests.Request(), settings.google_client_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google ID token") from exc
    if settings.google_client_id and info.get("aud") != settings.google_client_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token audience mismatch")
    if not info.get("sub") or not info.get("email"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token is missing required claims")
    return {"google_id": info["sub"], "email": info["email"], "name": info.get("name", info["email"]) }


async def verify_google_id_token(id_token: str) -> dict[str, str]:
    # Run the blocking google-auth verification in a thread to avoid blocking the event loop
    return await anyio.to_thread.run_sync(_verify_sync, id_token)
