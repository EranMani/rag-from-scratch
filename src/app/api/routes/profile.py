import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import get_current_user
from app.profile.db import get_profile_by_user_id
from app.profile.schemas import UserProfilePublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/me", response_model=UserProfilePublic)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Return the profile for the authenticated user.

    A profile is created automatically on registration, so a missing profile
    indicates a data integrity problem — logged server-side for diagnosis.
    """
    user_id: str = current_user["id"]

    profile = await asyncio.to_thread(get_profile_by_user_id, user_id)
    if profile is None:
        logger.warning(
            "Profile not found for user_id=%s — data integrity anomaly", user_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Contact support if this persists.",
        )

    return profile
