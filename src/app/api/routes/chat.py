"""
POST /api/chat — the live bridge between the HTTP client and the LangGraph agent.

This is where the entire auth + profile + agent pipeline converges into a single
streaming response. The endpoint:
    1. Authenticates (optional or required, per config) via JWT.
    2. Loads mastery_level from profile/db.py (LTM → adaptive-prompting).
    3. Builds initial AgentState and invokes the compiled graph.
    4. Streams LLM tokens as SSE events in real time.

Memory model (two layers):
    Short-Term Memory — LangGraph checkpointer keyed by thread_id (user_id or session_id).
        Prior HumanMessage/AIMessage turns are replayed automatically each request.
    Long-Term Memory — profile/db.py (mastery_level, topic_scores). Injected fresh into
        initial_state every turn so the graph always sees current mastery, not stale state.

The graph is accessed from app.state.rag_graph — never from a module-level import —
so the MemorySaver checkpointer and conversation history survive across requests.

SSE event schema:
    {"type": "token", "content": "<partial text>"}  — one per LLM token
    {"type": "done",  "answer": "<text>",
                      "user_level": "<level>",
                      "assessed_topics": {}}         — final summary event

Why SSE: LLM responses take seconds. Streaming tokens as they arrive keeps the UI
responsive; waiting for full completion feels like the system is hanging.
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
    """Inbound payload for a chat turn.

    user_id in the body is intentionally ignored — the trusted identity always
    comes from the JWT (defense against spoofed requests).
    """
    question: str
    session_id: str | None = None
    user_id: str | None = None  # ignored — trusted user_id comes from JWT


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

async def current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """Resolve the Bearer token to a user dict, or None for anonymous callers.

    Unlike get_current_user in deps.py, invalid/expired tokens return None instead of 401,
    so anonymous chat remains possible when settings.allow_anonymous_chat is True.
    """
    if creds is None:
        return None

    from app.auth.tokens import decode_access_token
    from app.auth.db import get_user_by_id

    try:
        uid = decode_access_token(creds.credentials).get("sub")
        if uid:
            return await asyncio.to_thread(get_user_by_id, uid)
    except Exception:
        pass  # malformed or expired token → treat as anonymous

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

    Graph lives on app.state so MemorySaver persists across requests in this process.
    thread_id (user_id or session_id) lets the checkpointer replay prior turns;
    initial_state is rebuilt each request with fresh LTM fields from the profile DB.
    """
    # Prevent unauthorized users from gaining access to the agent when anonymous chat is disabled
    if not settings.allow_anonymous_chat and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="login required",
        )

    # Get graph from FastAPI app state — shared MemorySaver across all requests in this process
    rag_graph = request.app.state.rag_graph
    session_id: str = req.session_id or str(uuid.uuid4())

    # Trust only the user_id from the verified JWT, never from the request body.
    user_id: str | None = current_user["id"] if current_user else None
    user_level = await asyncio.to_thread(get_user_level, user_id)

    # Reset the state for every request — bridge between LTM (profile DB) and this turn's input.
    # We inject mastery_level and related fields fresh from the database each time.
    # Per-turn AgentState envelope — fields match agents/state.py.
    # Only the current HumanMessage is in messages[]; prior turns come from the checkpointer.
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
        "is_mcq": False,
        "pending_mcq_correct_answer": None,
        "trace_id": str(uuid.uuid4()),
        "latency_ms": 0,
        "cache_hit": "miss",
    }

    # initial_state holds only this turn's payload + fresh LTM fields.
    # LangGraph checkpointer uses thread_id to merge with all prior chat history (STM).
    config: dict = {"configurable": {"thread_id": user_id or session_id}}

    async def generate_stream():
        """Async generator: yield SSE lines from LangGraph event stream.

        Takes graph events and translates them into simple messages the browser can display.
        No blocking I/O inside this generator — all calls are async.
        Relies on async iteration over rag_graph.astream_events().
        """
        final_state: dict = {}

        # astream_events lets you peek into the graph and catch events in between —
        # without waiting for the whole process to finish
        async for event in rag_graph.astream_events(
            initial_state, config=config, version="v2"
        ):
            # Look for events that come directly from the generate node.
            # Prevents sending the agent's inner thoughts (e.g. assess node) to the user.
            # Only stream the words the agent produces for the final answer.
            if (
                event["event"] == "on_chat_model_stream"
                and event.get("metadata", {}).get("langgraph_node") == "generate"
            ):
                # Every time the model emits a word (token), send it as a "token" SSE event
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield (
                        f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
                    )
            # Wait for on_chain_end on the whole graph — final_state is captured after all nodes finish
            elif event["event"] == "on_chain_end" and event.get("name") == "LangGraph":
                final_state = event["data"].get("output", {})

        # Called after the graph run completes — packs the full answer + updated profile fields
        chat_response: ChatResponse = build_chat_response(final_state)
        yield (
            f"data: {json.dumps({'type': 'done', **chat_response.model_dump()})}\n\n"
        )

    # StreamingResponse handles responses that are too large or built incrementally (token by token)
    return StreamingResponse(generate_stream(), media_type="text/event-stream")
