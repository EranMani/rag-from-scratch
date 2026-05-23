"""
Tests for Commit 45.4 (question-difficulty-degradation).

Gates:
1. _is_difficulty_signal returns True for expected phrases
2. _is_difficulty_signal returns False for normal answers (no false positives)
3. Difficulty signal with question_simplified=False → simplification path (step 2)
4. Difficulty signal with question_simplified=True → doc reveal path (step 3)
5. question_simplified resets to False in build_selection_result (new question delivery)
6. Simplification prompt contains "Do NOT reveal" hard constraint
7. Normal answer path is unchanged (no difficulty signal → existing MCQ/open routing)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agents.assessment.evaluation import _is_difficulty_signal
from agents.assessment.results import build_selection_result
from agents.prompts.assessment import simplification_prompt


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _pending_state(**overrides: Any) -> dict[str, Any]:
    """State with a pending open question and a HumanMessage last (eval mode)."""
    base: dict[str, Any] = {
        "messages": [
            AIMessage(content="Here is your question: What is a vector embedding?"),
            HumanMessage(content="I don't understand"),
        ],
        "question": "I don't understand",
        "user_id": None,
        "user_level": "novice",
        "docs": [],
        "answer": "",
        "topic_scores_delta": {},
        "identified_gaps": [],
        "assessment_error": False,
        "pending_test_question": "In your own words, explain what a vector embedding is.",
        "pending_test_slug": "embeddings_and_similarity",
        "is_mcq": False,
        "pending_mcq_correct_answer": None,
        "question_simplified": False,
        "session_question_counts": {},
        "is_passive_delta": False,
        "trace_id": "test-trace-45-4",
        "latency_ms": 0,
        "cache_hit": "miss",
        "gate_just_passed": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Gate 1 — _is_difficulty_signal detects expected phrases
# ---------------------------------------------------------------------------

class TestGate1DifficultySignalDetection:

    @pytest.mark.parametrize("phrase", [
        "too hard",
        "I don't understand",
        "i don't understand",
        "I do not understand",
        "help",
        "can you simplify",
        "simplify",
        "hint",
        "I don't know",
        "I do not know",
        "not sure",
        "no idea",
        "give up",
    ])
    def test_difficulty_phrase_detected(self, phrase: str) -> None:
        assert _is_difficulty_signal(phrase), f"Expected difficulty signal for: {phrase!r}"

    def test_signal_case_insensitive(self) -> None:
        assert _is_difficulty_signal("TOO HARD")
        assert _is_difficulty_signal("Help Me")


# ---------------------------------------------------------------------------
# Gate 2 — _is_difficulty_signal returns False for normal answers
# ---------------------------------------------------------------------------

class TestGate2NoDifficultySignalFalsePositives:

    @pytest.mark.parametrize("answer", [
        "A",
        "B",
        "C",
        "D",
        "A vector embedding is a fixed-length numerical vector.",
        "RAG stands for Retrieval-Augmented Generation.",
        "Chunking splits documents into smaller pieces.",
        "correct",
        "yes",
        "no",
    ])
    def test_normal_answer_not_flagged(self, answer: str) -> None:
        assert not _is_difficulty_signal(answer), (
            f"Normal answer should NOT trigger difficulty signal: {answer!r}"
        )


# ---------------------------------------------------------------------------
# Gate 3 — Step 2: simplification fires when question_simplified=False
# ---------------------------------------------------------------------------

class TestGate3SimplificationPath:

    @pytest.mark.asyncio
    async def test_step2_returns_simplified_question(self) -> None:
        """Difficulty signal + question_simplified=False → returns rephrased question."""
        from agents.assessment.node import assess_node

        state = _pending_state(question_simplified=False)

        with patch(
            "agents.assessment.evaluation._simplify_question",
            new=AsyncMock(return_value="What does a number list represent for text?"),
        ):
            result = await assess_node(state)  # type: ignore[arg-type]

        assert result.get("pending_test_question") == "What does a number list represent for text?"
        assert result.get("question_simplified") is True

    @pytest.mark.asyncio
    async def test_step2_fires_only_once(self) -> None:
        """Difficulty signal + question_simplified=True → does NOT call simplify again."""
        from agents.assessment.node import assess_node

        state = _pending_state(question_simplified=True)

        simplify_mock = AsyncMock(return_value="should not be called")
        with patch("agents.assessment.evaluation._simplify_question", new=simplify_mock):
            result = await assess_node(state)  # type: ignore[arg-type]

        simplify_mock.assert_not_called()
        assert result.get("pending_test_question") is None, (
            "Step 3 must clear pending_test_question so generate_node uses RAG path"
        )

    @pytest.mark.asyncio
    async def test_step2_includes_guidance_message(self) -> None:
        """Step 2 response includes an AIMessage with the rephrased question."""
        from agents.assessment.node import assess_node

        state = _pending_state(question_simplified=False)

        with patch(
            "agents.assessment.evaluation._simplify_question",
            new=AsyncMock(return_value="Simpler version of the question"),
        ):
            result = await assess_node(state)  # type: ignore[arg-type]

        messages = result.get("messages") or []
        assert messages, "Step 2 must add a guidance message"
        assert isinstance(messages[0], AIMessage)

    @pytest.mark.asyncio
    async def test_step2_clears_is_mcq_flag(self) -> None:
        """Step 2 must set is_mcq=False; LangGraph partial merge keeps prior is_mcq=True otherwise."""
        from agents.assessment.node import assess_node

        state = _pending_state(
            question_simplified=False,
            is_mcq=True,
            pending_mcq_correct_answer="B",
        )

        with patch(
            "agents.assessment.evaluation._simplify_question",
            new=AsyncMock(return_value="What does a number list represent for text?"),
        ):
            result = await assess_node(state)  # type: ignore[arg-type]

        assert result.get("is_mcq") is False, (
            "Step 2 must set is_mcq=False so the user's next answer routes to the "
            "LLM evaluator, not the MCQ evaluator"
        )


# ---------------------------------------------------------------------------
# Gate 4 — Step 3: second difficulty signal → doc reveal (RAG) path
# ---------------------------------------------------------------------------

class TestGate4DocRevealPath:

    @pytest.mark.asyncio
    async def test_step3_clears_pending_question(self) -> None:
        """Second difficulty signal (already_simplified=True) clears pending_test_question."""
        from agents.assessment.node import assess_node

        state = _pending_state(question_simplified=True)

        result = await assess_node(state)  # type: ignore[arg-type]

        assert result.get("pending_test_question") is None
        assert result.get("pending_test_slug") is None

    @pytest.mark.asyncio
    async def test_step3_marks_slug_as_gap(self) -> None:
        """Step 3 adds the slug to identified_gaps so it's recorded as a knowledge gap."""
        from agents.assessment.node import assess_node

        state = _pending_state(question_simplified=True, identified_gaps=[])

        result = await assess_node(state)  # type: ignore[arg-type]

        assert "embeddings_and_similarity" in result.get("identified_gaps", []), (
            "Step 3 must add the pending slug to identified_gaps"
        )

    @pytest.mark.asyncio
    async def test_step3_no_assessment_error(self) -> None:
        """Step 3 is a known outcome, not an error — assessment_error must be False."""
        from agents.assessment.node import assess_node

        state = _pending_state(question_simplified=True)

        result = await assess_node(state)  # type: ignore[arg-type]

        assert result.get("assessment_error") is False


