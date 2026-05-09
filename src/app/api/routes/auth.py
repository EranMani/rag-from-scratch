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
    return UserPublic(
        user_id=user["id"],
        email=user["email"],
        display_name=user["display_name"],
    )


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterBody):
    """Register new user and return the token generated with user id"""
    if get_user_by_email(body.email):
        # Cant have the same email registered. Its a unique field
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Hash password for security reasons
    password_hash = hash_password(body.password)
    user_id = create_user(body.email, password_hash, body.display_name)

    # create_profile (not get_or_create_profile) — registration is the profile's creation event;
    # we don't need the returned dict, and IntegrityError on a retry race is swallowed below.
    # Auto-create the user profile immediately after registration.
    # IntegrityError on a duplicate (e.g., a retry race) is swallowed — the
    # profile already exists and the user can still log in. Any other DB error
    # propagates as an unhandled 500 so it surfaces in logs.
    try:
        await asyncio.to_thread(create_profile, user_id)
    except sqlite3.IntegrityError:
        pass  # duplicate insert lost a race — profile already exists

    # Generate the token using the user id and email as extra
    token = create_access_token(sub=user_id, extra={"email": body.email})

    return TokenResponse(access_token=token, user_id=user_id)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginBody):
    # Fetch user by email
    row = get_user_by_email(body.email)

    # If no user found or password not varified, raise error
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password")

    # Create the token for the user
    token = create_access_token(sub=row["id"], extra={"email": row["email"]})

    return TokenResponse(access_token=token, user_id=row["id"])
