"""
Tests for Commit 45.3 (question-type-balance).

Gates:
1. novice always returns 'mcq' from select_question_type
2. intermediate, advanced, expert can return both 'mcq' and 'open'
3. Ratio distribution is approximately correct over many draws
4. select_test_question routes to open delivery for non-novice levels (via mock)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import HumanMessage

from agents.assessment.question_selection import select_question_type
from agents.assessment.test_delivery import select_test_question


def _base_state(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "messages": [HumanMessage(content="What is RAG?")],
        "question": "What is RAG?",
        "user_id": None,
        "user_level": "novice",
        "docs": [],
        "retrieval_source": "chroma",
        "answer": "",
        "topic_scores_delta": {},
        "identified_gaps": ["embeddings_and_similarity"],
        "assessment_error": False,
        "test_mode": False,
        "pending_test_question": None,
        "pending_test_slug": None,
        "is_mcq": False,
        "pending_mcq_correct_answer": None,
        "session_question_counts": {},
        "trace_id": "test-trace-45-3",
        "latency_ms": 0,
        "cache_hit": "miss",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Gate 1 — novice always MCQ (deterministic)
# ---------------------------------------------------------------------------

class TestDeterministicLevels:
    """novice never draws open questions."""

    def test_novice_always_mcq(self) -> None:
        results = {select_question_type("novice") for _ in range(50)}
        assert results == {"mcq"}

    def test_unknown_level_defaults_to_mcq(self) -> None:
        results = {select_question_type("unknown") for _ in range(20)}
        assert results == {"mcq"}


# ---------------------------------------------------------------------------
# Gate 2 — probabilistic levels return both types
# ---------------------------------------------------------------------------

class TestProbabilisticLevels:
    """intermediate/advanced/expert must produce both MCQ and open over enough draws."""

    def test_intermediate_produces_both_types(self) -> None:
        results = {select_question_type("intermediate") for _ in range(200)}
        assert "mcq" in results
        assert "open" in results

    def test_advanced_produces_both_types(self) -> None:
        results = {select_question_type("advanced") for _ in range(200)}
        assert "mcq" in results
        assert "open" in results

    def test_expert_produces_both_types(self) -> None:
        results = {select_question_type("expert") for _ in range(200)}
        assert "mcq" in results
        assert "open" in results


# ---------------------------------------------------------------------------
# Gate 3 — approximate ratio check (comment-level assertion)
# ---------------------------------------------------------------------------

class TestRatioApproximation:
    """
    Expected open-question rates: intermediate ~20%, advanced ~40%, expert ~70%.
    We use a ±15% tolerance over 1000 draws to avoid flaky CI failures.
    """

    def _open_rate(self, level: str, draws: int = 1000) -> float:
        return sum(1 for _ in range(draws) if select_question_type(level) == "open") / draws

    def test_intermediate_open_rate_near_20pct(self) -> None:
        rate = self._open_rate("intermediate")
        assert 0.05 <= rate <= 0.35, f"intermediate open rate {rate:.2%} outside 5–35%"

    def test_advanced_open_rate_near_40pct(self) -> None:
        rate = self._open_rate("advanced")
        assert 0.25 <= rate <= 0.55, f"advanced open rate {rate:.2%} outside 25–55%"

    def test_expert_open_rate_near_70pct(self) -> None:
        rate = self._open_rate("expert")
        assert 0.55 <= rate <= 0.85, f"expert open rate {rate:.2%} outside 55–85%"


# ---------------------------------------------------------------------------
# Gate 4 — select_test_question routes to open delivery
# ---------------------------------------------------------------------------

class TestSelectTestQuestionRouting:
    """select_test_question delegates to deliver_open_question when type is 'open'."""

    @pytest.mark.asyncio
    async def test_open_path_called_when_type_is_open(self) -> None:
        state = _base_state(user_level="expert")
        mock_result = {"is_mcq": False, "assessment_error": False, "messages": []}

        with (
            patch(
                "agents.assessment.test_delivery.run_passive_assessment",
                new=AsyncMock(return_value=({}, True, False)),
            ),
            patch(
                "agents.assessment.test_delivery.select_question_type",
                return_value="open",
            ),
            patch(
                "agents.assessment.test_delivery.deliver_open_question",
                new=AsyncMock(return_value=mock_result),
            ) as mock_open,
        ):
            result = await select_test_question(state)  # type: ignore[arg-type]
            mock_open.assert_awaited_once()
            assert result["is_mcq"] is False

    @pytest.mark.asyncio
    async def test_mcq_path_when_type_is_mcq(self) -> None:
        state = _base_state(user_level="novice")

        with (
            patch(
                "agents.assessment.test_delivery.run_passive_assessment",
                new=AsyncMock(return_value=({}, True, False)),
            ),
            patch(
                "agents.assessment.test_delivery.select_question_type",
                return_value="mcq",
            ),
            patch(
                "agents.assessment.test_delivery.select_mcq_question_for_level",
                return_value=("embeddings_and_similarity", 0),
            ),
            patch(
                "agents.assessment.test_delivery.load_mcq_question_for_difficulty",
                return_value=("MCQ question text", "B"),
            ),
        ):
            result = await select_test_question(state)  # type: ignore[arg-type]
            assert result["is_mcq"] is True

    @pytest.mark.asyncio
    async def test_non_rag_returns_early_before_type_selection(self) -> None:
        state = _base_state(user_level="expert")

        with (
            patch(
                "agents.assessment.test_delivery.run_passive_assessment",
                new=AsyncMock(return_value=({}, False, False)),
            ),
            patch(
                "agents.assessment.test_delivery.select_question_type",
            ) as mock_type,
        ):
            await select_test_question(state)  # type: ignore[arg-type]
            mock_type.assert_not_called()
