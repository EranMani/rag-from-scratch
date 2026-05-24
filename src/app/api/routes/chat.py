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
from functools import lru_cache
from typing import Literal

import numpy as np

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
from rag.embeddings.local_embedder import get_local_embeddings

router = APIRouter(prefix="/api", tags=["chat"])

# ---------------------------------------------------------------------------
# Navigation-intent detection — semantic similarity via the same embedder
# used for document retrieval (all-MiniLM-L6-v2, normalized embeddings).
# Anchors are computed once at first call and cached for the process lifetime.
# ---------------------------------------------------------------------------

_NAV_INTENT_THRESHOLD = 0.52

_NAV_ANCHOR_PHRASES = [
    "what should I learn?",
    "where do I start?",
    "I'm not sure where to begin",
    "can you guide me through the curriculum?",
    "what topics are covered here?",
    "help me navigate the learning path",
    "what's available to study?",
    "teach me from the beginning",
    "I don't know where to start",
    "show me what I can learn",
    "what's the course structure?",
    "how do I start learning RAG?",
    "give me an overview of the topics",
    "what's the learning roadmap?",
]

_NAV_CHIPS = [
    {"name": "Embeddings & Similarity",   "description": "How vectors represent meaning and measure similarity"},
    {"name": "RAG Pipeline Architecture", "description": "The overall structure: retrieve → augment → generate"},
    {"name": "Chunking Strategies",       "description": "How documents are split to improve retrieval precision"},
    {"name": "Vector Databases",          "description": "Storing and querying embeddings at scale"},
    {"name": "Retrieval Methods",         "description": "Semantic, keyword, hybrid search, and re-ranking"},
    {"name": "Context & Prompting",       "description": "Feeding the right context to the LLM for accurate answers"},
    {"name": "Evaluation & Metrics",      "description": "Measuring retrieval quality and answer correctness"},
    {"name": "Production Patterns",       "description": "Caching, observability, latency tuning, and deployment"},
]


@lru_cache(maxsize=1)
def _nav_anchor_embeddings() -> "np.ndarray":
    """Embed anchor phrases once; shape (N, 384). Called in a thread."""
    vecs = get_local_embeddings().embed_documents(_NAV_ANCHOR_PHRASES)
    return np.array(vecs, dtype=np.float32)


def _chips_for_level(level: str) -> list[dict]:
    """Return the subset of chips the user has unlocked based on their mastery level."""
    if level == "novice":
        return _NAV_CHIPS[:2]   # Phase 1: Embeddings & Similarity, RAG Pipeline Architecture
    if level == "intermediate":
        return _NAV_CHIPS[:6]   # Phase 1 + Phase 2
    return _NAV_CHIPS           # advanced / expert: all 8


