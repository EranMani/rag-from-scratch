"""
Tests for Commit 24 (assessment-engine-rewrite).

Coverage targets (spec gates):

Gate 1 — Test mode turn: node returns curriculum question in pending_test_question
         with correct pending_test_slug; no LLM call made.
Gate 2 — Evaluation mode turn: node evaluates answer and updates topic_scores_delta.
Gate 3 — Score delta is derived from verdict, not question content.
Gate 4 — assessment_error fallback path still works; graph never crashes on LLM failure.
Gate 5 — AgentState schema: all 4 new fields present with correct types.

Additional coverage:
Gate 6 — pending_test_slug validated against VALID_MODULE_SLUGS; invalid slug sets
          assessment_error=True without crashing.
Gate 7 — Output key boundary: assess_node writes only its declared keys.
Gate 8 — Graph compiles and ainvoke() does not raise (topology smoke test).

Design notes:
- Test mode tests do NOT mock get_provider() — the mode is fully deterministic.
  They DO mock pathlib.Path.read_text to avoid filesystem dependency.
- Evaluation mode tests mock get_provider() and assessment_prompt exactly as before.
- _route_after_assess is still tested as a pure function.
- asyncio_mode = "auto" in pyproject.toml makes @pytest.mark.asyncio optional.
"""

from __future__ import annotations

import pathlib
import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agents.nodes.assess import (
    _CURRICULUM_DIR,
    _evaluate_mcq_answer,
    _load_mcq_question,
    _select_question_index,
    assess_node,
)
from agents.assessment.question_selection import select_mcq_question
from agents.state import VALID_MODULE_SLUGS, AgentState, EvaluationOutput


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _base_state(**overrides: Any) -> dict[str, Any]:
    """Minimal AgentState dict for assess_node unit tests."""
    base: dict[str, Any] = {
        "messages": [HumanMessage(content="What is RAG?")],
        "question": "What is RAG?",
        "user_id": None,
        "user_level": "novice",
        "docs": [Document(page_content="RAG = Retrieval-Augmented Generation.", metadata={})],
        "retrieval_source": "chroma",
        "answer": "RAG stands for Retrieval-Augmented Generation.",
        "topic_scores_delta": {},
        "identified_gaps": ["embeddings_and_similarity"],
        "assessment_error": False,
        "test_mode": False,
        "pending_test_question": None,
        "pending_test_slug": None,
        "is_mcq": False,
        "pending_mcq_correct_answer": None,
        "session_question_counts": {},
        "trace_id": "test-trace-24",
        "latency_ms": 0,
        "cache_hit": "miss",
    }
    base.update(overrides)
    return base


def _eval_mode_state(**overrides: Any) -> dict[str, Any]:
    """State that triggers evaluation mode: pending question + HumanMessage last."""
    base = _base_state(
        messages=[
            AIMessage(content="Here is your test question: What is a vector embedding?"),
            HumanMessage(content="A vector embedding is a list of numbers representing text."),
        ],
        question="A vector embedding is a list of numbers representing text.",
        pending_test_question="In your own words, explain what a vector embedding is.",
        pending_test_slug="embeddings_and_similarity",
        test_mode=True,
    )
    base.update(overrides)
    return base


def _mcq_eval_state(**overrides: Any) -> dict[str, Any]:
    """State that triggers MCQ evaluation mode."""
    base = _base_state(
        messages=[
            AIMessage(content="Knowledge check: Why must documents be split?\n\nA. Cost\nB. Token limit\nC. Quality\nD. LLM"),
            HumanMessage(content="B"),
        ],
        question="B",
        pending_test_question="Knowledge check: Why must documents be split?\n\nA. Cost\nB. Token limit\nC. Quality\nD. LLM",
        pending_test_slug="chunking_strategies",
        test_mode=True,
        is_mcq=True,
        pending_mcq_correct_answer="B",
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Curriculum path on disk (regression: wrong parents[N] skips profile updates)
# ---------------------------------------------------------------------------


class TestCurriculumDirLayout:
    def test_curriculum_question_dir_exists_in_repo(self) -> None:
        assert _CURRICULUM_DIR.is_dir()
        assert (_CURRICULUM_DIR / "embeddings_and_similarity.md").is_file()

    @pytest.mark.asyncio
    async def test_test_mode_loads_real_curriculum_without_assessment_error(self) -> None:
        with patch(
            "agents.nodes.assess._run_passive_assessment",
            new=AsyncMock(return_value=({}, True)),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["assessment_error"] is False
        assert result["test_mode"] is True
        assert result["pending_test_question"]


def _make_full_initial_state(question: str = "What is RAG?") -> dict[str, Any]:
    """Full AgentState dict for end-to-end graph invocation tests."""
    return {
        "messages": [HumanMessage(content=question)],
        "question": question,
        "user_id": None,
        "user_level": "novice",
        "docs": [],
        "retrieval_source": "",
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
        "trace_id": "test-trace-24-e2e",
        "latency_ms": 0,
        "cache_hit": "miss",
    }


def _stub_retrieve(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "docs": [Document(page_content="RAG = Retrieval-Augmented Generation.", metadata={})],
        "retrieval_source": "chroma",
    }


async def _stub_generate(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": [AIMessage(content="Stubbed answer.")],
        "answer": "Stubbed answer.",
    }


# Sample curriculum file content matching the real format.
_SAMPLE_CURRICULUM_MD = """\
# Question Bank: `embeddings_and_similarity`

## Q1 — What is a vector embedding?

**Difficulty:** beginner

**Question:**
In your own words, explain what a vector embedding is. What does it represent, and why
is it useful for comparing text?

**Correct answer criteria:**
- States that an embedding is a fixed-length numerical vector

**Partial credit criteria:**
- Correctly describes embeddings as numerical vectors but misses similarity

**Incorrect / no-credit criteria:**
- Describes embeddings as a list of keywords
"""


def _make_eval_output(verdict: str = "partial") -> EvaluationOutput:
    """Build a valid EvaluationOutput for mocking."""
    return EvaluationOutput(
        verdict=verdict,  # type: ignore[arg-type]
        confidence=0.85,
        identified_gaps=["embeddings_and_similarity"],
        user_level="beginner",
    )


def _make_provider_mock() -> MagicMock:
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=MagicMock())
    mock_provider = MagicMock()
    mock_provider.get_llm = MagicMock(return_value=mock_llm)
    return mock_provider


def _make_prompt_mock(eval_output: EvaluationOutput) -> tuple[MagicMock, MagicMock]:
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=eval_output)
    mock_prompt = MagicMock()
    mock_prompt.__or__ = MagicMock(return_value=mock_chain)
    return mock_prompt, mock_chain


