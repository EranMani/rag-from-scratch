"""
FastAPI dependency — the authentication gate for the agent.

Validates the JWT, confirms the user exists in the DB via a thread-safe async call,
and provides the user identity required for personalizing the AI agent's state.

Why this matters for agentic systems:
    The user_id returned here is the anchor for the agent's entire memory.
    Without it, LangGraph cannot retrieve the correct thread_id, and the agent
    would "lose its memory" and restart context every single turn.

    In one sentence: only those with a valid Bearer token can initiate an
    interaction with the adaptive agent — saving LLM calls and protecting state.
"""


import asyncio
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.auth.db import get_user_by_id
from app.auth.tokens import decode_access_token

# Expects an Authorization: Bearer <token> header on incoming requests.
# auto_error=False means FastAPI won't raise its own 403 — we handle missing/invalid creds manually below.
security = HTTPBearer(auto_error=False)


async def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    # creds is injected by FastAPI from the Authorization header.
    # HTTP supports multiple auth schemes (Basic, Digest, etc.) — we only accept Bearer (JWT).
    # .lower() guards against clients sending "BEARER" or "Bearer" inconsistently.
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        # Decode the JWT and extract the "sub" claim (the user_id set during login)
        payload = decode_access_token(creds.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("no sub")
    except Exception:
        # Covers expired tokens, tampered signatures, and missing claims
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    # get_user_by_id is synchronous (SQLite). asyncio.to_thread offloads it to a
    # worker thread so the event loop stays free to serve other requests concurrently.
    row = await asyncio.to_thread(get_user_by_id, user_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return row