def _is_nav_question(question: str) -> bool:
    """Return True if question is semantically close to any navigation-intent anchor.

    Runs synchronously — call via asyncio.to_thread from async context.
    Embeddings are unit-normalized so dot product == cosine similarity.
    """
    q_vec = np.array(
        get_local_embeddings().embed_query(question), dtype=np.float32
    )
    sims = _nav_anchor_embeddings() @ q_vec
    return bool(sims.max() > _NAV_INTENT_THRESHOLD)


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
) -> Literal["novice", "intermediate", "advanced", "expert"]:
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
    valid: set[str] = {"novice", "intermediate", "advanced", "expert"}
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
        "answer": "",
        "topic_scores_delta": {},
        "identified_gaps": [],
        "assessment_error": False,
        # is_mcq and pending_mcq_correct_answer are intentionally NOT reset here.
        # They must persist from the question-selection turn (N) to the answer-
        # evaluation turn (N+1) via the LangGraph checkpointer. Resetting them here
        # would cause every MCQ evaluation to fall through to the LLM grading path.
        "trace_id": str(uuid.uuid4()),
        "latency_ms": 0,
        "cache_hit": "miss",
    }

    # initial_state holds only this turn's payload + fresh LTM fields.
    # LangGraph checkpointer uses thread_id to merge with all prior chat history (STM).
    config: dict = {"configurable": {"thread_id": user_id or session_id}}

    # Run nav-intent check in a thread — embedding is CPU-bound.
    is_nav = await asyncio.to_thread(_is_nav_question, req.question)

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
        done_payload: dict = {"type": "done", **chat_response.model_dump()}
        if is_nav:
            done_payload["chips"] = _chips_for_level(user_level)
        yield f"data: {json.dumps(done_payload)}\n\n"

    # StreamingResponse handles responses that are too large or built incrementally (token by token)
    return StreamingResponse(generate_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Seed endpoint — auto-initiated intro, authenticated only
# ---------------------------------------------------------------------------

# Curriculum order for returning-user "next topic" recommendation
_CURRICULUM_ORDER = [
    "chunking_strategies",
    "embeddings_and_similarity",
    "retrieval_methods",
    "vector_databases",
    "context_and_prompting",
    "evaluation_and_metrics",
    "rag_pipeline_architecture",
    "document_ingestion",
    "langchain_fundamentals",
    "langgraph_fundamentals",
    "production_patterns",
]


def _build_seed_prompt(mastery_level: str, topic_scores: dict) -> str:
    """Build the seed prompt string for first-time or returning users.

    topic_scores values may be None — use (v or 0.0) throughout.
    """
    is_first_time = not topic_scores or all(
        (v or 0.0) == 0.0 for v in topic_scores.values()
    )

    if is_first_time:
        return (
            f"You are a RAG learning coach. A brand-new student (level: {mastery_level}) has just opened\n"
            "this app for the first time. Give them a short, exciting introduction that:\n"
            "1. Opens with a surprising, real-world use case where RAG solves something impressively\n"
            "   (e.g., a company's internal knowledge base that actually answers correctly)\n"
            "2. Explains in plain terms what RAG is — no jargon, analogy preferred for novice level\n"
            "3. Lists 2–3 things they'll understand by the end of this course\n"
            "4. Ends with an inviting question or \"pick a topic below to get started\"\n"
            "Keep it under 150 words. Sound like a coach who genuinely cares, not a textbook.\n"
            "Do not say \"I am an AI\"."
        )

    # Classify scores
    strengths: list[str] = []
    gaps: list[str] = []
    uncovered: list[str] = []

    for slug in _CURRICULUM_ORDER:
        score = topic_scores.get(slug)
        numeric = score or 0.0
        if numeric >= 0.7:
            strengths.append(slug)
        elif numeric > 0.0:
            gaps.append(slug)
        else:
            uncovered.append(slug)

    # Highest-priority next focus: biggest gap first; if no gaps, first uncovered in order
    if gaps:
        next_topic = gaps[0]
    elif uncovered:
        next_topic = uncovered[0]
    else:
        next_topic = strengths[-1] if strengths else _CURRICULUM_ORDER[0]

    strengths_list = ", ".join(strengths) if strengths else "none yet"
    gaps_list = ", ".join(gaps) if gaps else "none"
    uncovered_list = ", ".join(uncovered) if uncovered else "none"

    return (
        f"You are a RAG learning coach welcoming back a student. Their level: {mastery_level}.\n"
        "Topic progress:\n"
        f"  Strengths (score ≥ 0.7): {strengths_list}\n"
        f"  In progress (score < 0.7): {gaps_list}\n"
        f"  Not yet covered: {uncovered_list}\n\n"
        "Write a warm, specific welcome-back message (2–3 sentences max) that:\n"
        "1. Acknowledges one specific strength by name\n"
        f"2. Identifies the single highest-priority next focus area: {next_topic}\n"
        "3. Ends with an invitation to continue\n\n"
        "Be specific — name actual topics. Do not be generic.\n"
        "Sound like a coach who has been tracking their journey.\n"
        "Do not say \"I am an AI\"."
    )


def _get_profile_for_seed(user_id: str) -> tuple[str, dict]:
    """Return (mastery_level, topic_scores) for user_id. Synchronous — call via to_thread."""
    profile = get_profile_by_user_id(user_id) or {}
    level = profile.get("mastery_level", "novice")
    valid: set[str] = {"novice", "intermediate", "advanced", "expert"}
    if level not in valid:
        level = "novice"
    topic_scores: dict = profile.get("topic_scores") or {}
    return level, topic_scores


@router.post("/chat/seed")
async def chat_seed(
    request: Request,
    current_user: dict | None = Depends(current_user_optional),
) -> StreamingResponse:
    """Stream an auto-initiated intro message as Server-Sent Events.

    Always requires JWT auth — no anonymous access.
    Builds a seed prompt from the user's profile and invokes the graph identically
    to /api/chat. No nav-intent check — seed responses never include chips.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="login required",
        )

    rag_graph = request.app.state.rag_graph
    user_id: str = current_user["id"]

    mastery_level, topic_scores = await asyncio.to_thread(_get_profile_for_seed, user_id)
    seed_prompt = _build_seed_prompt(mastery_level, topic_scores)

    initial_state: dict = {
        "messages": [HumanMessage(content=seed_prompt)],
        "question": seed_prompt,
        "user_id": user_id,
        "user_level": mastery_level,
        "docs": [],
        "answer": "",
        "topic_scores_delta": {},
        "identified_gaps": [],
        "assessment_error": False,
        "trace_id": str(uuid.uuid4()),
        "latency_ms": 0,
        "cache_hit": "miss",
    }
    config: dict = {"configurable": {"thread_id": user_id}}

    async def generate_seed_stream():
        final_state: dict = {}
        async for event in rag_graph.astream_events(initial_state, config=config, version="v2"):
            if (
                event["event"] == "on_chat_model_stream"
                and event.get("metadata", {}).get("langgraph_node") == "generate"
            ):
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
            elif event["event"] == "on_chain_end" and event.get("name") == "LangGraph":
                final_state = event["data"].get("output", {})

        chat_response: ChatResponse = build_chat_response(final_state)
        done_payload: dict = {"type": "done", **chat_response.model_dump()}
        yield f"data: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(generate_seed_stream(), media_type="text/event-stream")
