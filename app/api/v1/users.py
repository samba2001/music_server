from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user

# Change prefix from "/user" to "/users"
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def me(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Return a simple user profile
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "google_id": current_user.google_id,
        "is_admin": current_user.is_admin,
    }