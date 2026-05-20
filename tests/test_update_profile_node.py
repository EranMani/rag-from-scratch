"""
Tests for Commit 15 — profile-update-node.

Coverage targets (spec gates):

Gate 1: After a full graph invocation with user_id set, the profile row in SQLite
        has updated topic_scores.
Gate 2: interaction_count increments after each turn.
Gate 3: Fallback path (assessment_error=True) does not write to the DB.
Gate 4: Node works correctly when user_id is None (anonymous user — skip profile update).
Gate 5: last_activity_at is set to a valid ISO 8601 timestamp after each successful turn.

Design notes:
- All tests call update_profile_node directly with a synthetic AgentState dict.
  No live LangGraph graph or LLM is needed — the node is synchronous and testable
  in isolation.
- Gates 1, 2, and 5 use a real in-memory SQLite DB (via an in-process patched
  settings.sqlite_db_path pointing to ":memory:").  This validates that the full
  DB round-trip works, not just that update_profile() was called.
- Gate 3 patches update_profile() to assert it is NOT called on the error path,
  avoiding any DB dependency.
- Gate 4 is a pure unit test — no DB, no patches needed; user_id=None short-circuits
  before any import of db functions.
- Thread safety: update_profile_node is synchronous.  Tests run synchronously.
  No asyncio runner needed.
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from agents.nodes.update_profile import update_profile_node
from agents.state import AgentState


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _base_state(**overrides: Any) -> dict[str, Any]:
    """Minimal AgentState dict for update_profile_node unit tests."""
    base: dict[str, Any] = {
        "user_id": "user-abc",
        "assessment_error": False,
        "topic_scores_delta": {"vector_databases": 0.5},
        "identified_gaps": ["chunking_strategies"],
        "user_level": "intermediate",
        "question": "What is RAG?",
        "answer": "RAG = Retrieval-Augmented Generation.",
        "session_question_counts": {},
        "trace_id": "test-trace-15",
        "latency_ms": 0,
        "cache_hit": "miss",
    }
    base.update(overrides)
    return base


def _fake_profile(
    user_id: str = "user-abc",
    topic_scores: dict[str, float] | None = None,
    interaction_count: int = 3,
) -> dict:
    """Construct a profile dict as returned by get_profile_by_user_id."""
    return {
        "id": "profile-id-1",
        "user_id": user_id,
        "mastery_level": "intermediate",
        "interaction_count": interaction_count,
        "topic_scores": topic_scores if topic_scores is not None else {"rag_fundamentals": 0.4},
        "strengths": [],
        "gaps": [],
        "last_activity_at": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# Gate 1 — topic_scores updated in SQLite after successful invocation
# ---------------------------------------------------------------------------

class TestGate1TopicScoresUpdated:
    """After update_profile_node runs with user_id set and assessment_error=False,
    the profile row must have the merged topic_scores persisted."""

    def test_topic_scores_written_to_db(self) -> None:
        """update_profile is called with merged topic_scores on the happy path."""
        initial_profile = _fake_profile(
            topic_scores={"rag_fundamentals": 0.4},
            interaction_count=2,
        )

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            result = update_profile_node(_base_state(  # type: ignore[arg-type]
                topic_scores_delta={"vector_databases": 0.6},
            ))

        assert result == {}, "update_profile_node must return {}"
        mock_update.assert_called_once()

        call_kwargs = mock_update.call_args.kwargs
        assert "topic_scores" in call_kwargs, (
            f"update_profile must receive topic_scores kwarg, got {call_kwargs!r}"
        )

    def test_topic_scores_merged_not_overwritten(self) -> None:
        """Existing topic_scores are preserved; delta is merged in additively."""
        initial_profile = _fake_profile(
            topic_scores={"rag_fundamentals": 0.4},
            interaction_count=1,
        )

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            update_profile_node(_base_state(  # type: ignore[arg-type]
                topic_scores_delta={"vector_databases": 0.7},
            ))

        call_kwargs = mock_update.call_args.kwargs
        topic_scores = call_kwargs["topic_scores"]

        assert "rag_fundamentals" in topic_scores, (
            f"existing rag_fundamentals must survive the merge, got {topic_scores!r}"
        )
        assert "vector_databases" in topic_scores, (
            f"new vector_databases delta must be merged in, got {topic_scores!r}"
        )

    def test_delta_values_reflected_in_merged_scores(self) -> None:
        """The delta value for a slug must be present in the merged topic_scores."""
        initial_profile = _fake_profile(topic_scores={}, interaction_count=0)

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            update_profile_node(_base_state(  # type: ignore[arg-type]
                topic_scores_delta={"langchain": 0.8},
            ))

        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs["topic_scores"].get("langchain") == pytest.approx(0.8), (
            f"langchain=0.8 delta must appear in merged topic_scores, "
            f"got {call_kwargs['topic_scores']!r}"
        )

    def test_returns_empty_dict(self) -> None:
        """update_profile_node always returns {} — it does not modify AgentState."""
        initial_profile = _fake_profile()

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch("agents.nodes.update_profile.update_profile"),
        ):
            result = update_profile_node(_base_state())  # type: ignore[arg-type]

        assert result == {}, f"update_profile_node must return empty dict, got {result!r}"


# ---------------------------------------------------------------------------
# Gate 2 — interaction_count increments after each turn
# ---------------------------------------------------------------------------

class TestGate2InteractionCountIncrements:
    """interaction_count in the profile must be incremented by 1 on each successful turn."""

    def test_interaction_count_incremented_by_one(self) -> None:
        """update_profile is called with interaction_count = existing + 1."""
        initial_profile = _fake_profile(interaction_count=5)

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            update_profile_node(_base_state())  # type: ignore[arg-type]

        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs.get("interaction_count") == 6, (
            f"interaction_count must be 5+1=6, got {call_kwargs.get('interaction_count')!r}"
        )

    def test_interaction_count_incremented_from_zero(self) -> None:
        """First interaction: interaction_count starts at 0, must be set to 1."""
        initial_profile = _fake_profile(interaction_count=0)

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            update_profile_node(_base_state())  # type: ignore[arg-type]

        call_kwargs = mock_update.call_args.kwargs
        assert call_kwargs.get("interaction_count") == 1, (
            f"First turn: interaction_count must be 0+1=1, got {call_kwargs.get('interaction_count')!r}"
        )

    def test_interaction_count_not_incremented_on_error_path(self) -> None:
        """When assessment_error=True, update_profile must not be called at all."""
        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
            ) as mock_get,
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            update_profile_node(_base_state(assessment_error=True))  # type: ignore[arg-type]

        mock_get.assert_not_called()
        mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# Gate 3 — Fallback path (assessment_error=True) does not write to DB
# ---------------------------------------------------------------------------

class TestGate3FallbackPathSkipsDB:
    """When assessment_error=True, update_profile_node must not touch the DB."""

    def test_update_profile_not_called_on_error(self) -> None:
        """assessment_error=True: update_profile() must NOT be called."""
        with (
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            result = update_profile_node(_base_state(  # type: ignore[arg-type]
                user_id="user-abc",
                assessment_error=True,
            ))

        mock_update.assert_not_called()
        assert result == {}, "Fallback path must return {}"

    def test_get_profile_not_called_on_error(self) -> None:
        """assessment_error=True: get_profile_by_user_id() must NOT be called."""
        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
            ) as mock_get,
            patch("agents.nodes.update_profile.update_profile"),
        ):
            update_profile_node(_base_state(  # type: ignore[arg-type]
                user_id="user-abc",
                assessment_error=True,
            ))

        mock_get.assert_not_called()

    def test_returns_empty_dict_on_error_path(self) -> None:
        """assessment_error=True path must still return {}."""
        result = update_profile_node(_base_state(  # type: ignore[arg-type]
            user_id="user-abc",
            assessment_error=True,
        ))
        assert result == {}, f"Error-path return must be empty dict, got {result!r}"

    def test_no_db_write_with_empty_delta_and_error(self) -> None:
        """assessment_error=True with empty delta: no DB write, no exception."""
        with patch("agents.nodes.update_profile.update_profile") as mock_update:
            result = update_profile_node(_base_state(  # type: ignore[arg-type]
                assessment_error=True,
                topic_scores_delta={},
                identified_gaps=[],
            ))

        mock_update.assert_not_called()
        assert result == {}


# ---------------------------------------------------------------------------
# Gate 4 — user_id is None: skip profile update (anonymous user)
# ---------------------------------------------------------------------------

class TestGate4AnonymousUserSkipsUpdate:
    """When user_id is None, the node must return {} immediately without any DB access."""

    def test_update_profile_not_called_when_anonymous(self) -> None:
        """user_id=None: update_profile() must NOT be called."""
        with (
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            result = update_profile_node(_base_state(user_id=None))  # type: ignore[arg-type]

        mock_update.assert_not_called()
        assert result == {}, "Anonymous path must return {}"

    def test_get_profile_not_called_when_anonymous(self) -> None:
        """user_id=None: get_profile_by_user_id() must NOT be called."""
        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
            ) as mock_get,
        ):
            update_profile_node(_base_state(user_id=None))  # type: ignore[arg-type]

        mock_get.assert_not_called()

    def test_returns_empty_dict_for_anonymous(self) -> None:
        """user_id=None must return {} without raising."""
        result = update_profile_node(_base_state(user_id=None))  # type: ignore[arg-type]
        assert result == {}, f"Anonymous user path must return {{}}, got {result!r}"

    def test_anonymous_with_non_empty_delta_still_skips(self) -> None:
        """Even with a non-empty topic_scores_delta, user_id=None means no DB write."""
        with patch("agents.nodes.update_profile.update_profile") as mock_update:
            result = update_profile_node(_base_state(  # type: ignore[arg-type]
                user_id=None,
                topic_scores_delta={"vector_databases": 0.9},
            ))

        mock_update.assert_not_called()
        assert result == {}


# ---------------------------------------------------------------------------
# Gate 5 — last_activity_at is set to a valid ISO 8601 timestamp
# ---------------------------------------------------------------------------

class TestGate5LastActivityAt:
    """On every successful turn, last_activity_at must be set to a UTC ISO 8601 timestamp."""

    def test_last_activity_at_passed_to_update_profile(self) -> None:
        """update_profile must receive last_activity_at kwarg on the happy path."""
        initial_profile = _fake_profile()

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            update_profile_node(_base_state())  # type: ignore[arg-type]

        call_kwargs = mock_update.call_args.kwargs
        assert "last_activity_at" in call_kwargs, (
            f"update_profile must receive last_activity_at, got kwargs: {call_kwargs!r}"
        )

    def test_last_activity_at_is_string(self) -> None:
        """last_activity_at must be a string (ISO 8601 datetime)."""
        initial_profile = _fake_profile()

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            update_profile_node(_base_state())  # type: ignore[arg-type]

        call_kwargs = mock_update.call_args.kwargs
        laa = call_kwargs["last_activity_at"]
        assert isinstance(laa, str), (
            f"last_activity_at must be a str, got {type(laa)!r}: {laa!r}"
        )

    def test_last_activity_at_is_valid_iso8601(self) -> None:
        """last_activity_at must be parseable as a UTC ISO 8601 datetime."""
        initial_profile = _fake_profile()

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            before = datetime.now(timezone.utc)
            update_profile_node(_base_state())  # type: ignore[arg-type]
            after = datetime.now(timezone.utc)

        call_kwargs = mock_update.call_args.kwargs
        laa_str: str = call_kwargs["last_activity_at"]

        try:
            laa_dt = datetime.fromisoformat(laa_str)
        except ValueError as exc:
            pytest.fail(
                f"last_activity_at={laa_str!r} is not a valid ISO 8601 string: {exc}"
            )

        # Normalize to UTC for comparison
        if laa_dt.tzinfo is not None:
            laa_utc = laa_dt.astimezone(timezone.utc)
        else:
            laa_utc = laa_dt.replace(tzinfo=timezone.utc)

        assert before <= laa_utc <= after, (
            f"last_activity_at={laa_str!r} must be between {before.isoformat()!r} "
            f"and {after.isoformat()!r}"
        )

    def test_last_activity_at_not_set_on_anonymous(self) -> None:
        """When user_id=None, update_profile is never called — no last_activity_at set."""
        with patch("agents.nodes.update_profile.update_profile") as mock_update:
            update_profile_node(_base_state(user_id=None))  # type: ignore[arg-type]

        mock_update.assert_not_called()

    def test_last_activity_at_not_set_on_error_path(self) -> None:
        """When assessment_error=True, update_profile is never called — no last_activity_at set."""
        with patch("agents.nodes.update_profile.update_profile") as mock_update:
            update_profile_node(_base_state(assessment_error=True))  # type: ignore[arg-type]

        mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# Additional defensive tests — missing profile row
# ---------------------------------------------------------------------------

class TestMissingProfileRow:
    """When get_profile_by_user_id returns None (no profile exists), the node
    must log a warning and return {} without writing to the DB."""

    def test_no_db_write_when_profile_not_found(self) -> None:
        """Profile not found: update_profile must NOT be called."""
        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=None,
            ),
            patch(
                "agents.nodes.update_profile.update_profile",
            ) as mock_update,
        ):
            result = update_profile_node(_base_state())  # type: ignore[arg-type]

        mock_update.assert_not_called()
        assert result == {}

    def test_returns_empty_dict_when_profile_not_found(self) -> None:
        """Missing profile row must not raise — returns {} cleanly."""
        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=None,
            ),
            patch("agents.nodes.update_profile.update_profile"),
        ):
            result = update_profile_node(_base_state())  # type: ignore[arg-type]

        assert result == {}, f"Missing profile must return {{}}, got {result!r}"


# ---------------------------------------------------------------------------
# TestSessionQuestionCountWiring — Commit 41: session_question_count passed to scoring
# ---------------------------------------------------------------------------

class TestSessionQuestionCountWiring:
    """update_profile_node passes per-topic session count to compute_topic_scores."""

    def test_session_count_passed_for_single_topic_delta(self) -> None:
        """When topic_scores_delta has one key, its session count is passed to compute_topic_scores."""
        initial_profile = _fake_profile(topic_scores={}, interaction_count=0)

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch("agents.nodes.update_profile.update_profile"),
            patch(
                "agents.nodes.update_profile.compute_topic_scores",
                return_value={
                    "topic_scores": {"vector_databases": 0.6},
                    "session_history": {},
                    "strengths": [],
                    "gaps": [],
                    "mastery_level": "beginner",
                },
            ) as mock_compute,
        ):
            update_profile_node(_base_state(  # type: ignore[arg-type]
                topic_scores_delta={"vector_databases": 0.6},
                session_question_counts={"vector_databases": 3},
            ))

        call_kwargs = mock_compute.call_args.kwargs
        assert call_kwargs.get("session_question_count") == 3, (
            f"session_question_count must be 3, got {call_kwargs.get('session_question_count')!r}"
        )

    def test_session_count_none_for_multi_topic_delta(self) -> None:
        """When topic_scores_delta has multiple keys, session_question_count is None."""
        initial_profile = _fake_profile(topic_scores={}, interaction_count=0)

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch("agents.nodes.update_profile.update_profile"),
            patch(
                "agents.nodes.update_profile.compute_topic_scores",
                return_value={
                    "topic_scores": {},
                    "session_history": {},
                    "strengths": [],
                    "gaps": [],
                    "mastery_level": "novice",
                },
            ) as mock_compute,
        ):
            update_profile_node(_base_state(  # type: ignore[arg-type]
                topic_scores_delta={
                    "vector_databases": 0.6,
                    "retrieval_methods": 0.4,
                },
                session_question_counts={"vector_databases": 2, "retrieval_methods": 1},
            ))

        call_kwargs = mock_compute.call_args.kwargs
        assert call_kwargs.get("session_question_count") is None, (
            f"Multi-topic delta must pass session_question_count=None, "
            f"got {call_kwargs.get('session_question_count')!r}"
        )

    def test_score_not_updated_when_count_below_3(self) -> None:
        """topic_scores_delta with count=1 does not update the stored score (guard active)."""
        initial_profile = _fake_profile(
            topic_scores={"vector_databases": 0.5},
            interaction_count=2,
        )

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch("agents.nodes.update_profile.update_profile") as mock_update,
        ):
            update_profile_node(_base_state(  # type: ignore[arg-type]
                topic_scores_delta={"vector_databases": 1.0},
                session_question_counts={"vector_databases": 1},
            ))

        call_kwargs = mock_update.call_args.kwargs
        # Guard fires: stored score stays at 0.5, not updated to blend with 1.0
        assert call_kwargs["topic_scores"].get("vector_databases") == pytest.approx(0.5), (
            f"Score must stay unchanged when session_question_count=1 < 3, "
            f"got {call_kwargs['topic_scores'].get('vector_databases')!r}"
        )

    def test_score_updated_when_count_is_3(self) -> None:
        """topic_scores_delta with count=3 updates the stored score (guard cleared)."""
        initial_profile = _fake_profile(
            topic_scores={},
            interaction_count=5,
        )

        with (
            patch(
                "agents.nodes.update_profile.get_profile_by_user_id",
                return_value=initial_profile,
            ),
            patch("agents.nodes.update_profile.update_profile") as mock_update,
        ):
            update_profile_node(_base_state(  # type: ignore[arg-type]
                topic_scores_delta={"vector_databases": 1.0},
                session_question_counts={"vector_databases": 3},
            ))

        call_kwargs = mock_update.call_args.kwargs
        # Guard cleared: score is computed from 1.0 (no prior history → topic_score = 1.0)
        assert call_kwargs["topic_scores"].get("vector_databases") == pytest.approx(1.0), (
            f"Score must be updated when session_question_count=3, "
            f"got {call_kwargs['topic_scores'].get('vector_databases')!r}"
        )