# ---------------------------------------------------------------------------
# Gate 1 — Test mode: returns pending_test_question with correct pending_test_slug
# ---------------------------------------------------------------------------

class TestGate1TestMode:
    """assess_node in test mode returns a curriculum question with a valid slug."""

    @pytest.mark.asyncio
    async def test_test_mode_returns_pending_test_question(self) -> None:
        """Test mode sets pending_test_question to a non-empty string."""
        with (
            patch(
                "agents.nodes.assess._run_passive_assessment",
                new=AsyncMock(return_value=({}, True)),
            ),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
            patch(
                "agents.nodes.assess._load_mcq_question",
                return_value=("Knowledge check: stub question\n\nA. a\nB. b\nC. c\nD. d", "B"),
            ),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["pending_test_question"], (
            "Test mode must set pending_test_question to a non-empty string"
        )

    @pytest.mark.asyncio
    async def test_test_mode_sets_test_mode_true(self) -> None:
        """Test mode sets test_mode=True."""
        with (
            patch(
                "agents.nodes.assess._run_passive_assessment",
                new=AsyncMock(return_value=({}, True)),
            ),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
            patch(
                "agents.nodes.assess._load_mcq_question",
                return_value=("Knowledge check: stub question\n\nA. a\nB. b\nC. c\nD. d", "B"),
            ),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["test_mode"] is True, (
            f"Test mode must set test_mode=True, got {result['test_mode']!r}"
        )

    @pytest.mark.asyncio
    async def test_test_mode_pending_slug_is_valid(self) -> None:
        """Test mode sets pending_test_slug to a value in VALID_MODULE_SLUGS."""
        with (
            patch(
                "agents.nodes.assess._run_passive_assessment",
                new=AsyncMock(return_value=({}, True)),
            ),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
            patch(
                "agents.nodes.assess._load_mcq_question",
                return_value=("Knowledge check: stub question\n\nA. a\nB. b\nC. c\nD. d", "B"),
            ),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["pending_test_slug"] in VALID_MODULE_SLUGS, (
            f"pending_test_slug {result['pending_test_slug']!r} not in VALID_MODULE_SLUGS"
        )

    @pytest.mark.asyncio
    async def test_test_mode_uses_identified_gap_slug(self) -> None:
        """Test mode prefers a gap slug when it is within the user's eligible phase."""
        # novice → Phase 1 eligible; rag_pipeline_architecture is a Phase 1 gap
        state = _base_state(user_level="novice", identified_gaps=["rag_pipeline_architecture"])
        with (
            patch(
                "agents.nodes.assess._run_passive_assessment",
                new=AsyncMock(return_value=({}, True)),
            ),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
            patch(
                "agents.nodes.assess._load_mcq_question",
                return_value=("Knowledge check: stub question\n\nA. a\nB. b\nC. c\nD. d", "B"),
            ),
        ):
            result = await assess_node(state)  # type: ignore[arg-type]
        assert result["pending_test_slug"] == "rag_pipeline_architecture", (
            f"Expected pending_test_slug='rag_pipeline_architecture', got {result['pending_test_slug']!r}"
        )

    @pytest.mark.asyncio
    async def test_test_mode_on_topic_sets_pending_test_question(self) -> None:
        """On-topic query in test mode still sets pending_test_question (get_provider is called)."""
        from agents.state import PassiveAssessmentOutput
        passive_out = PassiveAssessmentOutput(
            relevant_slug="embeddings_and_similarity",
            inferred_level="beginner",
            confidence=0.8,
        )
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(return_value=passive_out)
        mock_llm = MagicMock()
        mock_llm.with_structured_output = MagicMock(return_value=mock_chain)
        mock_provider = MagicMock()
        mock_provider.get_llm = MagicMock(return_value=mock_llm)
        with (
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch(
                "agents.nodes.assess._load_mcq_question",
                return_value=("Knowledge check: stub question\n\nA. a\nB. b\nC. c\nD. d", "B"),
            ),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["pending_test_question"], (
            "On-topic query must still set pending_test_question"
        )



# ---------------------------------------------------------------------------
# Gate 2 — Evaluation mode: clears test state and invokes LLM path
# ---------------------------------------------------------------------------

class TestGate2EvaluationMode:
    """assess_node in evaluation mode clears test state and invokes the LLM path."""

    @pytest.mark.asyncio
    async def test_eval_mode_clears_test_mode_flag(self) -> None:
        """Evaluation mode sets test_mode=False and clears pending fields."""
        eval_out = _make_eval_output("partial")
        mock_provider = _make_provider_mock()
        mock_prompt, _ = _make_prompt_mock(eval_out)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            result = await assess_node(_eval_mode_state())  # type: ignore[arg-type]
        assert result["test_mode"] is False
        assert result["pending_test_question"] is None
        assert result["pending_test_slug"] is None

    @pytest.mark.asyncio
    async def test_eval_mode_calls_get_provider(self) -> None:
        """Evaluation mode calls get_provider() exactly once."""
        eval_out = _make_eval_output("partial")
        mock_provider = _make_provider_mock()
        mock_prompt, _ = _make_prompt_mock(eval_out)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider) as mock_gp,
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            await assess_node(_eval_mode_state())  # type: ignore[arg-type]
        mock_gp.assert_called_once()


# ---------------------------------------------------------------------------
# Gate 3 — Score delta derived from verdict, not question content
# ---------------------------------------------------------------------------

class TestGate3ScoreDeltaFromScore:
    """topic_scores_delta is derived from verdict and pending_test_slug."""

    @pytest.mark.asyncio
    async def test_correct_verdict_produces_delta_1_0(self) -> None:
        """correct verdict → topic_scores_delta[slug]=1.0."""
        eval_out = _make_eval_output("correct")
        mock_provider = _make_provider_mock()
        mock_prompt, _ = _make_prompt_mock(eval_out)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            result = await assess_node(_eval_mode_state())  # type: ignore[arg-type]
        assert result["topic_scores_delta"] == {"embeddings_and_similarity": 1.0}, (
            f"Expected delta {{embeddings_and_similarity: 1.0}}, got {result['topic_scores_delta']!r}"
        )

    @pytest.mark.asyncio
    async def test_partial_verdict_produces_delta_0_5(self) -> None:
        """partial verdict → topic_scores_delta[slug]=0.5."""
        eval_out = _make_eval_output("partial")
        mock_provider = _make_provider_mock()
        mock_prompt, _ = _make_prompt_mock(eval_out)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            result = await assess_node(_eval_mode_state())  # type: ignore[arg-type]
        assert result["topic_scores_delta"] == {"embeddings_and_similarity": 0.5}, (
            f"Expected delta {{embeddings_and_similarity: 0.5}}, got {result['topic_scores_delta']!r}"
        )

    @pytest.mark.asyncio
    async def test_incorrect_verdict_produces_empty_delta(self) -> None:
        """incorrect verdict → topic_scores_delta is empty (no positive score to record)."""
        eval_out = _make_eval_output("incorrect")
        mock_provider = _make_provider_mock()
        mock_prompt, _ = _make_prompt_mock(eval_out)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            result = await assess_node(_eval_mode_state())  # type: ignore[arg-type]
        assert result["topic_scores_delta"] == {}, (
            f"incorrect verdict must produce empty delta, got {result['topic_scores_delta']!r}"
        )

    @pytest.mark.asyncio
    async def test_delta_key_matches_pending_slug(self) -> None:
        """Delta key comes from pending_test_slug, not question content."""
        eval_out = _make_eval_output("correct")
        mock_provider = _make_provider_mock()
        mock_prompt, _ = _make_prompt_mock(eval_out)
        state = _eval_mode_state(pending_test_slug="vector_databases")
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            result = await assess_node(state)  # type: ignore[arg-type]
        assert "vector_databases" in result["topic_scores_delta"], (
            f"Delta key must be pending_test_slug='vector_databases', got {result['topic_scores_delta']!r}"
        )


# ---------------------------------------------------------------------------
# Gate 4 — assessment_error fallback path: graph never crashes on LLM failure
# ---------------------------------------------------------------------------

class TestGate4FallbackOnFailure:
    """assess_node sets assessment_error=True and returns safely on any failure."""

    @pytest.mark.asyncio
    async def test_provider_error_in_eval_mode_sets_assessment_error(self) -> None:
        """LLM provider failure in eval mode sets assessment_error=True."""
        with (
            patch("agents.nodes.assess.get_provider", side_effect=RuntimeError("provider down")),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            result = await assess_node(_eval_mode_state())  # type: ignore[arg-type]
        assert result["assessment_error"] is True

    @pytest.mark.asyncio
    async def test_chain_failure_in_eval_mode_does_not_raise(self) -> None:
        """chain.ainvoke() raising must not propagate out of assess_node."""
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(side_effect=ValueError("LLM schema error"))
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)
        mock_provider = _make_provider_mock()
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            try:
                result = await assess_node(_eval_mode_state())  # type: ignore[arg-type]
            except Exception as exc:
                pytest.fail(f"assess_node must not raise on LLM failure: {exc!r}")
        assert result["assessment_error"] is True

    @pytest.mark.asyncio
    async def test_missing_curriculum_file_sets_assessment_error(self) -> None:
        """FileNotFoundError loading curriculum sets assessment_error=True."""
        with (
            patch(
                "agents.nodes.assess._run_passive_assessment",
                new=AsyncMock(return_value=({}, True)),
            ),
            patch("pathlib.Path.read_text", side_effect=FileNotFoundError("no file")),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["assessment_error"] is True

    @pytest.mark.asyncio
    async def test_error_fallback_returns_all_keys(self) -> None:
        """Fallback result from any failure mode contains all 9 declared output keys."""
        with patch("agents.nodes.assess.get_provider", side_effect=Exception("any error")):
            with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
                with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                    result = await assess_node(_eval_mode_state())  # type: ignore[arg-type]
        expected = {
            "topic_scores_delta", "identified_gaps", "assessment_error",
            "test_mode", "pending_test_question", "pending_test_slug",
            "is_mcq", "pending_mcq_correct_answer",
        }
        assert set(result.keys()) == expected, (
            f"Fallback must return all 8 keys, got {set(result.keys())}"
        )

    @pytest.mark.asyncio
    async def test_invalid_pending_slug_sets_assessment_error(self) -> None:
        """pending_test_slug not in VALID_MODULE_SLUGS triggers assessment_error=True."""
        state = _eval_mode_state(pending_test_slug="not_a_real_slug")
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(state)  # type: ignore[arg-type]
        assert result["assessment_error"] is True, (
            "Invalid pending_test_slug must produce assessment_error=True"
        )


# ---------------------------------------------------------------------------
# Gate 5 — AgentState schema: all 4 new fields present with correct types
# ---------------------------------------------------------------------------

class TestGate5AgentStateNewFields:
    """All 4 new AgentState fields exist, have correct types in output."""

    @pytest.mark.asyncio
    async def test_test_mode_field_is_bool(self) -> None:
        """test_mode output is a bool."""
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert isinstance(result["test_mode"], bool), (
            f"test_mode must be bool, got {type(result['test_mode'])}"
        )

    @pytest.mark.asyncio
    async def test_pending_test_question_is_str_or_none(self) -> None:
        """pending_test_question is str in test mode, None in eval mode."""
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(_base_state())  # type: ignore[arg-type]
        val = result["pending_test_question"]
        assert val is None or isinstance(val, str), (
            f"pending_test_question must be str or None, got {type(val)}"
        )

    @pytest.mark.asyncio
    async def test_pending_test_slug_is_str_or_none(self) -> None:
        """pending_test_slug is str in test mode, None in eval mode."""
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(_base_state())  # type: ignore[arg-type]
        val = result["pending_test_slug"]
        assert val is None or isinstance(val, str), (
            f"pending_test_slug must be str or None, got {type(val)}"
        )

    @pytest.mark.asyncio
    async def test_all_3_new_fields_present_in_test_mode_output(self) -> None:
        """test_mode output contains all 3 new AgentState fields."""
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(_base_state())  # type: ignore[arg-type]
        for field in ("test_mode", "pending_test_question", "pending_test_slug"):
            assert field in result, f"Output missing new field '{field}'"

    @pytest.mark.asyncio
    async def test_all_3_new_fields_present_in_eval_mode_output(self) -> None:
        """eval_mode output contains all 3 new AgentState fields."""
        eval_out = _make_eval_output("partial")
        mock_provider = _make_provider_mock()
        mock_prompt, _ = _make_prompt_mock(eval_out)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            result = await assess_node(_eval_mode_state())  # type: ignore[arg-type]
        for field in ("test_mode", "pending_test_question", "pending_test_slug"):
            assert field in result, f"Eval mode output missing new field '{field}'"


# ---------------------------------------------------------------------------
# Gate 6 — pending_test_slug validated against VALID_MODULE_SLUGS
# ---------------------------------------------------------------------------

class TestGate6SlugValidation:
    """pending_test_slug in eval mode must be in VALID_MODULE_SLUGS."""

    def test_valid_module_slugs_contains_9_canonical_slugs(self) -> None:
        """VALID_MODULE_SLUGS has exactly the 9 canonical topic slugs."""
        expected = {
            "embeddings_and_similarity",
            "rag_pipeline_architecture",
            "chunking_strategies",
            "vector_databases",
            "retrieval_methods",
            "context_and_prompting",
            "langchain_fundamentals",
            "evaluation_and_metrics",
            "production_patterns",
        }
        assert VALID_MODULE_SLUGS == expected, (
            f"VALID_MODULE_SLUGS mismatch.\n"
            f"Expected: {expected}\n"
            f"Got:      {VALID_MODULE_SLUGS}"
        )

    @pytest.mark.asyncio
    async def test_eval_mode_with_valid_slug_succeeds(self) -> None:
        """Valid pending_test_slug in eval mode does not set assessment_error."""
        eval_out = _make_eval_output("correct")
        mock_provider = _make_provider_mock()
        mock_prompt, _ = _make_prompt_mock(eval_out)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            result = await assess_node(_eval_mode_state(pending_test_slug="embeddings_and_similarity"))  # type: ignore[arg-type]
        assert result["assessment_error"] is False

    @pytest.mark.asyncio
    async def test_eval_mode_with_invalid_slug_sets_assessment_error(self) -> None:
        """Invalid pending_test_slug in eval mode sets assessment_error=True."""
        state = _eval_mode_state(pending_test_slug="rag_fundamentals")  # stale slug
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(state)  # type: ignore[arg-type]
        assert result["assessment_error"] is True, (
            "Stale slug 'rag_fundamentals' must trigger assessment_error=True"
        )


# ---------------------------------------------------------------------------
# Gate 7 — Output key boundary
# ---------------------------------------------------------------------------

class TestGate7OutputKeyBoundary:
    """assess_node must write only its 8 declared output keys."""

    _DECLARED_OUTPUT_KEYS: frozenset[str] = frozenset({
        "topic_scores_delta",
        "identified_gaps",
        "assessment_error",
        "test_mode",
        "pending_test_question",
        "pending_test_slug",
        "is_mcq",
        "pending_mcq_correct_answer",
    })

    _FORBIDDEN_KEYS: frozenset[str] = frozenset({
        "messages",
        "docs",
        "answer",
        "question",
        "retrieval_source",
        "user_id",
        "trace_id",
        "latency_ms",
        "cache_hit",
        "user_level",
    })

    @pytest.mark.asyncio
    async def test_no_foreign_keys_in_test_mode_output(self) -> None:
        """Test mode output must not contain any forbidden state keys."""
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(_base_state())  # type: ignore[arg-type]
        foreign = set(result.keys()) & self._FORBIDDEN_KEYS
        assert not foreign, f"assess_node must not write forbidden keys: {foreign}"

    @pytest.mark.asyncio
    async def test_output_has_exactly_declared_keys_test_mode(self) -> None:
        """Test mode output contains exactly the 7 declared keys."""
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert set(result.keys()) == self._DECLARED_OUTPUT_KEYS, (
            f"Output keys mismatch: {set(result.keys())} != {self._DECLARED_OUTPUT_KEYS}"
        )

    @pytest.mark.asyncio
    async def test_output_has_exactly_declared_keys_eval_mode(self) -> None:
        """Eval mode output contains exactly the 9 declared keys plus session_question_counts."""
        eval_out = _make_eval_output("partial")
        mock_provider = _make_provider_mock()
        mock_prompt, _ = _make_prompt_mock(eval_out)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            result = await assess_node(_eval_mode_state())  # type: ignore[arg-type]
        expected = self._DECLARED_OUTPUT_KEYS | {"session_question_counts"}
        assert set(result.keys()) == expected, (
            f"Eval mode output keys mismatch: {set(result.keys())} != {expected}"
        )

    @pytest.mark.asyncio
    async def test_user_level_not_written_to_state(self) -> None:
        """assess_node must NOT write user_level — state ownership conflict."""
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert "user_level" not in result, (
            "assess_node must NOT write user_level to state (ownership conflict)"
        )


# ---------------------------------------------------------------------------
# Gate 8 — Graph compiles and ainvoke() does not raise
# ---------------------------------------------------------------------------

class TestGate8GraphTopologySmoke:
    """Full 4-node graph must compile and run without raising."""

    @pytest.mark.asyncio
    async def test_graph_compiles(self) -> None:
        """build_graph() returns a CompiledStateGraph."""
        from langgraph.graph.state import CompiledStateGraph

        from agents.graph import build_graph

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
        ):
            graph = build_graph(MemorySaver())
        assert isinstance(graph, CompiledStateGraph)

    @pytest.mark.asyncio
    async def test_ainvoke_does_not_raise(self) -> None:
        """4-node graph ainvoke() with test-mode state does not raise."""
        from agents.graph import build_graph

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "assess-24-smoke"}}
            try:
                await graph.ainvoke(_make_full_initial_state(), config=config)
            except Exception as exc:
                pytest.fail(f"4-node graph ainvoke() raised unexpectedly: {exc}")

    @pytest.mark.asyncio
    async def test_fallback_path_reaches_update_profile(self) -> None:
        """assessment_error=True from assess_node still routes to update_profile_node."""
        from agents.graph import build_graph

        update_profile_calls: list[dict[str, Any]] = []

        async def stub_assess_error(state: dict[str, Any]) -> dict[str, Any]:
            return {
                "topic_scores_delta": {},
                "identified_gaps": [],
                "assessment_error": True,
                "test_mode": False,
                "pending_test_question": None,
                "pending_test_slug": None,
                "is_mcq": False,
                "pending_mcq_correct_answer": None,
            }

        def capture_update_profile(state: dict[str, Any]) -> dict[str, Any]:
            update_profile_calls.append(dict(state))
            return {}

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
            patch("agents.graph.assess_node", side_effect=stub_assess_error),
            patch("agents.graph.update_profile_node", side_effect=capture_update_profile),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "assess-24-fallback"}}
            result = await graph.ainvoke(_make_full_initial_state(), config=config)

        assert len(update_profile_calls) == 1, (
            f"update_profile_node must run exactly once; got {len(update_profile_calls)}"
        )
        assert result.get("assessment_error") is True

    def test_route_after_assess_always_returns_update_profile(self) -> None:
        """_route_after_assess routes both True and False assessment_error to 'update_profile'."""
        from agents.graph import _route_after_assess

        state_ok = _base_state(assessment_error=False)
        state_err = _base_state(assessment_error=True)
        assert _route_after_assess(state_ok) == "update_profile"  # type: ignore[arg-type]
        assert _route_after_assess(state_err) == "update_profile"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestOffTopicSuppression — off-topic queries must not produce a knowledge check
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# TestPhaseGateSlugSelection — select_test_slug phase-gating (Commit 34)
# ---------------------------------------------------------------------------

