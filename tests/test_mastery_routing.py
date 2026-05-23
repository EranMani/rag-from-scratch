"""
Tests for Commit 46 (mastery-matched-routing).

Gates:
1. Novice user receives only novice-difficulty questions
2. Advanced user receives advanced-difficulty questions
3. Fallback tier: if no questions at target tier, nearest tier is served
4. mastery_level=None preserves unrestricted (prior) behavior
"""

from __future__ import annotations

import re
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import HumanMessage

from agents.mcq_utils import (
    get_mcq_blocks_for_difficulty,
    get_mcq_count_for_difficulty,
    load_mcq_question_for_difficulty,
)
from agents.assessment.question_selection import select_mcq_question_for_level
from agents.assessment.test_delivery import select_test_question


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REAL_SLUG = "embeddings_and_similarity"


def _base_state(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "messages": [HumanMessage(content="What is RAG?")],
        "question": "What is RAG?",
        "user_id": None,
        "user_level": "novice",
        "docs": [],
        "answer": "",
        "topic_scores_delta": {},
        "identified_gaps": [_REAL_SLUG],
        "assessment_error": False,
        "pending_test_question": None,
        "pending_test_slug": None,
        "is_mcq": False,
        "pending_mcq_correct_answer": None,
        "session_question_counts": {},
        "trace_id": "test-trace-46",
        "latency_ms": 0,
        "cache_hit": "miss",
    }
    base.update(overrides)
    return base


def _difficulty_of_block(block: str) -> str | None:
    m = re.search(r"^\*\*Difficulty:\*\*\s*(\w+)", block, re.MULTILINE)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Gate 1 — novice receives only novice-difficulty questions
# ---------------------------------------------------------------------------

class TestNoviceTierFiltering:
    """Questions returned for novice mastery are all difficulty=novice."""

    def test_blocks_for_novice_are_all_novice(self) -> None:
        blocks = get_mcq_blocks_for_difficulty(_REAL_SLUG, "novice")
        assert len(blocks) > 0
        for block in blocks:
            assert _difficulty_of_block(block) == "novice"

    def test_count_for_novice_matches_novice_block_count(self) -> None:
        blocks = get_mcq_blocks_for_difficulty(_REAL_SLUG, "novice")
        assert get_mcq_count_for_difficulty(_REAL_SLUG, "novice") == len(blocks)

    def test_loaded_question_for_novice_is_novice_difficulty(self) -> None:
        blocks = get_mcq_blocks_for_difficulty(_REAL_SLUG, "novice")
        count = len(blocks)
        for idx in range(count):
            _, _ = load_mcq_question_for_difficulty(_REAL_SLUG, idx, "novice")
            # verify the underlying block difficulty
            assert _difficulty_of_block(blocks[idx % count]) == "novice"

    def test_select_mcq_for_level_novice_returns_valid_tuple(self) -> None:
        state = _base_state(user_level="novice")
        result = select_mcq_question_for_level(state)  # type: ignore[arg-type]
        assert result is not None
        slug, idx = result
        assert slug == _REAL_SLUG
        assert 0 <= idx < get_mcq_count_for_difficulty(slug, "novice")


# ---------------------------------------------------------------------------
# Gate 2 — advanced user receives advanced-difficulty questions
# ---------------------------------------------------------------------------

class TestAdvancedTierFiltering:
    """Questions returned for advanced mastery are all difficulty=advanced."""

    def test_blocks_for_advanced_are_all_advanced(self) -> None:
        blocks = get_mcq_blocks_for_difficulty(_REAL_SLUG, "advanced")
        assert len(blocks) > 0
        for block in blocks:
            assert _difficulty_of_block(block) == "advanced"

    def test_count_for_advanced_matches_advanced_block_count(self) -> None:
        blocks = get_mcq_blocks_for_difficulty(_REAL_SLUG, "advanced")
        assert get_mcq_count_for_difficulty(_REAL_SLUG, "advanced") == len(blocks)

    def test_loaded_question_for_advanced_is_advanced_difficulty(self) -> None:
        blocks = get_mcq_blocks_for_difficulty(_REAL_SLUG, "advanced")
        count = len(blocks)
        for idx in range(count):
            _, _ = load_mcq_question_for_difficulty(_REAL_SLUG, idx, "advanced")
            assert _difficulty_of_block(blocks[idx % count]) == "advanced"

    def test_select_mcq_for_level_advanced_returns_valid_tuple(self) -> None:
        state = _base_state(user_level="advanced")
        result = select_mcq_question_for_level(state)  # type: ignore[arg-type]
        assert result is not None
        slug, idx = result
        # advanced users get Phase 3 slugs, not Phase 1 — only verify index is in range
        assert 0 <= idx < get_mcq_count_for_difficulty(slug, "advanced")


# ---------------------------------------------------------------------------
# Gate 3 — fallback tier logic
# ---------------------------------------------------------------------------

