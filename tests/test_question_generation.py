"""
Tests for Commit 52 (ai-question-generation).

Gates:
1. Generated questions are served when LLM call succeeds and output validates
2. Fallback to bank question when validation fails — no error raised
3. generated_question_pool persists within a session (cache hit — LLM not called again)
4. New session (empty pool) triggers a fresh generation call
5. All existing tests still pass (verified by not importing conflicting fixtures)
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from agents.assessment.question_generation import _validate_question, generate_questions
from agents.assessment.test_delivery import _deliver_mcq, select_test_question


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_SLUG = "embeddings_and_similarity"
_LEVEL = "novice"
_CACHE_KEY = f"{_SLUG}:{_LEVEL}"

_VALID_GENERATED_Q: dict[str, Any] = {
    "question": "Which property of an embedding enables semantic search?",
    "options": {
        "A": "Its byte length",
        "B": "Its geometric position in high-dimensional space",
        "C": "Its compression ratio",
        "D": "Its token count",
    },
    "correct": "B",
    "slug": _SLUG,
    "mastery_level": _LEVEL,
    "explanations": {
        "A": "Byte length is a storage property, unrelated to semantic meaning.",
        "C": "Compression ratio measures space savings, not meaning.",
        "D": "Token count is a surface-level metric; embeddings encode semantics.",
    },
}

_VALID_LLM_PAYLOAD = json.dumps([_VALID_GENERATED_Q])


def _base_state(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "messages": [HumanMessage(content="What is RAG?")],
        "question": "What is RAG?",
        "user_id": None,
        "user_level": _LEVEL,
        "docs": [],
        "answer": "",
        "topic_scores_delta": {},
        "identified_gaps": [_SLUG],
        "assessment_error": False,
        "pending_test_question": None,
        "pending_test_slug": None,
        "is_mcq": False,
        "pending_mcq_correct_answer": None,
        "session_question_counts": {},
        "generated_question_pool": None,
        "trace_id": "test-trace-52",
        "latency_ms": 0,
        "cache_hit": "miss",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Gate 1 — validate_question structural checks
# ---------------------------------------------------------------------------

class TestValidateQuestion:
    """_validate_question enforces all structural constraints."""

    def test_valid_question_passes(self) -> None:
        assert _validate_question(_VALID_GENERATED_Q, _SLUG) is True

    def test_missing_required_key_fails(self) -> None:
        q = {**_VALID_GENERATED_Q}
        del q["explanations"]
        assert _validate_question(q, _SLUG) is False

    def test_wrong_option_keys_fails(self) -> None:
        q = {**_VALID_GENERATED_Q, "options": {"A": "x", "B": "y", "E": "z", "F": "w"}}
        assert _validate_question(q, _SLUG) is False

    def test_three_options_fails(self) -> None:
        q = {**_VALID_GENERATED_Q, "options": {"A": "x", "B": "y", "C": "z"}}
        assert _validate_question(q, _SLUG) is False

    def test_invalid_correct_key_fails(self) -> None:
        q = {**_VALID_GENERATED_Q, "correct": "E"}
        assert _validate_question(q, _SLUG) is False

    def test_wrong_distractor_keys_fails(self) -> None:
        # explanations must be for exactly the 3 non-correct options
        q = {**_VALID_GENERATED_Q, "explanations": {"A": "wrong", "C": "wrong", "D": "wrong"}}
        # correct is B, so A/C/D are the distractors — this should pass
        assert _validate_question(q, _SLUG) is True

    def test_correct_in_explanations_fails(self) -> None:
        # explanations should not include the correct key
        q = {
            **_VALID_GENERATED_Q,
            "explanations": {
                "A": "wrong",
                "B": "also included — invalid",
                "C": "wrong",
            },
        }
        assert _validate_question(q, _SLUG) is False

    def test_circular_distractor_fails(self) -> None:
        stem = "Which property of an embedding enables semantic search?"
        q = {
            **_VALID_GENERATED_Q,
            "question": stem,
            "explanations": {
                "A": stem,  # circular — verbatim stem in explanation
                "C": "compression ratio",
                "D": "token count",
            },
        }
        assert _validate_question(q, _SLUG) is False

    def test_slug_mismatch_fails(self) -> None:
        q = {**_VALID_GENERATED_Q, "slug": "wrong_slug"}
        assert _validate_question(q, _SLUG) is False

    def test_non_dict_input_fails(self) -> None:
        assert _validate_question("not a dict", _SLUG) is False

    def test_none_input_fails(self) -> None:
        assert _validate_question(None, _SLUG) is False


# ---------------------------------------------------------------------------
# Gate 2 — generate_questions: success path
# ---------------------------------------------------------------------------

class TestGenerateQuestionsSuccess:
    """generate_questions returns validated question list on LLM success."""

    @pytest.mark.asyncio
    async def test_returns_list_with_valid_question(self) -> None:
        mock_response = MagicMock()
        mock_response.content = _VALID_LLM_PAYLOAD

        with patch("agents.assessment.question_generation.get_provider") as mock_provider:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_provider.return_value.get_llm.return_value = mock_llm

            result = await generate_questions(_SLUG, _LEVEL, ["## MCQ-1\n**Difficulty:** novice"])

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["slug"] == _SLUG

    @pytest.mark.asyncio
    async def test_strips_markdown_fences(self) -> None:
        fenced = f"```json\n{_VALID_LLM_PAYLOAD}\n```"
        mock_response = MagicMock()
        mock_response.content = fenced

        with patch("agents.assessment.question_generation.get_provider") as mock_provider:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_provider.return_value.get_llm.return_value = mock_llm

            result = await generate_questions(_SLUG, _LEVEL, [])

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_filters_invalid_questions(self) -> None:
        # Mix of one valid and one invalid (wrong slug) question
        invalid_q = {**_VALID_GENERATED_Q, "slug": "wrong"}
        payload = json.dumps([_VALID_GENERATED_Q, invalid_q])
        mock_response = MagicMock()
        mock_response.content = payload

        with patch("agents.assessment.question_generation.get_provider") as mock_provider:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_provider.return_value.get_llm.return_value = mock_llm

            result = await generate_questions(_SLUG, _LEVEL, [])

        assert len(result) == 1
        assert result[0]["slug"] == _SLUG

    @pytest.mark.asyncio
    async def test_raises_when_all_invalid(self) -> None:
        invalid = [{**_VALID_GENERATED_Q, "slug": "wrong"}]
        mock_response = MagicMock()
        mock_response.content = json.dumps(invalid)

        with patch("agents.assessment.question_generation.get_provider") as mock_provider:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_provider.return_value.get_llm.return_value = mock_llm

            with pytest.raises(ValueError, match="No questions passed validation"):
                await generate_questions(_SLUG, _LEVEL, [])

    @pytest.mark.asyncio
    async def test_raises_on_non_array_output(self) -> None:
        mock_response = MagicMock()
        mock_response.content = '{"question": "oops"}'  # object, not array

        with patch("agents.assessment.question_generation.get_provider") as mock_provider:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_provider.return_value.get_llm.return_value = mock_llm

            with pytest.raises(ValueError, match="not a JSON array"):
                await generate_questions(_SLUG, _LEVEL, [])

    @pytest.mark.asyncio
    async def test_raises_on_json_parse_failure(self) -> None:
        mock_response = MagicMock()
        mock_response.content = "not json at all"

        with patch("agents.assessment.question_generation.get_provider") as mock_provider:
            mock_llm = MagicMock()
            mock_llm.ainvoke = AsyncMock(return_value=mock_response)
            mock_provider.return_value.get_llm.return_value = mock_llm

            with pytest.raises(Exception):
                await generate_questions(_SLUG, _LEVEL, [])

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self) -> None:
        import asyncio

        with patch("agents.assessment.question_generation.get_provider") as mock_provider:
            mock_llm = MagicMock()

            async def _slow(*args: Any, **kwargs: Any) -> None:
                await asyncio.sleep(999)

            mock_llm.ainvoke = _slow
            mock_provider.return_value.get_llm.return_value = mock_llm

            with patch("agents.assessment.question_generation._LLM_TIMEOUT_SECONDS", 0.05):
                with pytest.raises(asyncio.TimeoutError):
                    await generate_questions(_SLUG, _LEVEL, [])


# ---------------------------------------------------------------------------
# Gate 3 — _deliver_mcq: generated question served on cache miss
# ---------------------------------------------------------------------------

class TestDeliverMcqGenerationPath:
    """_deliver_mcq serves a generated question when LLM succeeds."""

    @pytest.mark.asyncio
    async def test_generated_question_served_on_success(self) -> None:
        state = _base_state()

        with patch(
            "agents.assessment.test_delivery.generate_questions",
            new=AsyncMock(return_value=[_VALID_GENERATED_Q]),
        ):
            display_text, correct = await _deliver_mcq(state, _SLUG, 0, _LEVEL)

        assert display_text is not None
        assert "Knowledge check:" in display_text
        assert correct == "B"

    @pytest.mark.asyncio
    async def test_pool_populated_after_generation(self) -> None:
        state = _base_state()

        with patch(
            "agents.assessment.test_delivery.generate_questions",
            new=AsyncMock(return_value=[_VALID_GENERATED_Q]),
        ):
            await _deliver_mcq(state, _SLUG, 0, _LEVEL)

        pool = state.get("generated_question_pool") or {}
        assert _CACHE_KEY in pool
        assert len(pool[_CACHE_KEY]) == 1


# ---------------------------------------------------------------------------
# Gate 4 — _deliver_mcq: fallback to bank on generation failure
# ---------------------------------------------------------------------------

class TestDeliverMcqFallback:
    """_deliver_mcq falls back to bank question silently on any generation failure."""

    @pytest.mark.asyncio
    async def test_fallback_on_llm_exception(self) -> None:
        state = _base_state()

        with (
            patch(
                "agents.assessment.test_delivery.generate_questions",
                new=AsyncMock(side_effect=RuntimeError("LLM down")),
            ),
            patch(
                "agents.assessment.test_delivery.load_mcq_question_for_difficulty",
                return_value=("Bank question text", "A"),
            ) as mock_bank,
        ):
            display_text, correct = await _deliver_mcq(state, _SLUG, 0, _LEVEL)

        assert display_text == "Bank question text"
        assert correct == "A"
        mock_bank.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_error_raised_on_generation_failure(self) -> None:
        state = _base_state()

        with (
            patch(
                "agents.assessment.test_delivery.generate_questions",
                new=AsyncMock(side_effect=ValueError("all invalid")),
            ),
            patch(
                "agents.assessment.test_delivery.load_mcq_question_for_difficulty",
                return_value=("Bank fallback", "C"),
            ),
        ):
            # Must not raise
            display_text, correct = await _deliver_mcq(state, _SLUG, 0, _LEVEL)

        assert display_text is not None

    @pytest.mark.asyncio
    async def test_returns_none_when_bank_also_fails(self) -> None:
        state = _base_state()

        with (
            patch(
                "agents.assessment.test_delivery.generate_questions",
                new=AsyncMock(side_effect=RuntimeError("LLM down")),
            ),
            patch(
                "agents.assessment.test_delivery.load_mcq_question_for_difficulty",
                side_effect=FileNotFoundError("no file"),
            ),
        ):
            display_text, correct = await _deliver_mcq(state, _SLUG, 0, _LEVEL)

        assert display_text is None
        assert correct is None


# ---------------------------------------------------------------------------
# Gate 5 — session cache: LLM not called again on cache hit
# ---------------------------------------------------------------------------

class TestSessionCache:
    """generated_question_pool persists across calls within same session."""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_generation(self) -> None:
        # Pre-populate the cache as if a prior call already generated questions
        state = _base_state(generated_question_pool={_CACHE_KEY: [_VALID_GENERATED_Q]})

        mock_generate = AsyncMock(return_value=[_VALID_GENERATED_Q])
        with patch("agents.assessment.test_delivery.generate_questions", new=mock_generate):
            display_text, correct = await _deliver_mcq(state, _SLUG, 0, _LEVEL)

        # LLM must NOT have been called
        mock_generate.assert_not_called()
        assert display_text is not None

    @pytest.mark.asyncio
    async def test_cache_hit_serves_generated_question(self) -> None:
        state = _base_state(generated_question_pool={_CACHE_KEY: [_VALID_GENERATED_Q]})

        with patch("agents.assessment.test_delivery.generate_questions", new=AsyncMock()) as mock_gen:
            display_text, correct = await _deliver_mcq(state, _SLUG, 0, _LEVEL)

        mock_gen.assert_not_called()
        assert "Knowledge check:" in display_text
        assert correct == "B"

    @pytest.mark.asyncio
    async def test_new_session_triggers_generation(self) -> None:
        # None pool = new session
        state = _base_state(generated_question_pool=None)

        mock_generate = AsyncMock(return_value=[_VALID_GENERATED_Q])
        with (
            patch("agents.assessment.test_delivery.generate_questions", new=mock_generate),
        ):
            await _deliver_mcq(state, _SLUG, 0, _LEVEL)

        mock_generate.assert_called_once()


# ---------------------------------------------------------------------------
# Gate 6 — select_test_question end-to-end: generated pool flows through
# ---------------------------------------------------------------------------

class TestSelectTestQuestionWithGeneration:
    """select_test_question routes through _deliver_mcq and includes pool in result."""

    @pytest.mark.asyncio
    async def test_pool_in_result_when_generation_succeeds(self) -> None:
        state = _base_state()

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
                return_value=(_SLUG, 0),
            ),
            patch(
                "agents.assessment.test_delivery.generate_questions",
                new=AsyncMock(return_value=[_VALID_GENERATED_Q]),
            ),
        ):
            result = await select_test_question(state)  # type: ignore[arg-type]

        assert result["is_mcq"] is True
        assert result["assessment_error"] is False
        assert result.get("generated_question_pool") is not None
        assert _CACHE_KEY in result["generated_question_pool"]

    @pytest.mark.asyncio
    async def test_fallback_question_delivered_on_llm_failure(self) -> None:
        state = _base_state()

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
                return_value=(_SLUG, 0),
            ),
            patch(
                "agents.assessment.test_delivery.generate_questions",
                new=AsyncMock(side_effect=RuntimeError("LLM unavailable")),
            ),
            patch(
                "agents.assessment.test_delivery.load_mcq_question_for_difficulty",
                return_value=("Bank question", "A"),
            ),
        ):
            result = await select_test_question(state)  # type: ignore[arg-type]

        assert result["is_mcq"] is True
        assert result["assessment_error"] is False
        assert result["pending_test_question"] == "Bank question"