class TestPhaseGateSlugSelection:
    """select_test_slug returns only slugs eligible for the user's current phase."""

    _PHASE_1_SLUGS: frozenset[str] = frozenset({"embeddings_and_similarity", "rag_pipeline_architecture"})
    _PHASE_2_SLUGS: frozenset[str] = frozenset({"chunking_strategies", "vector_databases", "retrieval_methods", "context_and_prompting", "langchain_fundamentals"})
    _PHASE_3_SLUGS: frozenset[str] = frozenset({"evaluation_and_metrics", "production_patterns"})

    def test_novice_returns_only_phase_1_slug(self) -> None:
        """novice level: selected slug must be a Phase 1 topic."""
        state = _base_state(user_level="novice", identified_gaps=[])
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result in self._PHASE_1_SLUGS, (
            f"novice must get a Phase 1 slug, got {result!r}"
        )

    def test_beginner_returns_only_phase_1_slug(self) -> None:
        """beginner level: selected slug must be a Phase 1 topic."""
        state = _base_state(user_level="beginner", identified_gaps=[])
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result in self._PHASE_1_SLUGS, (
            f"beginner must get a Phase 1 slug, got {result!r}"
        )

    def test_intermediate_returns_only_phase_2_slug(self) -> None:
        """intermediate level: selected slug must be a Phase 2 topic."""
        state = _base_state(user_level="intermediate", identified_gaps=[])
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result in self._PHASE_2_SLUGS, (
            f"intermediate must get a Phase 2 slug, got {result!r}"
        )

    def test_advanced_returns_only_phase_3_slug(self) -> None:
        """advanced level: selected slug must be a Phase 3 topic."""
        state = _base_state(user_level="advanced", identified_gaps=[])
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result in self._PHASE_3_SLUGS, (
            f"advanced must get a Phase 3 slug, got {result!r}"
        )

    def test_expert_returns_phase_1_slug_first(self) -> None:
        """expert level: canonical ordering puts Phase 1 first, so first slug is Phase 1."""
        state = _base_state(user_level="expert", identified_gaps=[])
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result in self._PHASE_1_SLUGS, (
            f"expert canonical ordering must start with Phase 1 slug, got {result!r}"
        )

    def test_gap_in_eligible_phase_returned_first(self) -> None:
        """Gap within the eligible phase is returned before canonical fallback."""
        state = _base_state(
            user_level="intermediate",
            identified_gaps=["retrieval_methods"],
        )
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result == "retrieval_methods", (
            f"Phase 2 gap 'retrieval_methods' must be returned first, got {result!r}"
        )

    def test_gap_outside_eligible_phase_is_skipped(self) -> None:
        """Gap from a non-eligible phase is skipped; canonical phase slug is returned instead."""
        state = _base_state(
            user_level="beginner",
            identified_gaps=["evaluation_and_metrics"],  # Phase 3 — not eligible for beginner
        )
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result in self._PHASE_1_SLUGS, (
            f"Phase 3 gap must be skipped for beginner; expected Phase 1 slug, got {result!r}"
        )

    def test_returns_none_when_valid_slugs_empty(self) -> None:
        """None returned when VALID_MODULE_SLUGS is patched to empty."""
        state = _base_state(user_level="novice", identified_gaps=[])
        with patch("agents.assessment.question_selection.VALID_MODULE_SLUGS", new=frozenset()):
            selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result is None, (
            f"Must return None when VALID_MODULE_SLUGS is empty, got {result!r}"
        )


