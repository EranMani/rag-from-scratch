"""
Tests for Commit 45.2 (open-question-delivery).

Gates:
1. select_open_question returns (slug, index) for a valid state
2. load_open_question loads display text from the correct file
3. deliver_open_question sets is_mcq=False in its return value
4. Existing MCQ tests remain unaffected (covered by test_assess_node.py)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage

from agents.assessment.question_selection import select_open_question
from agents.assessment.test_delivery import deliver_open_question
from agents.mcq_utils import load_open_question
from agents.state import VALID_MODULE_SLUGS


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
        "trace_id": "test-trace-45-2",
        "latency_ms": 0,
        "cache_hit": "miss",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Gate 1 — select_open_question
# ---------------------------------------------------------------------------

class TestSelectOpenQuestion:
    """select_open_question returns (slug, index) for valid state."""

    def test_returns_tuple_for_valid_state(self) -> None:
        state = _base_state()
        result = select_open_question(state)  # type: ignore[arg-type]
        assert result is not None
        slug, idx = result
        assert isinstance(slug, str)
        assert isinstance(idx, int)

    def test_slug_is_in_valid_module_slugs(self) -> None:
        state = _base_state()
        result = select_open_question(state)  # type: ignore[arg-type]
        assert result is not None
        slug, _ = result
        assert slug in VALID_MODULE_SLUGS

    def test_gap_slug_returned_first(self) -> None:
        state = _base_state(identified_gaps=["rag_pipeline_architecture"])
        result = select_open_question(state)  # type: ignore[arg-type]
        assert result is not None
        slug, _ = result
        assert slug == "rag_pipeline_architecture"

    def test_returns_none_when_valid_slugs_empty(self) -> None:
        state = _base_state()
        with patch("agents.assessment.question_selection.VALID_MODULE_SLUGS", new=frozenset()):
            result = select_open_question(state)  # type: ignore[arg-type]
        assert result is None

    def test_index_is_message_count_modulo_question_count(self) -> None:
        """Index wraps via modulo — never out of range."""
        messages = [HumanMessage(content=f"m{i}") for i in range(3)]
        state = _base_state(messages=messages, identified_gaps=["embeddings_and_similarity"])
        result = select_open_question(state)  # type: ignore[arg-type]
        assert result is not None
        _, idx = result
        assert 0 <= idx < 100  # modulo keeps it in range


# ---------------------------------------------------------------------------
# Gate 2 — load_open_question
# ---------------------------------------------------------------------------

class TestLoadOpenQuestion:
    """load_open_question reads display text from the curriculum open-question files."""

    def test_returns_string_for_valid_slug(self) -> None:
        text = load_open_question("embeddings_and_similarity", 0)
        assert isinstance(text, str)

    def test_display_text_starts_with_knowledge_check(self) -> None:
        text = load_open_question("embeddings_and_similarity", 0)
        assert text.startswith("Knowledge check:")

    def test_display_text_is_non_empty(self) -> None:
        text = load_open_question("embeddings_and_similarity", 0)
        assert len(text) > len("Knowledge check:")

    def test_unknown_slug_raises_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_open_question("nonexistent_slug", 0)

    def test_modulo_wrapping_stays_in_range(self) -> None:
        """High index wraps via modulo — must not raise IndexError."""
        text = load_open_question("embeddings_and_similarity", 999)
        assert text.startswith("Knowledge check:")

    def test_different_index_returns_different_question(self) -> None:
        """Questions at index 0 and index 1 should differ for a multi-question file."""
        text_0 = load_open_question("embeddings_and_similarity", 0)
        text_1 = load_open_question("embeddings_and_similarity", 1)
        assert text_0 != text_1, "Index 0 and 1 must yield different questions"


# ---------------------------------------------------------------------------
# Gate 3 — deliver_open_question
# ---------------------------------------------------------------------------

class TestDeliverOpenQuestion:
    """deliver_open_question sets is_mcq=False and returns a valid state update."""

    @pytest.mark.asyncio
    async def test_is_mcq_false(self) -> None:
        state = _base_state()
        result = await deliver_open_question(state, {}, [], False)  # type: ignore[arg-type]
        assert result["is_mcq"] is False

    @pytest.mark.asyncio
    async def test_pending_test_question_set(self) -> None:
        state = _base_state()
        result = await deliver_open_question(state, {}, [], False)  # type: ignore[arg-type]
        assert result.get("pending_test_question") is not None
        assert result["pending_test_question"].startswith("Knowledge check:")

    @pytest.mark.asyncio
    async def test_pending_test_slug_is_valid(self) -> None:
        state = _base_state()
        result = await deliver_open_question(state, {}, [], False)  # type: ignore[arg-type]
        assert result["pending_test_slug"] in VALID_MODULE_SLUGS

    @pytest.mark.asyncio
    async def test_no_pending_mcq_correct_answer(self) -> None:
        """Open questions must not set pending_mcq_correct_answer."""
        state = _base_state()
        result = await deliver_open_question(state, {}, [], False)  # type: ignore[arg-type]
        assert result.get("pending_mcq_correct_answer") is None

    @pytest.mark.asyncio
    async def test_messages_list_contains_question(self) -> None:
        state = _base_state()
        result = await deliver_open_question(state, {}, [], False)  # type: ignore[arg-type]
        messages = result.get("messages", [])
        assert len(messages) >= 1
        assert "Knowledge check:" in messages[-1].content

    @pytest.mark.asyncio
    async def test_redirect_prepends_redirect_message(self) -> None:
        from agents.assessment.test_delivery import _REDIRECT_MESSAGE
        state = _base_state()
        result = await deliver_open_question(state, {}, [], True)  # type: ignore[arg-type]
        messages = result.get("messages", [])
        assert len(messages) == 2
        assert messages[0].content == _REDIRECT_MESSAGE

    @pytest.mark.asyncio
    async def test_no_redirect_yields_single_message(self) -> None:
        state = _base_state()
        result = await deliver_open_question(state, {}, [], False)  # type: ignore[arg-type]
        messages = result.get("messages", [])
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_no_valid_slug_sets_assessment_error(self) -> None:
        state = _base_state()
        with patch("agents.assessment.question_selection.VALID_MODULE_SLUGS", new=frozenset()):
            result = await deliver_open_question(state, {}, [], False)  # type: ignore[arg-type]
        assert result["assessment_error"] is True

    @pytest.mark.asyncio
    async def test_file_not_found_sets_assessment_error(self) -> None:
        state = _base_state()
        with patch("agents.assessment.test_delivery.load_open_question", side_effect=FileNotFoundError("no file")):
            result = await deliver_open_question(state, {}, [], False)  # type: ignore[arg-type]
        assert result["assessment_error"] is True

    @pytest.mark.asyncio
    async def test_passive_delta_passed_through(self) -> None:
        state = _base_state()
        delta = {"embeddings_and_similarity": 0.3}
        result = await deliver_open_question(state, delta, [], False)  # type: ignore[arg-type]
        assert result["topic_scores_delta"] == delta

    @pytest.mark.asyncio
    async def test_gaps_passed_through(self) -> None:
        state = _base_state()
        gaps = ["rag_pipeline_architecture"]
        result = await deliver_open_question(state, {}, gaps, False)  # type: ignore[arg-type]
        assert result["identified_gaps"] == gaps
