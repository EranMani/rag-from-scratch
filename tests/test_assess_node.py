"""
Tests for Commit 24 (assessment-engine-rewrite).

Coverage targets (spec gates):

Gate 1 — Test mode turn: node returns curriculum question in pending_test_question
         with correct pending_test_slug; no LLM call made.
Gate 2 — Evaluation mode turn: node evaluates answer and returns non-zero test_answer_score.
Gate 3 — Score delta is derived from test_answer_score, not question content.
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
from typing import Any
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agents.nodes.assess import _CURRICULUM_DIR, assess_node
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
        "test_answer_score": None,
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
        "test_answer_score": None,
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
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["pending_test_slug"] in VALID_MODULE_SLUGS, (
            f"pending_test_slug {result['pending_test_slug']!r} not in VALID_MODULE_SLUGS"
        )

    @pytest.mark.asyncio
    async def test_test_mode_uses_identified_gap_slug(self) -> None:
        """Test mode prefers a slug from identified_gaps when available."""
        state = _base_state(identified_gaps=["vector_databases"])
        with (
            patch(
                "agents.nodes.assess._run_passive_assessment",
                new=AsyncMock(return_value=({}, True)),
            ),
            patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")),
            patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD),
        ):
            result = await assess_node(state)  # type: ignore[arg-type]
        assert result["pending_test_slug"] == "vector_databases", (
            f"Expected pending_test_slug='vector_databases', got {result['pending_test_slug']!r}"
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
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                with patch("agents.nodes.assess.get_provider", return_value=mock_provider):
                    result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["pending_test_question"], (
            "On-topic query must still set pending_test_question"
        )

    @pytest.mark.asyncio
    async def test_test_mode_test_answer_score_is_none(self) -> None:
        """Test mode sets test_answer_score=None (no answer yet)."""
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["test_answer_score"] is None, (
            f"Test mode must set test_answer_score=None, got {result['test_answer_score']!r}"
        )


# ---------------------------------------------------------------------------
# Gate 2 — Evaluation mode: returns non-zero test_answer_score
# ---------------------------------------------------------------------------

class TestGate2EvaluationMode:
    """assess_node in evaluation mode returns a scored test_answer_score."""

    @pytest.mark.asyncio
    async def test_eval_mode_returns_nonzero_score_for_partial(self) -> None:
        """Evaluation mode with 'partial' verdict returns test_answer_score=0.5."""
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
        assert result["test_answer_score"] == 0.5, (
            f"Expected test_answer_score=0.5 for 'partial', got {result['test_answer_score']!r}"
        )

    @pytest.mark.asyncio
    async def test_eval_mode_returns_1_0_for_correct(self) -> None:
        """Evaluation mode with 'correct' verdict returns test_answer_score=1.0."""
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
        assert result["test_answer_score"] == 1.0, (
            f"Expected test_answer_score=1.0 for 'correct', got {result['test_answer_score']!r}"
        )

    @pytest.mark.asyncio
    async def test_eval_mode_returns_0_0_for_incorrect(self) -> None:
        """Evaluation mode with 'incorrect' verdict returns test_answer_score=0.0."""
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
        assert result["test_answer_score"] == 0.0, (
            f"Expected test_answer_score=0.0 for 'incorrect', got {result['test_answer_score']!r}"
        )

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
# Gate 3 — Score delta derived from test_answer_score, not question content
# ---------------------------------------------------------------------------

class TestGate3ScoreDeltaFromScore:
    """topic_scores_delta is derived from test_answer_score and pending_test_slug."""

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
        """Fallback result from any failure mode contains all 7 declared output keys."""
        with patch("agents.nodes.assess.get_provider", side_effect=Exception("any error")):
            with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
                with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                    result = await assess_node(_eval_mode_state())  # type: ignore[arg-type]
        expected = {
            "topic_scores_delta", "identified_gaps", "assessment_error",
            "test_mode", "pending_test_question", "pending_test_slug", "test_answer_score",
        }
        assert set(result.keys()) == expected, (
            f"Fallback must return all 7 keys, got {set(result.keys())}"
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
    async def test_test_answer_score_is_float_or_none(self) -> None:
        """test_answer_score is float after evaluation, None in test mode."""
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
        val = result["test_answer_score"]
        assert val is None or isinstance(val, float), (
            f"test_answer_score must be float or None, got {type(val)}"
        )

    @pytest.mark.asyncio
    async def test_all_4_new_fields_present_in_test_mode_output(self) -> None:
        """test_mode output contains all 4 new AgentState fields."""
        with patch("agents.nodes.assess._CURRICULUM_DIR", new=pathlib.Path("/fake")):
            with patch("pathlib.Path.read_text", return_value=_SAMPLE_CURRICULUM_MD):
                result = await assess_node(_base_state())  # type: ignore[arg-type]
        for field in ("test_mode", "pending_test_question", "pending_test_slug", "test_answer_score"):
            assert field in result, f"Output missing new field '{field}'"

    @pytest.mark.asyncio
    async def test_all_4_new_fields_present_in_eval_mode_output(self) -> None:
        """eval_mode output contains all 4 new AgentState fields."""
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
        for field in ("test_mode", "pending_test_question", "pending_test_slug", "test_answer_score"):
            assert field in result, f"Eval mode output missing new field '{field}'"


# ---------------------------------------------------------------------------
# Gate 6 — pending_test_slug validated against VALID_MODULE_SLUGS
# ---------------------------------------------------------------------------

class TestGate6SlugValidation:
    """pending_test_slug in eval mode must be in VALID_MODULE_SLUGS."""

    def test_valid_module_slugs_contains_8_canonical_slugs(self) -> None:
        """VALID_MODULE_SLUGS has exactly the 8 canonical topic slugs."""
        expected = {
            "embeddings_and_similarity",
            "rag_pipeline_architecture",
            "chunking_strategies",
            "vector_databases",
            "retrieval_methods",
            "context_and_prompting",
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
    """assess_node must write only its 7 declared output keys."""

    _DECLARED_OUTPUT_KEYS: frozenset[str] = frozenset({
        "topic_scores_delta",
        "identified_gaps",
        "assessment_error",
        "test_mode",
        "pending_test_question",
        "pending_test_slug",
        "test_answer_score",
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
        """Eval mode output contains exactly the 7 declared keys."""
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
        assert set(result.keys()) == self._DECLARED_OUTPUT_KEYS, (
            f"Eval mode output keys mismatch: {set(result.keys())} != {self._DECLARED_OUTPUT_KEYS}"
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
                "test_answer_score": None,
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
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["pending_test_question"], (
            "On-topic query must set pending_test_question to a non-empty string"
        )
        assert result["test_mode"] is True, (
            "On-topic query must set test_mode=True"
        )