# ---------------------------------------------------------------------------
# Gate 5 — question_simplified resets on new question delivery
# ---------------------------------------------------------------------------

class TestGate5ResetOnNewQuestion:

    def test_build_selection_result_resets_question_simplified(self) -> None:
        """build_selection_result always sets question_simplified=False."""
        result = build_selection_result(
            topic_scores_delta={},
            identified_gaps=[],
            assessment_error=False,
            pending_test_question="Some question",
            pending_test_slug="embeddings_and_similarity",
        )
        assert result["question_simplified"] is False

    def test_build_selection_result_resets_even_when_True_was_set(self) -> None:
        """question_simplified is always False in build_selection_result — no carry-over."""
        result = build_selection_result(
            topic_scores_delta={"embeddings_and_similarity": 0.5},
            identified_gaps=["embeddings_and_similarity"],
            assessment_error=False,
        )
        assert result["question_simplified"] is False


# ---------------------------------------------------------------------------
# Gate 6 — Simplification prompt contains hard no-reveal constraint
# ---------------------------------------------------------------------------

class TestGate6SimplificationPromptConstraint:

    def test_prompt_contains_do_not_reveal(self) -> None:
        """Simplification prompt must explicitly forbid revealing the answer."""
        messages = simplification_prompt.messages
        full_text = " ".join(
            getattr(m, "prompt", None) and m.prompt.template or str(m)
            for m in messages
        )
        assert "Do NOT reveal" in full_text or "do not reveal" in full_text.lower(), (
            "Simplification prompt must contain 'Do NOT reveal' constraint"
        )

    def test_prompt_takes_question_and_user_level(self) -> None:
        """Simplification prompt accepts {question} and {user_level} placeholders."""
        input_vars = simplification_prompt.input_variables
        assert "question" in input_vars
        assert "user_level" in input_vars
