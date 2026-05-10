"""
Tests for Commit 10 — langgraph-graph-assembly.

Coverage targets (6 spec gates):

Gate 1: build_graph() returns a CompiledStateGraph.
Gate 2: Graph topology — retrieve_node runs before generate_node.
        Confirmed by intercepting both nodes and asserting call order.
Gate 3: MemorySaver checkpointer is wired — second turn with the same
        thread_id receives prior messages in state (cross-turn persistence).
Gate 4: recursion_limit is set — graph config contains a finite recursion_limit.
Gate 5: SessionMemory removal — src/rag/memory/conversation.py does not exist;
        no SessionMemory import survives in any src/ file.
Gate 6: Circuit breaker OPEN → BM25 fallback works through the graph — retrieve_node
        can still run (returning 'bm25' source) when chroma_cb is unavailable.

Design notes:
- All tests use MemorySaver as the checkpointer (the same production checkpointer).
- retrieve_node and generate_node are patched at their module-level import sites so
  no real ChromaDB, BM25, LLM, or network calls occur.
- An async generate_node stub is used because generate_node is async in production;
  a synchronous stub would break LangGraph's async execution model.
- AgentState is a TypedDict — initial_state is constructed as a plain dict.
- asyncio_mode = "auto" in pyproject.toml makes @pytest.mark.asyncio optional,
  but it is included explicitly for clarity.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_initial_state(question: str = "What is RAG?") -> dict[str, Any]:
    """Minimal AgentState dict for graph invocation tests."""
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
        "trace_id": "test-trace-10",
        "latency_ms": 0,
        "cache_hit": "miss",
    }


def _stub_retrieve(state: dict) -> dict:
    """Synchronous retrieve_node stub — returns one synthetic document."""
    return {
        "docs": [Document(page_content="RAG = Retrieval-Augmented Generation.", metadata={})],
        "retrieval_source": "chroma",
    }


async def _stub_generate(state: dict) -> dict:
    """Async generate_node stub — returns a synthetic AIMessage."""
    return {
        "messages": [AIMessage(content="Stubbed answer.")],
        "answer": "Stubbed answer.",
    }


def _build_test_graph() -> CompiledStateGraph:
    """Build the graph with MemorySaver and stub nodes (no real LLM/DB)."""
    from agents.graph import build_graph

    with (
        patch("agents.graph.retrieve_node", side_effect=_stub_retrieve),
        patch("agents.graph.generate_node", side_effect=_stub_generate),
    ):
        checkpointer = MemorySaver()
        return build_graph(checkpointer)


# ---------------------------------------------------------------------------
# Gate 1 — build_graph() returns a CompiledStateGraph
# ---------------------------------------------------------------------------

class TestGate1BuildGraphReturnType:
    """build_graph() must return a CompiledStateGraph instance."""

    def test_build_graph_returns_compiled_state_graph(self) -> None:
        """Return value is a CompiledStateGraph, not bare Any."""
        graph = _build_test_graph()
        assert isinstance(graph, CompiledStateGraph), (
            f"Expected CompiledStateGraph, got {type(graph)}"
        )

    def test_build_graph_accepts_memory_saver(self) -> None:
        """build_graph() accepts a MemorySaver without raising."""
        try:
            _build_test_graph()
        except Exception as exc:
            pytest.fail(f"build_graph() raised with MemorySaver: {exc}")


# ---------------------------------------------------------------------------
# Gate 2 — Graph topology: retrieve runs before generate
# ---------------------------------------------------------------------------

class TestGate2GraphTopology:
    """retrieve_node must execute before generate_node in every invocation."""

    @pytest.mark.asyncio
    async def test_retrieve_executes_before_generate(self) -> None:
        """Call order: retrieve_node is called, then generate_node."""
        call_order: list[str] = []

        def ordered_retrieve(state: dict) -> dict:
            call_order.append("retrieve")
            return {
                "docs": [Document(page_content="context", metadata={})],
                "retrieval_source": "chroma",
            }

        async def ordered_generate(state: dict) -> dict:
            call_order.append("generate")
            return {
                "messages": [AIMessage(content="answer")],
                "answer": "answer",
            }

        from agents.graph import build_graph

        with (
            patch("agents.graph.retrieve_node", side_effect=ordered_retrieve),
            patch("agents.graph.generate_node", side_effect=ordered_generate),
        ):
            graph = build_graph(MemorySaver())
            config = {"configurable": {"thread_id": "topology-test"}}
            await graph.ainvoke(_make_initial_state(), config=config)

        assert call_order == ["retrieve", "generate"], (
            f"Expected ['retrieve', 'generate'], got {call_order}"
        )

    @pytest.mark.asyncio
    async def test_generate_receives_docs_from_retrieve(self) -> None:
        """generate_node receives the docs that retrieve_node returned."""
        captured_state: dict = {}
        expected_doc = Document(page_content="retrieved context", metadata={})

        def retrieve_with_doc(state: dict) -> dict:
            return {"docs": [expected_doc], "retrieval_source": "chroma"}

        async def capture_generate(state: dict) -> dict:
            captured_state.update(state)
            return {"messages": [AIMessage(content="ok")], "answer": "ok"}

        from agents.graph import build_graph

        with (
            patch("agents.graph.retrieve_node", side_effect=retrieve_with_doc),
            patch("agents.graph.generate_node", side_effect=capture_generate),
        ):
            graph = build_graph(MemorySaver())
            config = {"configurable": {"thread_id": "topology-docs-test"}}
            await graph.ainvoke(_make_initial_state(), config=config)

        assert len(captured_state.get("docs", [])) == 1
        assert captured_state["docs"][0].page_content == "retrieved context"


# ---------------------------------------------------------------------------
# Gate 3 — MemorySaver checkpointer: cross-turn persistence
# ---------------------------------------------------------------------------

class TestGate3CrossTurnPersistence:
    """Second turn with the same thread_id must receive prior messages in state."""

    @pytest.mark.asyncio
    async def test_second_turn_messages_contain_prior_history(self) -> None:
        """After two turns with the same thread_id, state has HumanMessage + AIMessage + HumanMessage."""
        captured_states: list[dict] = []

        def retrieve_stub(state: dict) -> dict:
            return {"docs": [], "retrieval_source": "bm25"}

        async def generate_capture(state: dict) -> dict:
            captured_states.append(dict(state))
            return {"messages": [AIMessage(content="answer")], "answer": "answer"}

        from agents.graph import build_graph

        with (
            patch("agents.graph.retrieve_node", side_effect=retrieve_stub),
            patch("agents.graph.generate_node", side_effect=generate_capture),
        ):
            graph = build_graph(MemorySaver())
            config = {"configurable": {"thread_id": "persistence-test"}}

            # Turn 1
            await graph.ainvoke(_make_initial_state("first question"), config=config)
            # Turn 2 — same thread_id
            await graph.ainvoke(_make_initial_state("second question"), config=config)

        # State on the second turn must include messages from both turns
        second_state = captured_states[1]
        messages = second_state["messages"]

        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]

        assert len(human_messages) >= 2, (
            f"Expected at least 2 HumanMessages in second turn, got {len(human_messages)}"
        )
        assert len(ai_messages) >= 1, (
            f"Expected at least 1 AIMessage in second turn, got {len(ai_messages)}"
        )

    @pytest.mark.asyncio
    async def test_different_thread_ids_are_independent(self) -> None:
        """Two sessions with different thread_ids do not share state."""
        captured_states: list[dict] = []

        def retrieve_stub(state: dict) -> dict:
            return {"docs": [], "retrieval_source": "bm25"}

        async def generate_capture(state: dict) -> dict:
            captured_states.append(dict(state))
            return {"messages": [AIMessage(content="answer")], "answer": "answer"}

        from agents.graph import build_graph

        checkpointer = MemorySaver()

        with (
            patch("agents.graph.retrieve_node", side_effect=retrieve_stub),
            patch("agents.graph.generate_node", side_effect=generate_capture),
        ):
            graph = build_graph(checkpointer)

            # Session A
            await graph.ainvoke(
                _make_initial_state("session A question"),
                config={"configurable": {"thread_id": "session-A"}},
            )
            # Session B — different thread_id, should have no history from session A
            await graph.ainvoke(
                _make_initial_state("session B question"),
                config={"configurable": {"thread_id": "session-B"}},
            )

        session_b_state = captured_states[1]
        human_messages = [m for m in session_b_state["messages"] if isinstance(m, HumanMessage)]
        # Session B has only its own HumanMessage — no bleed from session A
        assert len(human_messages) == 1, (
            f"Session B should have only 1 HumanMessage, got {len(human_messages)}"
        )


# ---------------------------------------------------------------------------
# Gate 4 — recursion_limit is set
# ---------------------------------------------------------------------------

class TestGate4RecursionLimit:
    """The compiled graph must have a finite recursion_limit in its config."""

    def test_compiled_graph_has_recursion_limit_in_config(self) -> None:
        """graph.config contains a 'recursion_limit' key with a positive int."""
        graph = _build_test_graph()
        # CompiledStateGraph exposes its resolved config
        config = graph.config if hasattr(graph, "config") else {}
        recursion_limit = config.get("recursion_limit")
        assert recursion_limit is not None, (
            "CompiledStateGraph.config must contain 'recursion_limit'"
        )
        assert isinstance(recursion_limit, int), (
            f"recursion_limit must be int, got {type(recursion_limit)}"
        )
        assert recursion_limit > 0, (
            f"recursion_limit must be positive, got {recursion_limit}"
        )


# ---------------------------------------------------------------------------
# Gate 5 — SessionMemory removal verification
# ---------------------------------------------------------------------------

class TestGate5SessionMemoryRemoved:
    """conversation.py must not exist; no SessionMemory import survives in src/."""

    def test_conversation_module_file_does_not_exist(self) -> None:
        """src/rag/memory/conversation.py must be absent from the filesystem."""
        path = Path(__file__).parent.parent / "src" / "rag" / "memory" / "conversation.py"
        assert not path.exists(), (
            f"conversation.py still exists at {path}; it must be deleted in Commit 10"
        )

    def test_session_memory_is_not_importable(self) -> None:
        """Importing rag.memory.conversation must raise ModuleNotFoundError."""
        with pytest.raises((ModuleNotFoundError, ImportError)):
            importlib.import_module("rag.memory.conversation")

    def test_no_session_memory_import_in_chain(self) -> None:
        """rag.chain must not import or reference SessionMemory."""
        import rag.chain as chain_module
        assert not hasattr(chain_module, "SessionMemory"), (
            "chain.py must not expose SessionMemory after Commit 10"
        )
        assert not hasattr(chain_module, "session_memory"), (
            "chain.py must not expose session_memory instance after Commit 10"
        )

    def test_no_run_rag_pipeline_in_chain(self) -> None:
        """run_rag_pipeline() must not exist in rag.chain after Commit 10."""
        import rag.chain as chain_module
        assert not hasattr(chain_module, "run_rag_pipeline"), (
            "chain.py must not expose run_rag_pipeline() after Commit 10 — "
            "the graph replaces it"
        )


# ---------------------------------------------------------------------------
# Gate 6 — Circuit breaker OPEN: BM25 fallback works through the graph
# ---------------------------------------------------------------------------

class TestGate6CircuitBreakerFallback:
    """When chroma_cb is unavailable, retrieve_node falls back to BM25 without raising."""

    @pytest.mark.asyncio
    async def test_bm25_fallback_when_chroma_unavailable(self) -> None:
        """Graph runs end-to-end with retrieval_source='bm25' when CB is OPEN."""
        from agents.graph import build_graph
        from agents.nodes.retrieve import retrieve_node as real_retrieve_node

        async def generate_stub(state: dict) -> dict:
            return {"messages": [AIMessage(content="fallback answer")], "answer": "fallback answer"}

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=[]),
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
            patch("agents.graph.generate_node", side_effect=generate_stub),
        ):
            mock_cb.is_available.return_value = False  # CB is OPEN → BM25

            graph = build_graph(MemorySaver())
            config = {"configurable": {"thread_id": "cb-fallback-test"}}
            result = await graph.ainvoke(_make_initial_state(), config=config)

        assert result.get("retrieval_source") == "bm25", (
            f"Expected 'bm25' retrieval_source, got {result.get('retrieval_source')!r}"
        )
        assert result.get("answer") == "fallback answer"
