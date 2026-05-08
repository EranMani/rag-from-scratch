from typing import Annotated
import asyncio
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from rag.chain import run_rag_pipeline
from app.core.config import settings
from app.auth.deps import security

router = APIRouter(prefix="/api", tags=["chat"])



class ChatRequest(BaseModel):
    question: str
    session_id: str = None
    user_id: str = None


class ChatResponse(BaseModel):
    answer: str
    cache_hit: str
    chunks: list[dict]
    latency_ms: int
    trace_id: str


async def current_user_optional(creds: HTTPAuthorizationCredentials | None = Depends(security)) -> dict | None:
    if creds is None:
        return None

    from app.auth.tokens import decode_access_token
    from app.auth.db import get_user_by_id
    try:
        uid = decode_access_token(creds.credentials).get("sub")
        if uid:
            return await asyncio.to_thread(get_user_by_id, uid)
    except Exception:
        pass

    return None


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, creds_user: Annotated[dict | None, Depends(current_user_optional)]):
    if not settings.allow_anonymous_chat and creds_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login required")
    
    # Use trusted user id only for security reasons. Ignore user id from client
    trusted_user_id = creds_user["id"] if creds_user else None
    
    with REQUEST_LATENCY.labels(endpoint="/chat").time():
        result = await asyncio.to_thread(
            run_rag_pipeline,
            question=body.question,
            session_id=body.session_id or str(uuid.uuid4()),
            user_id=trusted_user_id,
        )
    REQUEST_COUNT.labels(endpoint="/chat", status="success").inc()
    return ChatResponse(**result)