from fastapi import APIRouter, HTTPException, status
from app.auth.db import create_user, get_user_by_email
from app.auth.password import hash_password, verify_password
from app.auth.schemas import RegisterBody, LoginBody, TokenResponse, UserPublic
from app.auth.tokens import create_access_token


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(prefix="/register", response_model=TokenResponse)
async def register(body: RegisterBody):
    """Register new user and return the token generated with user id"""
    if get_user_by_email(body.email):
        # Cant have the same email registered. Its a unique field
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # Hash password for security reasons
    password_hash = hash_password(body.password)
    user_id = create_user(body.email, password_hash, body.display_name)
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
