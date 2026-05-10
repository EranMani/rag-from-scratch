"""
Tests for Commit 12 — langgraph-assessment-scaffold.

Coverage targets (spec gates):

Gate 1: assess_node stub sets assessment_error=False and returns empty AssessmentOutput.
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
Gate 6: Existing 14 smoke tests (test_graph_smoke.py) still pass with the
        updated graph topology (all smoke patches now also stub assess_node).

Design notes:
- assess_node is tested directly (unit) and via full graph invocation (integration).
- For conditional-edge tests the graph is patched so assess_node sets
  assessment_error=True, and we assert that update_profile_node still runs.
- _route_after_assess is imported and tested as a pure function — no graph
  needed for the unit-level routing test.
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
from agents.state import AgentState, AssessmentOutput


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
# Gate 1 — assess_node stub returns empty AssessmentOutput, assessment_error=False
# ---------------------------------------------------------------------------

class TestGate1AssessNodeStub:
    """The stub assess_node must return deterministic empty output."""

    @pytest.mark.asyncio
    async def test_returns_assessment_error_false(self) -> None:
        """assess_node returns assessment_error=False when no exception occurs."""
        result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert result["assessment_error"] is False, (
            f"assessment_error must be False for stub, got {result['assessment_error']!r}"
        )

    @pytest.mark.asyncio
    async def test_returns_empty_topic_scores_delta(self) -> None:
        """assess_node stub returns an empty topic_scores_delta dict."""
        result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert isinstance(result["topic_scores_delta"], dict), (
            f"topic_scores_delta must be dict, got {type(result['topic_scores_delta'])}"
        )
        assert result["topic_scores_delta"] == {}, (
            f"Stub must return empty topic_scores_delta, got {result['topic_scores_delta']!r}"
        )

    @pytest.mark.asyncio
    async def test_returns_empty_identified_gaps(self) -> None:
        """assess_node stub returns an empty identified_gaps list."""
        result = await assess_node(_base_state())  # type: ignore[arg-type]
        assert isinstance(result["identified_gaps"], list), (
            f"identified_gaps must be list, got {type(result['identified_gaps'])}"
        )
        assert result["identified_gaps"] == [], (
            f"Stub must return empty identified_gaps, got {result['identified_gaps']!r}"
        )

    @pytest.mark.asyncio
    async def test_output_types_are_correct(self) -> None:
        """assess_node output types: dict, list, bool."""
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
        result = await assess_node(_base_state())  # type: ignore[arg-type]
        foreign: set[str] = set(result.keys()) & self._FORBIDDEN_KEYS
        assert not foreign, (
            f"assess_node must not write to foreign state keys: {foreign}"
        )

    @pytest.mark.asyncio
    async def test_all_declared_keys_present(self) -> None:
        """assess_node return dict must contain all three declared output keys."""
        result = await assess_node(_base_state())  # type: ignore[arg-type]
        missing: set[str] = self._DECLARED_OUTPUT_KEYS - set(result.keys())
        assert not missing, (
            f"assess_node output is missing declared keys: {missing}"
        )

    @pytest.mark.asyncio
    async def test_output_has_exactly_declared_keys(self) -> None:
        """assess_node return dict contains only the three declared output keys."""
        result = await assess_node(_base_state())  # type: ignore[arg-type]
        extra: set[str] = set(result.keys()) - self._DECLARED_OUTPUT_KEYS
        assert not extra, (
            f"assess_node output has extra keys beyond declared contract: {extra}"
        )


# ---------------------------------------------------------------------------
# Gate 3 — assess_node fallback on internal exception
# ---------------------------------------------------------------------------

class TestGate3FallbackOnException:
    """When assess_node raises internally, it catches and returns assessment_error=True."""

    @pytest.mark.asyncio
    async def test_exception_sets_assessment_error_true(self) -> None:
        """If an exception occurs inside assess_node, assessment_error is True."""
        # We patch AssessmentOutput so its constructor raises to simulate an LLM
        # parse failure — the exact mechanism that will trigger the fallback in Commit 13.
        with patch(
            "agents.nodes.assess.AssessmentOutput",
            side_effect=ValueError("Simulated LLM parse failure"),
        ):
            result = await assess_node(_base_state())  # type: ignore[arg-type]

        assert result["assessment_error"] is True, (
            f"assessment_error must be True on exception, got {result['assessment_error']!r}"
        )

    @pytest.mark.asyncio
    async def test_exception_returns_empty_deltas(self) -> None:
        """On exception, topic_scores_delta and identified_gaps are both empty."""
        with patch(
            "agents.nodes.assess.AssessmentOutput",
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
            "agents.nodes.assess.AssessmentOutput",
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
    and complete ainvoke() without raising."""

    @pytest.mark.asyncio
    async def test_graph_compiles_without_error(self) -> None:
        """build_graph() with 4-node topology returns a CompiledStateGraph."""
        from langgraph.graph.state import CompiledStateGraph

        from agents.graph import build_graph

        mock_provider = MagicMock()
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Test answer."))
        mock_provider.get_llm.return_value = mock_llm

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

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
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

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
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

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "assess-gate-5c"}}
            result = await graph.ainvoke(_make_full_initial_state(), config=config)

        assert "assessment_error" in result, "Final state must contain 'assessment_error'"
        assert "topic_scores_delta" in result, "Final state must contain 'topic_scores_delta'"
        assert "identified_gaps" in result, "Final state must contain 'identified_gaps'"
        assert result["assessment_error"] is False, (
            f"Stub assess_node sets assessment_error=False, got {result['assessment_error']!r}"
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

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
            patch("agents.graph.generate_node", side_effect=_stub_generate),
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