class TestOffTopicSuppression:
    """Off-topic queries suppress pending_test_question; on-topic queries do not."""

    @pytest.mark.asyncio
    async def test_off_topic_query_suppresses_test_question(self) -> None:
        """When _run_passive_assessment returns is_rag_related=False, no knowledge check is set."""
        with patch(
            "agents.nodes.assess._run_passive_assessment",
            new=AsyncMock(return_value=({}, False)),
        ):
            result = await assess_node(_base_state(question="hi there"))  # type: ignore[arg-type]
        assert result["pending_test_question"] is None, (
            "Off-topic query must not produce a pending_test_question"
        )
        assert result["test_mode"] is False, (
            "Off-topic query must set test_mode=False"
        )

    @pytest.mark.asyncio
    async def test_on_topic_query_sets_test_question(self) -> None:
        """When _run_passive_assessment returns is_rag_related=True, knowledge check is served."""
        with (
            patch(
                "agents.nodes.assess._run_passive_assessment",
                new=AsyncMock(return_value=({"embeddings_and_similarity": 0.1}, True)),
            ),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
            patch(
                "agents.nodes.assess._load_mcq_question",
                return_value=("Knowledge check: stub question\n\nA. a\nB. b\nC. c\nD. d", "B"),
            ),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["pending_test_question"], (
            "On-topic query must set pending_test_question to a non-empty string"
        )
        assert result["test_mode"] is True, (
            "On-topic query must set test_mode=True"
        )


# ---------------------------------------------------------------------------
# TestMcqLoader — _load_mcq_question(slug, question_index)
# ---------------------------------------------------------------------------

class TestMcqLoader:
    """Tests for _load_mcq_question: file loading, format contract, error paths."""

    def test_valid_slug_returns_tuple(self) -> None:
        """Valid slug returns a (display_text, correct_answer) tuple."""
        display_text, correct_answer = _load_mcq_question("chunking_strategies", 0)
        assert isinstance(display_text, str)
        assert isinstance(correct_answer, str)

    def test_display_text_starts_with_knowledge_check(self) -> None:
        """display_text must start with 'Knowledge check:'."""
        display_text, _ = _load_mcq_question("chunking_strategies", 0)
        assert display_text.startswith("Knowledge check:"), (
            f"display_text must start with 'Knowledge check:', got: {display_text[:40]!r}"
        )

    def test_display_text_contains_all_four_options(self) -> None:
        """display_text must contain all 4 options matching '^[A-D].' pattern."""
        display_text, _ = _load_mcq_question("chunking_strategies", 0)
        matches = re.findall(r"^[A-D]\.", display_text, re.MULTILINE)
        assert len(matches) == 4, (
            f"Expected 4 options matching '^[A-D].', found {len(matches)}: {matches}"
        )

    def test_correct_answer_is_valid_letter(self) -> None:
        """correct_answer must be one of 'A', 'B', 'C', 'D'."""
        _, correct_answer = _load_mcq_question("chunking_strategies", 0)
        assert correct_answer in ("A", "B", "C", "D"), (
            f"correct_answer must be A/B/C/D, got {correct_answer!r}"
        )

    def test_first_question_correct_answer_is_b(self) -> None:
        """MCQ-1 for chunking_strategies has correct answer B (known from file)."""
        _, correct_answer = _load_mcq_question("chunking_strategies", 0)
        assert correct_answer == "B", (
            f"MCQ-1 chunking_strategies correct answer must be 'B', got {correct_answer!r}"
        )

    def test_unknown_slug_raises_file_not_found(self) -> None:
        """Unknown slug raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            _load_mcq_question("nonexistent_slug", 0)

    def test_malformed_question_block_raises_value_error(self, tmp_path: pathlib.Path) -> None:
        """MCQ file missing **Question:** field raises ValueError."""
        bad_mcq = tmp_path / "bad_topic.md"
        bad_mcq.write_text(
            "## MCQ-1 — Broken question\n\n**Difficulty:** beginner\n\n"
            "**Options:**\nA. Opt1\nB. Opt2\nC. Opt3\nD. Opt4\n\n"
            "**Correct answer:** A\n",
            encoding="utf-8",
        )
        from agents.mcq_utils import _MCQ_DIR  # noqa: F401 — imported for patch target validation
        with patch("agents.mcq_utils._MCQ_DIR", new=tmp_path):
            with pytest.raises(ValueError):
                _load_mcq_question("bad_topic", 0)

    def test_modulo_wrapping_returns_same_as_index_zero(self) -> None:
        """question_index=5 wraps to same question as index=0 for a 5-question file."""
        text_0, ans_0 = _load_mcq_question("chunking_strategies", 0)
        text_5, ans_5 = _load_mcq_question("chunking_strategies", 5)
        assert text_0 == text_5, "question_index=5 must wrap to question_index=0 (5 % 5 == 0)"
        assert ans_0 == ans_5


# ---------------------------------------------------------------------------
# TestMcqEvaluator — _evaluate_mcq_answer(user_message, correct_answer)
# ---------------------------------------------------------------------------

class TestMcqEvaluator:
    """Deterministic binary MCQ scorer — no LLM involved."""

    def test_exact_match_returns_1_0(self) -> None:
        """Exact letter match returns 1.0."""
        assert _evaluate_mcq_answer("B", "B") == 1.0

    def test_case_insensitive_match_returns_1_0(self) -> None:
        """Lowercase user answer matched case-insensitively."""
        assert _evaluate_mcq_answer("b", "B") == 1.0

    def test_wrong_letter_returns_0_0(self) -> None:
        """Wrong letter returns 0.0."""
        assert _evaluate_mcq_answer("A", "B") == 0.0

    def test_letter_extracted_from_prose_returns_1_0(self) -> None:
        """Letter extracted from prose when user says 'Option B is correct'."""
        assert _evaluate_mcq_answer("Option B is correct", "B") == 1.0

    def test_no_letter_in_message_returns_0_0(self) -> None:
        """No matching letter in message returns 0.0."""
        assert _evaluate_mcq_answer("none of the above", "B") == 0.0

    def test_letter_followed_by_period_returns_1_0(self) -> None:
        """'B.' — letter with trailing period — must be extracted and matched."""
        assert _evaluate_mcq_answer("B.", "B") == 1.0


# ---------------------------------------------------------------------------
# TestMcqEvaluationIntegration — _evaluate_answer with is_mcq=True
# ---------------------------------------------------------------------------

class TestMcqEvaluationIntegration:
    """Integration tests for the MCQ branch in _evaluate_answer."""

    @pytest.mark.asyncio
    async def test_correct_mcq_answer_returns_score_1_0(self) -> None:
        """is_mcq=True with correct answer: binary score 1.0 returned, no LLM call."""
        with patch("agents.nodes.assess.get_provider") as mock_gp:
            result = await assess_node(_mcq_eval_state())  # type: ignore[arg-type]
        mock_gp.assert_not_called()
        assert result["topic_scores_delta"].get("chunking_strategies") == 1.0, (
            f"Correct MCQ answer must score 1.0 in topic_scores_delta, got {result['topic_scores_delta']!r}"
        )

    @pytest.mark.asyncio
    async def test_mcq_flags_cleared_after_evaluation(self) -> None:
        """is_mcq and pending_mcq_correct_answer cleared to False/None after MCQ eval."""
        with patch("agents.nodes.assess.get_provider"):
            result = await assess_node(_mcq_eval_state())  # type: ignore[arg-type]
        assert result["is_mcq"] is False, (
            f"is_mcq must be False after MCQ evaluation, got {result['is_mcq']!r}"
        )
        assert result["pending_mcq_correct_answer"] is None, (
            f"pending_mcq_correct_answer must be None after MCQ evaluation, got {result['pending_mcq_correct_answer']!r}"
        )

    @pytest.mark.asyncio
    async def test_mcq_evaluation_identified_gaps_is_empty(self) -> None:
        """identified_gaps is empty list in MCQ evaluation result."""
        with patch("agents.nodes.assess.get_provider"):
            result = await assess_node(_mcq_eval_state())  # type: ignore[arg-type]
        assert result["identified_gaps"] == [], (
            f"MCQ path must return empty identified_gaps, got {result['identified_gaps']!r}"
        )

    @pytest.mark.asyncio
    async def test_incorrect_mcq_answer_returns_score_0_0(self) -> None:
        """is_mcq=True with wrong answer: binary score 0.0 returned."""
        state = _mcq_eval_state(
            messages=[
                AIMessage(content="Knowledge check: Why must documents be split?\n\nA. Cost\nB. Token limit\nC. Quality\nD. LLM"),
                HumanMessage(content="A"),
            ],
            question="A",
        )
        with patch("agents.nodes.assess.get_provider"):
            result = await assess_node(state)  # type: ignore[arg-type]
        assert result["topic_scores_delta"].get("chunking_strategies") == 0.0, (
            f"Wrong MCQ answer must score 0.0 in topic_scores_delta, got {result['topic_scores_delta']!r}"
        )

    @pytest.mark.asyncio
    async def test_non_mcq_path_calls_get_provider(self) -> None:
        """is_mcq=False in eval mode calls the LLM path (get_provider invoked)."""
        eval_out = _make_eval_output("partial")
        mock_provider = _make_provider_mock()
        mock_prompt, _ = _make_prompt_mock(eval_out)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider) as mock_gp,
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            await assess_node(_eval_mode_state())  # type: ignore[arg-type]
        mock_gp.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcq_none_correct_answer_returns_assessment_error(self) -> None:
        """is_mcq=True with pending_mcq_correct_answer=None must flag assessment_error."""
        state = _mcq_eval_state(pending_mcq_correct_answer=None)
        with patch("agents.nodes.assess.get_provider") as mock_gp:
            result = await assess_node(state)  # type: ignore[arg-type]
        assert result["assessment_error"] is True, (
            "Missing correct answer with is_mcq=True must return assessment_error=True"
        )
        mock_gp.assert_not_called()

    @pytest.mark.asyncio
    async def test_evaluate_answer_invalid_slug_with_is_mcq_returns_error(self) -> None:
        """Slug validation fires before MCQ branch — invalid slug returns assessment_error."""
        state = _mcq_eval_state(pending_test_slug="fake_topic")
        with patch("agents.nodes.assess.get_provider") as mock_gp:
            result = await assess_node(state)  # type: ignore[arg-type]
        assert result["assessment_error"] is True
        assert result.get("topic_scores_delta") == {}, (
            "Invalid slug must not produce a score delta"
        )
        mock_gp.assert_not_called()

    @pytest.mark.asyncio
    async def test_select_test_question_mcq_answer_is_single_letter(self) -> None:
        """pending_mcq_correct_answer must be a single letter A-D, not question text."""
        state = _base_state(
            identified_gaps=["chunking_strategies"],
            user_level="novice",
        )
        with patch(
            "agents.nodes.assess._run_passive_assessment",
            new=AsyncMock(return_value=({}, True)),
        ):
            result = await assess_node(state)  # type: ignore[arg-type]
        if result.get("test_mode"):
            answer = result.get("pending_mcq_correct_answer")
            assert answer in ("A", "B", "C", "D"), (
                f"pending_mcq_correct_answer must be A/B/C/D, got {answer!r}"
            )


# ---------------------------------------------------------------------------
# TestQuestionIndexCycling — _select_question_index  — Commit 39 bug fix
# ---------------------------------------------------------------------------

class TestQuestionIndexCycling:
    """_select_question_index returns len(messages) % 5, cycling within the 5-question bank."""

    def test_zero_messages_returns_0(self) -> None:
        state = _base_state(messages=[])
        assert _select_question_index(state) == 0

    def test_turn_4_returns_index_4(self) -> None:
        state = _base_state(messages=[HumanMessage(content=f"q{i}") for i in range(4)])
        assert _select_question_index(state) == 4

    def test_turn_5_wraps_to_index_0(self) -> None:
        """Turn 5 (5 % 5 = 0) must cycle back to question 0, not index 5 (out of range)."""
        state = _base_state(messages=[HumanMessage(content=f"q{i}") for i in range(5)])
        assert _select_question_index(state) == 0, (
            "5 messages: 5 % 5 = 0 — must return 0 not 5"
        )

    def test_turn_6_wraps_to_index_1(self) -> None:
        state = _base_state(messages=[HumanMessage(content=f"q{i}") for i in range(6)])
        assert _select_question_index(state) == 1

    def test_turn_7_wraps_to_index_2(self) -> None:
        state = _base_state(messages=[HumanMessage(content=f"q{i}") for i in range(7)])
        assert _select_question_index(state) == 2

    def test_index_always_valid_for_5_question_bank(self) -> None:
        """Any message count must produce an index in [0, 4] — never out of range for a 5-question file."""
        for n in range(20):
            state = _base_state(messages=[HumanMessage(content=f"q{i}") for i in range(n)])
            idx = _select_question_index(state)
            assert 0 <= idx <= 4, (
                f"n_messages={n} produced index={idx}, which is out of [0, 4]"
            )


# ---------------------------------------------------------------------------
# TestGateRemediation — intermediate users receive Phase 1 gap questions (Commit 41)
# ---------------------------------------------------------------------------

class TestGateRemediation:
    """select_test_slug grants intermediate users access to Phase 1 gap remediation."""

    def test_intermediate_with_phase1_gap_returns_phase1_slug(self) -> None:
        """Intermediate user with a Phase 1 identified gap receives that Phase 1 slug."""
        state = _base_state(
            user_level="intermediate",
            identified_gaps=["embeddings_and_similarity"],
        )
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result == "embeddings_and_similarity", (
            f"Intermediate user with Phase 1 gap must receive that slug, got {result!r}"
        )

    def test_intermediate_with_no_gaps_returns_phase2_slug(self) -> None:
        """Intermediate user with no gaps falls through to canonical Phase 2 ordering."""
        state = _base_state(user_level="intermediate", identified_gaps=[])
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        from app.profile.scoring import PHASE_2_TOPICS
        assert result in PHASE_2_TOPICS, (
            f"Intermediate with no gaps must get a Phase 2 slug, got {result!r}"
        )

    def test_intermediate_phase1_gap_takes_priority_over_phase2_gap(self) -> None:
        """Phase 1 gap remediation takes priority over a Phase 2 gap for intermediate users."""
        state = _base_state(
            user_level="intermediate",
            identified_gaps=["retrieval_methods", "rag_pipeline_architecture"],
        )
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result == "rag_pipeline_architecture", (
            f"Phase 1 gap must beat Phase 2 gap for intermediate; got {result!r}"
        )

    def test_novice_with_phase1_gap_still_returns_phase1_slug(self) -> None:
        """Novice users also get Phase 1 gap slugs via the normal gap-first path (unchanged)."""
        state = _base_state(
            user_level="novice",
            identified_gaps=["rag_pipeline_architecture"],
        )
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result == "rag_pipeline_architecture", (
            f"Novice with Phase 1 gap must still receive that slug, got {result!r}"
        )

    def test_langchain_fundamentals_slug_is_valid(self) -> None:
        """langchain_fundamentals must be in VALID_MODULE_SLUGS after Commit 41 wiring."""
        assert "langchain_fundamentals" in VALID_MODULE_SLUGS, (
            "langchain_fundamentals must be a valid slug"
        )

    def test_langchain_fundamentals_served_to_intermediate_user(self) -> None:
        """Intermediate user with no gaps can receive langchain_fundamentals (Phase 2)."""
        state = _base_state(
            user_level="intermediate",
            identified_gaps=["langchain_fundamentals"],
        )
        selection = select_mcq_question(state)  # type: ignore[arg-type]
        result = selection[0] if selection else None
        assert result == "langchain_fundamentals", (
            f"langchain_fundamentals gap must be served to intermediate user, got {result!r}"
        )


# ---------------------------------------------------------------------------
# TestSessionQuestionCounts — session_question_counts incremented in eval mode (Commit 41)
# ---------------------------------------------------------------------------

class TestSessionQuestionCounts:
    """assess_node emits session_question_counts increments in evaluation mode."""

    @pytest.mark.asyncio
    async def test_mcq_eval_emits_session_question_counts(self) -> None:
        """MCQ evaluation mode emits session_question_counts with pending_slug incremented."""
        with patch("agents.nodes.assess.get_provider"):
            result = await assess_node(_mcq_eval_state())  # type: ignore[arg-type]
        assert "session_question_counts" in result, (
            "MCQ eval must emit session_question_counts"
        )
        counts = result["session_question_counts"]
        assert counts.get("chunking_strategies") == 1, (
            f"chunking_strategies must be 1 after first eval, got {counts!r}"
        )

    @pytest.mark.asyncio
    async def test_session_counts_accumulate_across_evals(self) -> None:
        """Prior session_question_counts are incremented, not reset."""
        state = _mcq_eval_state(session_question_counts={"chunking_strategies": 2})
        with patch("agents.nodes.assess.get_provider"):
            result = await assess_node(state)  # type: ignore[arg-type]
        counts = result["session_question_counts"]
        assert counts.get("chunking_strategies") == 3, (
            f"chunking_strategies must be 3 (2+1), got {counts!r}"
        )

    @pytest.mark.asyncio
    async def test_test_mode_does_not_emit_session_question_counts(self) -> None:
        """Test mode (question selection) must NOT emit session_question_counts."""
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert "session_question_counts" not in result, (
            "Test mode must not emit session_question_counts"
        )
