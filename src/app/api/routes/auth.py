"""
Auth routes — the orchestrator that wires identity modules into HTTP endpoints.

This router is the "conductor" that coordinates the auth pipeline:
    RegisterBody (schemas) → hash_password (password) → create_user (db) →
    create_profile (profile/db) → create_access_token (tokens) → TokenResponse

    LoginBody (schemas) → get_user_by_email (db) → verify_password (password) →
    create_access_token (tokens) → TokenResponse

Connection to the agent:
    Registration is the moment the agent's Long-Term Memory is born — create_profile
    initializes the mastery state that LangGraph will personalize over time.
    Login produces the JWT whose `sub` claim becomes the thread_id anchor for every
    subsequent agent interaction.
"""

import asyncio
import sqlite3

from fastapi import APIRouter, HTTPException, status, Depends
from app.auth.db import create_user, get_user_by_email
from app.auth.password import hash_password, verify_password
from app.auth.schemas import RegisterBody, LoginBody, TokenResponse, UserPublic
from app.auth.tokens import create_access_token
from app.auth.deps import get_current_user
from app.profile.db import create_profile

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=UserPublic)
async def me(user: dict = Depends(get_current_user)):
    """Return the authenticated user's public profile (excludes password_hash)."""
    return UserPublic(
        user_id=user["id"],
        email=user["email"],
        display_name=user["display_name"],
    )


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterBody):
    """Create a new user + mastery profile, return a signed JWT.

    This is the birth of the agent's memory for this user — after this call,
    LangGraph has a thread_id anchor and an empty mastery profile to evolve.
    """
    if get_user_by_email(body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    password_hash = hash_password(body.password)
    user_id = create_user(body.email, password_hash, body.display_name)

    # create_profile (not get_or_create_profile) — registration is the canonical
    # creation event. IntegrityError on a retry race is safe to swallow because
    # the profile already exists and login will still work.
    try:
        await asyncio.to_thread(create_profile, user_id)
    except sqlite3.IntegrityError:
        pass  # duplicate insert lost a race — profile already exists

    token = create_access_token(sub=user_id, extra={"email": body.email})
    return TokenResponse(access_token=token, user_id=user_id)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginBody):
    """Authenticate credentials and return a signed JWT.

    The token's `sub` claim carries the user_id that deps.py will inject into
    AgentState on every subsequent request — linking this login to the agent's memory.
    """
    row = get_user_by_email(body.email)

    # Single error message for both "user not found" and "wrong password" —
    # prevents attackers from enumerating valid emails.
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid email or password")

    token = create_access_token(sub=row["id"], extra={"email": row["email"]})
    return TokenResponse(access_token=token, user_id=row["id"])
