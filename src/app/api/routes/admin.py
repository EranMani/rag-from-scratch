"""
Admin routes — privileged operations on user identity records.

These endpoints allow managing the user base (listing, deletion). Every route
requires a valid Bearer token via get_current_user, so only authenticated users
can perform admin actions.

Connection to the agent system:
    Deleting a user here triggers ON DELETE CASCADE in the DB, which removes
    their mastery profile (profile/db.py) and effectively erases the agent's
    Long-Term Memory for that user. The thread_id anchor is gone, so any
    future LangGraph checkpoint for that identity becomes unreachable.

    asyncio.to_thread offloads the synchronous SQLite calls to a worker thread,
    keeping the FastAPI event loop free for concurrent agent conversations.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.db import list_users, delete_user
from app.auth.deps import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def get_users(current_user: dict = Depends(get_current_user)) -> list[dict]:
    """List all registered users. Requires authentication."""
    return await asyncio.to_thread(list_users)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a user by ID. Returns 204 on success, 404 if user doesn't exist.

    Cascades to profile deletion — the agent loses all memory of this user.
    """
    deleted = await asyncio.to_thread(delete_user, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
