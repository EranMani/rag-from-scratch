"""
Tests for Commit 10 — langgraph-graph-assembly, chat.py HTTP layer.

Coverage targets (Quinn gate):
1. POST /api/chat returns Content-Type: text/event-stream (Spec Gate 1)
2. Token events arrive before done event (Spec Gate 2)
3. done event schema and topic_scores_delta → assessed_topics key mapping (Spec Gate 3)
4. 401 when allow_anonymous_chat=False and no Authorization header (security gate)

Design notes:
- Construct a lightweight test app that mounts only the chat router, with no lifespan.
  app.state.rag_graph is set directly on the test app — not via a real lifespan.
- current_user_optional is overridden via FastAPI dependency_overrides.
- FakeGraph replaces the real CompiledStateGraph. Its astream_events method is an
  async generator that yields pre-constructed LangGraph v2 event dicts.
- get_user_level (defined in chat.py) is patched via unittest.mock.patch for
  authenticated tests (1-3) because it calls get_profile_by_user_id which requires
  a live SQLite DB. We patch it at the source: "app.api.routes.chat.get_user_level".
- settings.allow_anonymous_chat is patched via the module-level singleton for Test 4.
  The lru_cache on get_settings() means we must patch the settings *instance*
  attribute directly on the already-imported module-level singleton, not the class.
- SSE frames are collected by iterating over the streaming response in with-block.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.chat import router, current_user_optional
import app.core.config as config_module

# ---------------------------------------------------------------------------
# Minimal test app — chat router only, no lifespan
# ---------------------------------------------------------------------------

_test_app = FastAPI()
_test_app.include_router(router)

_FAKE_USER = {
    "id": "test-user-id",
    "email": "nova@example.com",
    "display_name": "Nova",
    "password_hash": "hashed",
    "created_at": "2026-01-01T00:00:00+00:00",
}


async def _override_authenticated() -> dict:
    """Dependency override: always returns a fake authenticated user."""
    return _FAKE_USER


async def _override_anonymous() -> None:
    """Dependency override: simulates an unauthenticated caller."""
    return None


# ---------------------------------------------------------------------------
# FakeGraph — async generator test double for CompiledStateGraph
# ---------------------------------------------------------------------------

class FakeGraph:
    """Minimal stand-in for a CompiledStateGraph.

    astream_events is constructed per-call by passing a list of event dicts.
    The constructor takes that list so each test can inject its own events.
    """

    def __init__(self, events: list[dict[str, Any]]) -> None:
        self._events = events

    async def astream_events(
        self, *args: Any, **kwargs: Any
    ) -> AsyncGenerator[dict[str, Any], None]:
        for event in self._events:
            yield event


def _make_chunk_event(content: str) -> dict[str, Any]:
    """Build an on_chat_model_stream event whose chunk.content == content."""
    chunk = type("Chunk", (), {"content": content})()
    return {
        "event": "on_chat_model_stream",
        "name": "ChatOpenAI",
        "metadata": {"langgraph_node": "generate"},
        "data": {"chunk": chunk},
    }


def _make_chain_end_event(output: dict[str, Any]) -> dict[str, Any]:
    """Build the on_chain_end/LangGraph event that triggers the done frame."""
    return {
        "event": "on_chain_end",
        "name": "LangGraph",
        "data": {"output": output},
    }


def _collect_sse_frames(response) -> list[dict[str, Any]]:
    """Read all SSE data lines from a streaming TestClient response.

    Each SSE frame has the form: "data: <json>\\n\\n"
    We split on newlines, strip "data: " prefix, skip blank lines, parse JSON.
    """
    frames: list[dict[str, Any]] = []
    for line in response.iter_lines():
        stripped = line.strip()
        if stripped.startswith("data:"):
            payload = stripped[len("data:"):].strip()
            if payload:
                frames.append(json.loads(payload))
    return frames


# ---------------------------------------------------------------------------
# Test 1 — Content-Type: text/event-stream (Spec Gate 1)
# ---------------------------------------------------------------------------

class TestChatContentType:
    """POST /api/chat must respond with Content-Type: text/event-stream."""

    def test_response_is_event_stream(self):
        # Zero-event graph — we only care about headers, not body content.
        _test_app.state.rag_graph = FakeGraph(events=[])

        _test_app.dependency_overrides[current_user_optional] = _override_authenticated
        # Patch get_user_level to avoid a live SQLite call for the fake user's profile.
        with patch("app.api.routes.chat.get_user_level", return_value="novice"):
            try:
                with TestClient(_test_app, raise_server_exceptions=True) as client:
                    with client.stream("POST", "/api/chat", json={"question": "test"}) as response:
                        assert response.status_code == 200, (
                            f"Expected 200, got {response.status_code}: {response.text}"
                        )
                        ct = response.headers.get("content-type", "")
                        assert ct.startswith("text/event-stream"), (
                            f"Expected content-type to start with 'text/event-stream', got: {ct!r}"
                        )
            finally:
                _test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test 2 — Token events arrive before done event (Spec Gate 2)
# ---------------------------------------------------------------------------

class TestChatEventOrder:
    """Token frames must precede the done frame in the SSE stream."""

    def test_token_before_done(self):
        events = [
            _make_chunk_event("hello"),
            _make_chain_end_event({"user_level": "novice", "topic_scores_delta": {}}),
        ]
        _test_app.state.rag_graph = FakeGraph(events=events)

        _test_app.dependency_overrides[current_user_optional] = _override_authenticated
        with patch("app.api.routes.chat.get_user_level", return_value="novice"):
            try:
                with TestClient(_test_app, raise_server_exceptions=True) as client:
                    with client.stream("POST", "/api/chat", json={"question": "test"}) as response:
                        frames = _collect_sse_frames(response)
            finally:
                _test_app.dependency_overrides.clear()

        token_frames = [f for f in frames if f.get("type") == "token"]
        done_frames = [f for f in frames if f.get("type") == "done"]

        assert len(token_frames) >= 1, (
            f"Expected at least one token frame, got frames: {frames}"
        )
        assert len(done_frames) == 1, (
            f"Expected exactly one done frame, got done_frames: {done_frames}"
        )

        # Token frame must precede the done frame in the ordered list.
        first_token_idx = next(i for i, f in enumerate(frames) if f.get("type") == "token")
        done_idx = next(i for i, f in enumerate(frames) if f.get("type") == "done")
        assert first_token_idx < done_idx, (
            f"Token frame (index {first_token_idx}) must come before done frame (index {done_idx})"
        )


# ---------------------------------------------------------------------------
# Test 3 — done event schema and key mapping (Spec Gate 3)
# ---------------------------------------------------------------------------

class TestChatDoneSchema:
    """The done frame must carry user_level and assessed_topics (mapped from topic_scores_delta)."""

    def test_done_frame_schema_and_key_mapping(self):
        events = [
            _make_chunk_event("some answer"),
            _make_chain_end_event(
                {
                    "user_level": "intermediate",
                    "topic_scores_delta": {"vectors": 0.2},
                }
            ),
        ]
        _test_app.state.rag_graph = FakeGraph(events=events)

        _test_app.dependency_overrides[current_user_optional] = _override_authenticated
        with patch("app.api.routes.chat.get_user_level", return_value="intermediate"):
            try:
                with TestClient(_test_app, raise_server_exceptions=True) as client:
                    with client.stream("POST", "/api/chat", json={"question": "test"}) as response:
                        frames = _collect_sse_frames(response)
            finally:
                _test_app.dependency_overrides.clear()

        done_frames = [f for f in frames if f.get("type") == "done"]
        assert len(done_frames) == 1, f"Expected exactly one done frame, got: {done_frames}"
        done = done_frames[0]

        assert done["type"] == "done", f"done frame type field: {done}"
        assert done["user_level"] == "intermediate", (
            f"Expected user_level='intermediate', got: {done.get('user_level')!r}"
        )
        assert done["assessed_topics"] == {"vectors": 0.2}, (
            f"Expected assessed_topics={{'vectors': 0.2}}, got: {done.get('assessed_topics')!r}"
        )
        # Verify the key is assessed_topics (not topic_scores_delta).
        assert "assessed_topics" in done, "done frame must use key 'assessed_topics'"
        assert "topic_scores_delta" not in done, (
            "done frame must NOT expose raw key 'topic_scores_delta'"
        )


# ---------------------------------------------------------------------------
# Test 4 — 401 when allow_anonymous_chat=False and no auth (security gate)
# ---------------------------------------------------------------------------

class TestChatAnonymousBlocked:
    """When allow_anonymous_chat=False, unauthenticated requests must receive 401."""

    def test_no_auth_returns_401_when_anonymous_disallowed(self):
        _test_app.state.rag_graph = FakeGraph(events=[])

        _test_app.dependency_overrides[current_user_optional] = _override_anonymous
        # Patch the module-level settings singleton directly.
        # Using the already-imported object avoids lru_cache re-evaluation.
        original_value = config_module.settings.allow_anonymous_chat
        config_module.settings.allow_anonymous_chat = False
        try:
            client = TestClient(_test_app, raise_server_exceptions=False)
            response = client.post("/api/chat", json={"question": "test"})
        finally:
            config_module.settings.allow_anonymous_chat = original_value
            _test_app.dependency_overrides.clear()

        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert "login required" in body.get("detail", "").lower(), (
            f"Expected 'login required' in detail, got: {body.get('detail')!r}"
        )
