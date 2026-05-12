import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.db import list_users, delete_user
from app.auth.deps import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def get_users(current_user: dict = Depends(get_current_user)) -> list[dict]:
    return await asyncio.to_thread(list_users)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(user_id: str, current_user: dict = Depends(get_current_user)):
    deleted = await asyncio.to_thread(delete_user, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