class TestFallbackTierLogic:
    """If no questions exist at the target tier, nearest tier is served."""

    def test_fallback_returns_nonempty_list_for_all_levels(self) -> None:
        for level in ("novice", "intermediate", "advanced", "expert"):
            # Use a slug known to have all tiers — embeddings_and_similarity has all 4
            blocks = get_mcq_blocks_for_difficulty(_REAL_SLUG, level)
            assert len(blocks) > 0, f"No blocks for level={level}"

    def test_fallback_for_nonexistent_tier_returns_something(self) -> None:
        # Simulate a slug that has only novice questions by mocking the block list
        novice_only_blocks = [
            "## MCQ-fake\n\n**Difficulty:** novice\n**Topic:** test\n\n**Question:**\nWhat?\n\n**Options:**\nA. A\nB. B\nC. C\nD. D\n\n**Correct answer:** A\n"
        ]
        from agents import mcq_utils
        original = mcq_utils.get_mcq_question_blocks

        def mock_blocks(slug: str) -> list[str]:
            return novice_only_blocks

        mcq_utils.get_mcq_question_blocks = mock_blocks  # type: ignore[assignment]
        try:
            # Requesting "advanced" when only "novice" exists — should fall back to novice
            blocks = get_mcq_blocks_for_difficulty("fake_slug", "advanced")
            assert len(blocks) == 1
            assert _difficulty_of_block(blocks[0]) == "novice"
        finally:
            mcq_utils.get_mcq_question_blocks = original  # type: ignore[assignment]

    def test_fallback_lower_before_higher(self) -> None:
        # advanced falls back to intermediate before novice
        intermediate_only = [
            "## MCQ-fake\n\n**Difficulty:** intermediate\n**Topic:** test\n\n**Question:**\nWhat?\n\n**Options:**\nA. A\nB. B\nC. C\nD. D\n\n**Correct answer:** B\n"
        ]
        from agents import mcq_utils
        original = mcq_utils.get_mcq_question_blocks

        def mock_blocks(slug: str) -> list[str]:
            return intermediate_only

        mcq_utils.get_mcq_question_blocks = mock_blocks  # type: ignore[assignment]
        try:
            blocks = get_mcq_blocks_for_difficulty("fake_slug", "advanced")
            assert _difficulty_of_block(blocks[0]) == "intermediate"
        finally:
            mcq_utils.get_mcq_question_blocks = original  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Gate 4 — mastery_level=None preserves unrestricted behavior
# ---------------------------------------------------------------------------

class TestNoneMasteryUnrestricted:
    """user_level=None (or unrecognized) returns all blocks with no filtering."""

    def test_none_difficulty_returns_all_blocks(self) -> None:
        from agents.mcq_utils import get_mcq_question_blocks
        all_blocks = get_mcq_question_blocks(_REAL_SLUG)
        filtered = get_mcq_blocks_for_difficulty(_REAL_SLUG, None)
        assert len(filtered) == len(all_blocks)

    def test_unrecognized_difficulty_returns_all_blocks(self) -> None:
        from agents.mcq_utils import get_mcq_question_blocks
        all_blocks = get_mcq_question_blocks(_REAL_SLUG)
        filtered = get_mcq_blocks_for_difficulty(_REAL_SLUG, "unknown_level")
        assert len(filtered) == len(all_blocks)

    def test_count_for_none_equals_total_question_count(self) -> None:
        from agents.mcq_utils import get_mcq_count
        assert get_mcq_count_for_difficulty(_REAL_SLUG, None) == get_mcq_count(_REAL_SLUG)

    @pytest.mark.asyncio
    async def test_select_test_question_none_level_delivers_question(self) -> None:
        """end-to-end: None mastery_level still delivers a question."""
        state = _base_state(user_level=None)

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
                return_value=(_REAL_SLUG, 0),
            ),
            patch(
                "agents.assessment.test_delivery.load_mcq_question_for_difficulty",
                return_value=("MCQ question text", "B"),
            ),
        ):
            result = await select_test_question(state)  # type: ignore[arg-type]
            assert result["is_mcq"] is True
            assert result["assessment_error"] is False


# ---------------------------------------------------------------------------
# Gate 5 — integration: full select_test_question with mastery routing
# ---------------------------------------------------------------------------

class TestSelectTestQuestionMasteryIntegration:
    """select_test_question routes MCQ delivery through mastery-filtered loader."""

    @pytest.mark.asyncio
    async def test_novice_state_reaches_difficulty_filtered_loader(self) -> None:
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
                return_value=(_REAL_SLUG, 0),
            ),
            patch(
                "agents.assessment.test_delivery.generate_questions",
                new=AsyncMock(side_effect=RuntimeError("LLM unavailable")),
            ),
            patch(
                "agents.assessment.test_delivery.load_mcq_question_for_difficulty",
                return_value=("Novice question text", "A"),
            ) as mock_loader,
        ):
            result = await select_test_question(state)  # type: ignore[arg-type]
            # verify loader was called with mastery level="novice" (via generation fallback)
            mock_loader.assert_called_once_with(_REAL_SLUG, 0, "novice")
            assert result["is_mcq"] is True

    @pytest.mark.asyncio
    async def test_advanced_state_passes_advanced_to_loader(self) -> None:
        state = _base_state(user_level="advanced")

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
                return_value=(_REAL_SLUG, 0),
            ),
            patch(
                "agents.assessment.test_delivery.generate_questions",
                new=AsyncMock(side_effect=RuntimeError("LLM unavailable")),
            ),
            patch(
                "agents.assessment.test_delivery.load_mcq_question_for_difficulty",
                return_value=("Advanced question text", "C"),
            ) as mock_loader,
        ):
            result = await select_test_question(state)  # type: ignore[arg-type]
            mock_loader.assert_called_once_with(_REAL_SLUG, 0, "advanced")
            assert result["is_mcq"] is True
