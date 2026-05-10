"""
chat.py — POST /api/chat endpoint.

Replaces the synchronous run_rag_pipeline() call with a LangGraph
graph.astream_events() SSE stream.  The compiled graph is accessed from
app.state.rag_graph — never from a module-level import — so that the
MemorySaver checkpointer and its conversation history are shared across
all requests within a single application lifetime.

SSE event schema:
  {"type": "token",  "content": "<partial text>"}   — one per LLM token
  {"type": "done",   "answer": "<text>",
                     "user_level": "<level>",
                     "assessed_topics": {}}           — final event
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from app.auth.deps import security
from app.core.logging_config import logger
from app.core.config import settings
from app.profile.db import get_profile_by_user_id
from rag.chain import ChatResponse, build_chat_response

router = APIRouter(prefix="/api", tags=["chat"])


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None
    user_id: str | None = None  # ignored — trusted user_id comes from JWT


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

async def current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """Resolve the Bearer token to a user dict, or None for anonymous callers."""
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


# ---------------------------------------------------------------------------
# Profile helper
# ---------------------------------------------------------------------------

def get_user_level(
    user_id: str | None,
) -> Literal["novice", "beginner", "intermediate", "advanced", "expert"]:
    """Return the persisted mastery_level for user_id, or 'novice' for anonymous.

    This is a synchronous DB call — callers must wrap it with asyncio.to_thread.
    Falls back to 'novice' if the profile row does not exist yet (e.g., first
    request before any assessment has run).
    """
    if user_id is None:
        return "novice"
    profile = get_profile_by_user_id(user_id)
    if profile is None:
        return "novice"
    level = profile.get("mastery_level", "novice")
    # Guard: coerce any unexpected DB value to the Literal set.
    valid: set[str] = {"novice", "beginner", "intermediate", "advanced", "expert"}
    if level not in valid:
        logger.warning(
            "get_user_level: unexpected mastery_level %r for user_id=%r — coercing to novice",
            level,
            user_id,
        )
        return "novice"  # type: ignore[return-value]
    return level  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(
    req: ChatRequest,
    request: Request,
    current_user: dict | None = Depends(current_user_optional),
) -> StreamingResponse:
    """Stream a RAG response as Server-Sent Events.

    The graph is retrieved from app.state so that the MemorySaver checkpointer
    and its conversation history survive across all requests in this process.
    Conversation continuity is achieved by passing session_id as thread_id in
    the LangGraph config — the checkpointer replays prior turns automatically.
    """
    if not settings.allow_anonymous_chat and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="login required",
        )

    rag_graph = request.app.state.rag_graph
    session_id: str = req.session_id or str(uuid.uuid4())
    # Trust only the user_id from the verified JWT, never from the request body.
    user_id: str | None = current_user["id"] if current_user else None
    user_level = await asyncio.to_thread(get_user_level, user_id)

    initial_state: dict = {
        "messages": [HumanMessage(content=req.question)],
        "question": req.question,
        "user_id": user_id,
        "user_level": user_level,
        "docs": [],
        "retrieval_source": "",
        "answer": "",
        "topic_scores_delta": {},
        "identified_gaps": [],
        "assessment_error": False,
        "trace_id": str(uuid.uuid4()),
        "latency_ms": 0,
        "cache_hit": "miss",
    }
    config: dict = {"configurable": {"thread_id": session_id}}

    async def generate_stream():
        """Async generator: yield SSE lines from LangGraph event stream.

        No blocking I/O inside this generator — all calls are async.
        The generator relies exclusively on async iteration over
        rag_graph.astream_events(), which is itself an async generator.
        """
        final_state: dict = {}

        async for event in rag_graph.astream_events(
            initial_state, config=config, version="v2"
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield (
                        f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
                    )
            elif event["event"] == "on_chain_end" and event.get("name") == "LangGraph":
                final_state = event["data"].get("output", {})

        chat_response: ChatResponse = build_chat_response(final_state)
        yield (
            f"data: {json.dumps({'type': 'done', **chat_response.model_dump()})}\n\n"
        )

    return StreamingResponse(generate_stream(), media_type="text/event-stream")
