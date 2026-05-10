"""
Tests for Commit 12 (langgraph-assessment-scaffold) and
Commit 13 (langgraph-assessment-llm).

Coverage targets (spec gates):

Gate 1: assess_node sets assessment_error=False and returns populated AssessmentOutput.
Gate 2: assess_node writes only its declared output keys (topic_scores_delta,
        identified_gaps, assessment_error) — no foreign state keys.
Gate 3: assess_node fallback — when an exception is raised internally, the node
        catches it, returns assessment_error=True, and returns empty deltas.
Gate 4: Conditional edge routes correctly:
        - assessment_error=False → "update_profile"
        - assessment_error=True  → "update_profile"
        Both paths compile and reach update_profile_node.
Gate 5: Graph compiles with the full 4-node topology (retrieve → generate →
        assess → update_profile → END) and ainvoke() does not raise.
Gate 6 (Commit 13): Happy-path LLM mock returns correct topic_scores_delta.
Gate 7 (Commit 13): LLM parse failure sets assessment_error=True without raising.
Gate 8 (Commit 13): user_level in mocked AssessmentOutput is a valid mastery level.
Gate 9 (Commit 13): get_provider() is called exactly once per assess_node invocation.

Design notes:
- All Gate 1–5 unit tests that call assess_node directly mock get_provider() so
  no live LLM or provider config is required.
- Gate 6–9 tests use targeted mocks: get_provider() returns a mock LLM whose
  with_structured_output().invoke() returns a controlled AssessmentOutput.
- Gate 3 tests patch get_provider() to raise — simulating a provider-level failure
  (e.g. circuit breaker exhausted, rate limit). This is the most realistic failure
  mode for the new LLM-backed implementation.
- _route_after_assess is imported and tested as a pure function — no graph needed.
- asyncio_mode = "auto" in pyproject.toml makes @pytest.mark.asyncio optional,
  but it is included explicitly for clarity.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agents.nodes.assess import assess_node
from agents.state import VALID_MODULE_SLUGS, AgentState, AssessmentOutput


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
        "identified_gaps": [],
        "assessment_error": False,
        "trace_id": "test-trace-12",
        "latency_ms": 0,
        "cache_hit": "miss",
    }
    base.update(overrides)
    return base


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
        "identified_gaps": [],
        "assessment_error": False,
        "trace_id": "test-trace-12-e2e",
        "latency_ms": 0,
        "cache_hit": "miss",
    }


def _stub_retrieve(state: dict[str, Any]) -> dict[str, Any]:
    """retrieve_node stub — returns one synthetic Document via chroma path."""
    return {
        "docs": [Document(page_content="RAG = Retrieval-Augmented Generation.", metadata={})],
        "retrieval_source": "chroma",
    }


async def _stub_generate(state: dict[str, Any]) -> dict[str, Any]:
    """Async generate_node stub — bypasses LLM for topology tests."""
    return {
        "messages": [AIMessage(content="Stubbed answer.")],
        "answer": "Stubbed answer.",
    }


# ---------------------------------------------------------------------------
# Shared mock factory — builds a get_provider mock returning controlled output
# ---------------------------------------------------------------------------

def _make_provider_mock(assessment_output: AssessmentOutput) -> MagicMock:
    """Return a mock provider whose get_llm() returns a mock LLM.

    The mock LLM's with_structured_output() returns a mock object that is
    recorded so tests can assert it was called with AssessmentOutput.
    The actual chain invocation is intercepted by patching assessment_prompt
    alongside get_provider (see _make_full_mock_context for the combined patch).
    """
    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=MagicMock())

    mock_provider = MagicMock()
    mock_provider.get_llm = MagicMock(return_value=mock_llm)

    return mock_provider


def _make_prompt_mock(assessment_output: AssessmentOutput) -> MagicMock:
    """Return a mock assessment_prompt whose pipe (|) chain.ainvoke() returns assessment_output.

    When assess_node does `chain = assessment_prompt | llm.with_structured_output(...)`,
    the mock_prompt's __or__ returns a mock chain whose ainvoke() is an AsyncMock
    returning assessment_output.  This avoids relying on LangChain's RunnableSequence
    internals to propagate mock return values correctly.
    """
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock(return_value=assessment_output)

    mock_prompt = MagicMock()
    mock_prompt.__or__ = MagicMock(return_value=mock_chain)

    return mock_prompt, mock_chain


def _default_assessment_output() -> AssessmentOutput:
    """A valid AssessmentOutput for use in happy-path tests."""
    return AssessmentOutput(
        topic_scores_delta={"vector_databases": 0.3},
        identified_gaps=["chunking_strategies"],
        user_level="intermediate",
    )


# ---------------------------------------------------------------------------
# Gate 1 — assess_node returns populated AssessmentOutput, assessment_error=False
# ---------------------------------------------------------------------------

class TestGate1AssessNodeHappyPath:
    """assess_node with mocked provider and prompt must return assessment_error=False
    and the output values from the LLM-parsed AssessmentOutput."""

    @pytest.mark.asyncio
    async def test_returns_assessment_error_false(self) -> None:
        """assess_node returns assessment_error=False when no exception occurs."""
        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["assessment_error"] is False, (
            f"assessment_error must be False on happy path, got {result['assessment_error']!r}"
        )

    @pytest.mark.asyncio
    async def test_returns_topic_scores_delta_dict(self) -> None:
        """assess_node returns a dict for topic_scores_delta."""
        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert isinstance(result["topic_scores_delta"], dict), (
            f"topic_scores_delta must be dict, got {type(result['topic_scores_delta'])}"
        )

    @pytest.mark.asyncio
    async def test_returns_identified_gaps_list(self) -> None:
        """assess_node returns a list for identified_gaps."""
        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert isinstance(result["identified_gaps"], list), (
            f"identified_gaps must be list, got {type(result['identified_gaps'])}"
        )

    @pytest.mark.asyncio
    async def test_output_types_are_correct(self) -> None:
        """assess_node output types: dict, list, bool."""
        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert isinstance(result["topic_scores_delta"], dict)
        assert isinstance(result["identified_gaps"], list)
        assert isinstance(result["assessment_error"], bool)


# ---------------------------------------------------------------------------
# Gate 2 — assess_node writes only its declared output keys
# ---------------------------------------------------------------------------

class TestGate2OutputKeyBoundary:
    """assess_node must not write to keys owned by other nodes."""

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
    })

    _DECLARED_OUTPUT_KEYS: frozenset[str] = frozenset({
        "topic_scores_delta",
        "identified_gaps",
        "assessment_error",
    })

    @pytest.mark.asyncio
    async def test_no_foreign_keys_in_output(self) -> None:
        """assess_node return dict must not contain any forbidden state keys."""
        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        foreign: set[str] = set(result.keys()) & self._FORBIDDEN_KEYS
        assert not foreign, (
            f"assess_node must not write to foreign state keys: {foreign}"
        )

    @pytest.mark.asyncio
    async def test_all_declared_keys_present(self) -> None:
        """assess_node return dict must contain all three declared output keys."""
        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        missing: set[str] = self._DECLARED_OUTPUT_KEYS - set(result.keys())
        assert not missing, (
            f"assess_node output is missing declared keys: {missing}"
        )

    @pytest.mark.asyncio
    async def test_output_has_exactly_declared_keys(self) -> None:
        """assess_node return dict contains only the three declared output keys."""
        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]
        extra: set[str] = set(result.keys()) - self._DECLARED_OUTPUT_KEYS
        assert not extra, (
            f"assess_node output has extra keys beyond declared contract: {extra}"
        )


# ---------------------------------------------------------------------------
# Gate 3 — assess_node fallback on internal exception
# ---------------------------------------------------------------------------

class TestGate3FallbackOnException:
    """When an exception is raised inside assess_node, it catches and returns
    assessment_error=True.  The realistic failure mode is the LLM chain raising —
    either from a provider error (get_provider() raises) or a structured-output
    parse failure (chain.ainvoke() raises).  Both are covered here."""

    @pytest.mark.asyncio
    async def test_provider_error_sets_assessment_error_true(self) -> None:
        """If get_provider() raises, assess_node returns assessment_error=True."""
        with patch(
            "agents.nodes.assess.get_provider",
            side_effect=ValueError("Simulated provider failure"),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]

        assert result["assessment_error"] is True, (
            f"assessment_error must be True on provider error, got {result['assessment_error']!r}"
        )

    @pytest.mark.asyncio
    async def test_chain_invoke_error_sets_assessment_error_true(self) -> None:
        """If chain.ainvoke() raises (LLM parse failure), assess_node returns assessment_error=True."""
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(side_effect=RuntimeError("Simulated LLM parse failure"))

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        mock_provider = MagicMock()
        mock_provider.get_llm = MagicMock(return_value=MagicMock())

        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]

        assert result["assessment_error"] is True, (
            f"assessment_error must be True on chain.ainvoke() failure, got {result['assessment_error']!r}"
        )

    @pytest.mark.asyncio
    async def test_exception_returns_empty_deltas(self) -> None:
        """On any exception, topic_scores_delta and identified_gaps are both empty."""
        with patch(
            "agents.nodes.assess.get_provider",
            side_effect=RuntimeError("Simulated timeout"),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]

        assert result["topic_scores_delta"] == {}, (
            f"On exception topic_scores_delta must be empty, got {result['topic_scores_delta']!r}"
        )
        assert result["identified_gaps"] == [], (
            f"On exception identified_gaps must be empty, got {result['identified_gaps']!r}"
        )

    @pytest.mark.asyncio
    async def test_exception_fallback_output_has_all_keys(self) -> None:
        """Fallback output on exception still contains all three declared output keys."""
        with patch(
            "agents.nodes.assess.get_provider",
            side_effect=Exception("Any failure"),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]

        assert set(result.keys()) == {"topic_scores_delta", "identified_gaps", "assessment_error"}, (
            f"Fallback output must have exactly the three declared keys, got {set(result.keys())}"
        )


# ---------------------------------------------------------------------------
# Gate 4 — Conditional edge routing (_route_after_assess)
# ---------------------------------------------------------------------------

class TestGate4ConditionalEdgeRouting:
    """_route_after_assess reads state['assessment_error'] and routes correctly."""

    def test_route_returns_update_profile_when_no_error(self) -> None:
        """assessment_error=False routes to 'update_profile'."""
        from agents.graph import _route_after_assess

        state = _base_state(assessment_error=False)
        assert _route_after_assess(state) == "update_profile", (  # type: ignore[arg-type]
            "assessment_error=False must route to 'update_profile'"
        )

    def test_route_returns_update_profile_when_error(self) -> None:
        """assessment_error=True also routes to 'update_profile' (fallback path)."""
        from agents.graph import _route_after_assess

        state = _base_state(assessment_error=True)
        assert _route_after_assess(state) == "update_profile", (  # type: ignore[arg-type]
            "assessment_error=True must route to 'update_profile' (fallback)"
        )

    def test_route_reads_assessment_error_not_other_key(self) -> None:
        """_route_after_assess is insensitive to unrelated state changes."""
        from agents.graph import _route_after_assess

        # Change several unrelated fields — routing must still depend only on assessment_error
        state_no_error = _base_state(assessment_error=False, user_level="expert")
        state_with_error = _base_state(assessment_error=True, user_level="expert")

        assert _route_after_assess(state_no_error) == "update_profile"  # type: ignore[arg-type]
        assert _route_after_assess(state_with_error) == "update_profile"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Gate 5 — Graph compiles with 4-node topology and ainvoke() does not raise
# ---------------------------------------------------------------------------

class TestGate5GraphCompiles:
    """Full 4-node graph (retrieve → generate → assess → update_profile) must compile
    and complete ainvoke() without raising.

    All tests that run the real assess_node must patch agents.nodes.assess.get_provider
    so no live LLM or provider config is required.
    """

    @pytest.mark.asyncio
    async def test_graph_compiles_without_error(self) -> None:
        """build_graph() with 4-node topology returns a CompiledStateGraph."""
        from langgraph.graph.state import CompiledStateGraph

        from agents.graph import build_graph

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
        ):
            graph = build_graph(MemorySaver())

        assert isinstance(graph, CompiledStateGraph), (
            f"build_graph() must return CompiledStateGraph, got {type(graph)}"
        )

    @pytest.mark.asyncio
    async def test_ainvoke_does_not_raise(self) -> None:
        """4-node graph ainvoke() with valid state does not raise any exception."""
        from agents.graph import build_graph

        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "assess-gate-5a"}}
            try:
                await graph.ainvoke(_make_full_initial_state(), config=config)
            except Exception as exc:
                pytest.fail(f"4-node graph ainvoke() raised unexpectedly: {exc}")

    @pytest.mark.asyncio
    async def test_ainvoke_returns_dict(self) -> None:
        """4-node graph ainvoke() returns a dict (state mapping)."""
        from agents.graph import build_graph

        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "assess-gate-5b"}}
            result = await graph.ainvoke(_make_full_initial_state(), config=config)

        assert isinstance(result, dict), (
            f"ainvoke() must return dict, got {type(result)}"
        )

    @pytest.mark.asyncio
    async def test_assess_node_output_in_final_state(self) -> None:
        """Final state contains topic_scores_delta, identified_gaps, assessment_error."""
        from agents.graph import build_graph

        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "assess-gate-5c"}}
            result = await graph.ainvoke(_make_full_initial_state(), config=config)

        assert "assessment_error" in result, "Final state must contain 'assessment_error'"
        assert "topic_scores_delta" in result, "Final state must contain 'topic_scores_delta'"
        assert "identified_gaps" in result, "Final state must contain 'identified_gaps'"
        assert result["assessment_error"] is False, (
            f"Real assess_node sets assessment_error=False on happy path, got {result['assessment_error']!r}"
        )

    @pytest.mark.asyncio
    async def test_fallback_path_reaches_update_profile(self) -> None:
        """When assess_node sets assessment_error=True, update_profile_node still runs."""
        from agents.graph import build_graph

        update_profile_calls: list[dict[str, Any]] = []

        async def stub_assess_error(state: dict[str, Any]) -> dict[str, Any]:
            """Simulate an assessment failure."""
            return {
                "topic_scores_delta": {},
                "identified_gaps": [],
                "assessment_error": True,
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
            config: dict[str, Any] = {"configurable": {"thread_id": "assess-gate-5-fallback"}}
            result = await graph.ainvoke(_make_full_initial_state(), config=config)

        assert len(update_profile_calls) == 1, (
            f"update_profile_node must run exactly once on fallback path, "
            f"got {len(update_profile_calls)} call(s)"
        )
        assert result.get("assessment_error") is True, (
            "Final state must preserve assessment_error=True from the error stub"
        )

    @pytest.mark.asyncio
    async def test_normal_path_reaches_update_profile(self) -> None:
        """When assess_node sets assessment_error=False, update_profile_node still runs."""
        from agents.graph import build_graph

        update_profile_calls: list[dict[str, Any]] = []

        def capture_update_profile(state: dict[str, Any]) -> dict[str, Any]:
            update_profile_calls.append(dict(state))
            return {}

        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
            patch("agents.graph.update_profile_node", side_effect=capture_update_profile),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "assess-gate-5-normal"}}
            result = await graph.ainvoke(_make_full_initial_state(), config=config)

        assert len(update_profile_calls) == 1, (
            f"update_profile_node must run exactly once on normal path, "
            f"got {len(update_profile_calls)} call(s)"
        )
        assert result.get("assessment_error") is False, (
            "Final state must have assessment_error=False on normal path"
        )


# ---------------------------------------------------------------------------
# Gate 6 (Commit 13) — Happy-path LLM mock: vector_databases slug present
# ---------------------------------------------------------------------------

class TestGate6HappyPathLLMOutput:
    """assess_node with a question about 'vector databases' returns topic_scores_delta
    with 'vector_databases' key set.  Spec gate: the LLM output is correctly mapped."""

    @pytest.mark.asyncio
    async def test_vector_databases_slug_in_delta(self) -> None:
        """Happy path: mock output with vector_databases slug is returned correctly."""
        llm_output = AssessmentOutput(
            topic_scores_delta={"vector_databases": 0.5},
            identified_gaps=[],
            user_level="beginner",
        )
        mock_provider = _make_provider_mock(llm_output)
        mock_prompt, _ = _make_prompt_mock(llm_output)
        state = _base_state(
            question="How do vector databases index embeddings?",
            answer="Vector databases use approximate nearest-neighbor algorithms like HNSW.",
        )
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(state)  # type: ignore[arg-type]

        assert "vector_databases" in result["topic_scores_delta"], (
            f"topic_scores_delta must contain 'vector_databases', got {result['topic_scores_delta']!r}"
        )
        assert result["topic_scores_delta"]["vector_databases"] == 0.5, (
            f"Expected delta 0.5, got {result['topic_scores_delta']['vector_databases']!r}"
        )

    @pytest.mark.asyncio
    async def test_output_delta_values_are_floats(self) -> None:
        """topic_scores_delta values must be float, not int or str."""
        llm_output = AssessmentOutput(
            topic_scores_delta={"rag_fundamentals": 0.2, "langchain": -0.1},
            identified_gaps=["chunking_strategies"],
            user_level="intermediate",
        )
        mock_provider = _make_provider_mock(llm_output)
        mock_prompt, _ = _make_prompt_mock(llm_output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]

        for slug, delta in result["topic_scores_delta"].items():
            assert isinstance(delta, float), (
                f"topic_scores_delta[{slug!r}] must be float, got {type(delta)}"
            )

    @pytest.mark.asyncio
    async def test_identified_gaps_values_are_valid_slugs(self) -> None:
        """identified_gaps values returned by assess_node must all be valid module slugs."""
        llm_output = AssessmentOutput(
            topic_scores_delta={},
            identified_gaps=["retrieval_methods", "production_patterns"],
            user_level="novice",
        )
        mock_provider = _make_provider_mock(llm_output)
        mock_prompt, _ = _make_prompt_mock(llm_output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]

        for gap in result["identified_gaps"]:
            assert gap in VALID_MODULE_SLUGS, (
                f"identified_gaps value {gap!r} is not a valid module slug"
            )


# ---------------------------------------------------------------------------
# Gate 7 (Commit 13) — LLM parse failure: assessment_error=True, no raise
# ---------------------------------------------------------------------------

class TestGate7LLMParseFailure:
    """When the LLM chain raises (parse failure or provider error), assess_node
    must set assessment_error=True and not re-raise the exception."""

    @pytest.mark.asyncio
    async def test_parse_failure_sets_assessment_error_true(self) -> None:
        """chain.ainvoke() raising ValueError → assessment_error=True, no raise."""
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(side_effect=ValueError("LLM returned invalid schema"))

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        mock_provider = MagicMock()
        mock_provider.get_llm = MagicMock(return_value=MagicMock())

        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]

        assert result["assessment_error"] is True, (
            f"LLM parse failure must set assessment_error=True, got {result['assessment_error']!r}"
        )

    @pytest.mark.asyncio
    async def test_parse_failure_returns_empty_topic_scores_delta(self) -> None:
        """On parse failure, topic_scores_delta must be an empty dict."""
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(side_effect=RuntimeError("Provider timeout"))

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        mock_provider = MagicMock()
        mock_provider.get_llm = MagicMock(return_value=MagicMock())

        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]

        assert result["topic_scores_delta"] == {}, (
            f"On failure topic_scores_delta must be empty, got {result['topic_scores_delta']!r}"
        )
        assert result["identified_gaps"] == [], (
            f"On failure identified_gaps must be empty, got {result['identified_gaps']!r}"
        )

    @pytest.mark.asyncio
    async def test_parse_failure_does_not_raise(self) -> None:
        """assess_node must not re-raise the LLM exception — must return gracefully."""
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(side_effect=Exception("Any LLM failure"))

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_chain)

        mock_provider = MagicMock()
        mock_provider.get_llm = MagicMock(return_value=MagicMock())

        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            try:
                result = await assess_node(_base_state())  # type: ignore[arg-type]
            except Exception as exc:
                pytest.fail(f"assess_node must not raise on LLM failure, got: {exc!r}")


# ---------------------------------------------------------------------------
# Gate 8 (Commit 13) — user_level in AssessmentOutput is a valid mastery level
# ---------------------------------------------------------------------------

class TestGate8UserLevelValidation:
    """AssessmentOutput.user_level must be one of the 5 valid mastery level Literals.
    The Pydantic model enforces this at parse time — assess_node never writes it
    back to AgentState."""

    _VALID_LEVELS: frozenset[str] = frozenset({
        "novice", "beginner", "intermediate", "advanced", "expert",
    })

    @pytest.mark.asyncio
    async def test_mocked_user_level_is_valid_literal(self) -> None:
        """The user_level in the mocked AssessmentOutput is one of the valid levels."""
        llm_output = _default_assessment_output()
        assert llm_output.user_level in self._VALID_LEVELS, (
            f"AssessmentOutput.user_level {llm_output.user_level!r} is not a valid mastery level"
        )

    def test_assessment_output_rejects_invalid_user_level(self) -> None:
        """AssessmentOutput raises ValidationError if user_level is not a valid Literal."""
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            AssessmentOutput(
                topic_scores_delta={},
                identified_gaps=[],
                user_level="master",  # type: ignore[arg-type]  — invalid
            )

    def test_assessment_output_accepts_all_valid_levels(self) -> None:
        """All 5 valid mastery levels are accepted by AssessmentOutput without error."""
        for level in self._VALID_LEVELS:
            output = AssessmentOutput(
                topic_scores_delta={},
                identified_gaps=[],
                user_level=level,  # type: ignore[arg-type]
            )
            assert output.user_level == level, (
                f"user_level {level!r} was mangled to {output.user_level!r}"
            )

    @pytest.mark.asyncio
    async def test_assess_node_does_not_write_user_level_to_state(self) -> None:
        """assess_node output must NOT contain 'user_level' — state ownership conflict."""
        llm_output = AssessmentOutput(
            topic_scores_delta={"rag_fundamentals": 0.1},
            identified_gaps=[],
            user_level="advanced",
        )
        mock_provider = _make_provider_mock(llm_output)
        mock_prompt, _ = _make_prompt_mock(llm_output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]

        assert "user_level" not in result, (
            "assess_node must NOT write 'user_level' back to AgentState — "
            f"state ownership conflict (Commit 15 design review); got keys: {set(result.keys())}"
        )


# ---------------------------------------------------------------------------
# Gate 9 (Commit 13) — get_provider() called once per assess_node invocation
# ---------------------------------------------------------------------------

class TestGate9ProviderRoutingPerInvocation:
    """get_provider() must be called once per assess_node() call — not at module level.
    Per-invocation call ensures every turn observes the current circuit breaker state."""

    @pytest.mark.asyncio
    async def test_get_provider_called_once_per_invocation(self) -> None:
        """get_provider() is called exactly once when assess_node is invoked once."""
        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider) as mock_get_provider,
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            await assess_node(_base_state())  # type: ignore[arg-type]

        mock_get_provider.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_provider_called_per_invocation_not_cached(self) -> None:
        """get_provider() is called once per assess_node() call — not cached across calls."""
        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider) as mock_get_provider,
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            await assess_node(_base_state())  # type: ignore[arg-type]
            await assess_node(_base_state())  # type: ignore[arg-type]

        assert mock_get_provider.call_count == 2, (
            f"get_provider() must be called once per assess_node() invocation (2 calls expected), "
            f"got {mock_get_provider.call_count} call(s)"
        )

    @pytest.mark.asyncio
    async def test_get_llm_called_on_provider_result(self) -> None:
        """get_llm() is called on the provider returned by get_provider()."""
        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            await assess_node(_base_state())  # type: ignore[arg-type]

        mock_provider.get_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_structured_output_called_with_assessment_output_class(self) -> None:
        """with_structured_output() is called with AssessmentOutput as the schema class."""
        output = _default_assessment_output()
        mock_provider = _make_provider_mock(output)
        mock_prompt, _ = _make_prompt_mock(output)
        with (
            patch("agents.nodes.assess.get_provider", return_value=mock_provider),
            patch("agents.nodes.assess.assessment_prompt", mock_prompt),
        ):
            await assess_node(_base_state())  # type: ignore[arg-type]

        mock_llm = mock_provider.get_llm.return_value
        mock_llm.with_structured_output.assert_called_once_with(AssessmentOutput)
