"""
Tests for Commit 11 — langgraph-graph-smoke-test.

End-to-end integration smoke tests for the fully assembled LangGraph graph.
These tests exercise the complete graph invocation path without any live
external services (no OpenAI, no ChromaDB, no BM25 corpus).

Coverage targets (spec gates):

Gate 1: Graph accepts a valid AgentState input and returns a state dict.
Gate 2: 'answer' in the returned state is a non-empty string.
Gate 3: 'docs' in the returned state is a list (may be empty in test environment).
Gate 4: 'retrieval_source' is exactly 'chroma' or 'bm25'.
Gate 5: Conversation history threading — a second invocation with the same
        session_id receives non-empty history (MemorySaver cross-turn persistence).

Design notes:
- retrieve_node is patched at its import site in agents.graph so no real
  ChromaDB, BM25, or network calls occur.
- get_provider() is patched at its import site in agents.nodes.generate so no
  real LLM or API key is required.  The mock provider's get_llm() returns a
  mock LLM whose ainvoke() returns a synthetic AIMessage.
- Both patches are applied before build_graph() is called so the compiled graph
  captures the stubbed functions. The graph and its checkpointer are created once
  per test that requires threading; sharing the same MemorySaver instance across
  two ainvoke() calls is the mechanism that exercises cross-turn persistence.
- asyncio_mode = "auto" in pyproject.toml makes @pytest.mark.asyncio optional,
  but it is included explicitly for clarity.
- AgentState is a TypedDict — initial_state is constructed as a plain dict.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_initial_state(question: str = "What is RAG?") -> dict[str, Any]:
    """Minimal AgentState dict for full graph invocation."""
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
        "trace_id": "test-trace-11",
        "latency_ms": 0,
        "cache_hit": "miss",
    }


def _make_mock_provider(ai_response: str = "Stubbed smoke-test answer.") -> MagicMock:
    """Return a mock provider whose get_llm().ainvoke() returns a synthetic AIMessage.

    Mirrors the pattern used in test_generate_node.py so the mock contract
    is consistent across the test suite.
    """
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content=ai_response))

    mock_provider = MagicMock()
    mock_provider.get_llm.return_value = mock_llm

    return mock_provider


def _stub_retrieve_chroma(state: dict[str, Any]) -> dict[str, Any]:
    """retrieve_node stub — returns one synthetic document via chroma path."""
    return {
        "docs": [Document(page_content="RAG = Retrieval-Augmented Generation.", metadata={})],
        "retrieval_source": "chroma",
    }


async def _stub_generate(state: dict[str, Any]) -> dict[str, Any]:
    """Async generate_node stub — bypasses the LLM entirely for topology tests."""
    return {
        "messages": [AIMessage(content="Stubbed answer.")],
        "answer": "Stubbed answer.",
    }


# ---------------------------------------------------------------------------
# Gate 1 — Graph accepts valid AgentState input and returns a state dict
# ---------------------------------------------------------------------------

class TestGate1GraphReturnsStateDict:
    """ainvoke() on a fully-assembled graph must return a mapping."""

    @pytest.mark.asyncio
    async def test_ainvoke_returns_dict(self) -> None:
        """Graph ainvoke() returns a dict (state mapping), not None or a raw value."""
        from agents.graph import build_graph

        mock_provider = _make_mock_provider()

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve_chroma),
            patch("agents.nodes.generate.get_provider", return_value=mock_provider),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-gate-1a"}}
            result = await graph.ainvoke(_make_initial_state(), config=config)

        assert isinstance(result, dict), (
            f"Graph ainvoke() must return a dict, got {type(result)}"
        )

    @pytest.mark.asyncio
    async def test_ainvoke_does_not_raise(self) -> None:
        """Graph ainvoke() with a valid AgentState does not raise any exception."""
        from agents.graph import build_graph

        mock_provider = _make_mock_provider()

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve_chroma),
            patch("agents.nodes.generate.get_provider", return_value=mock_provider),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-gate-1b"}}
            try:
                await graph.ainvoke(_make_initial_state(), config=config)
            except Exception as exc:
                pytest.fail(f"Graph ainvoke() raised unexpectedly: {exc}")


# ---------------------------------------------------------------------------
# Gate 2 — 'answer' is a non-empty string
# ---------------------------------------------------------------------------

class TestGate2AnswerNonEmpty:
    """The 'answer' field in the returned state must be a non-empty string."""

    @pytest.mark.asyncio
    async def test_answer_is_string(self) -> None:
        """Returned state['answer'] is a str instance."""
        from agents.graph import build_graph

        mock_provider = _make_mock_provider("This is the answer.")

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve_chroma),
            patch("agents.nodes.generate.get_provider", return_value=mock_provider),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-gate-2a"}}
            result = await graph.ainvoke(_make_initial_state(), config=config)

        assert isinstance(result.get("answer"), str), (
            f"state['answer'] must be str, got {type(result.get('answer'))}"
        )

    @pytest.mark.asyncio
    async def test_answer_is_non_empty(self) -> None:
        """Returned state['answer'] is a non-empty string (not '' or whitespace-only)."""
        from agents.graph import build_graph

        mock_provider = _make_mock_provider("Non-empty answer from smoke test.")

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve_chroma),
            patch("agents.nodes.generate.get_provider", return_value=mock_provider),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-gate-2b"}}
            result = await graph.ainvoke(_make_initial_state(), config=config)

        answer: str = result.get("answer", "")
        assert answer.strip(), (
            "state['answer'] must be a non-empty, non-whitespace string after graph execution"
        )

    @pytest.mark.asyncio
    async def test_answer_matches_llm_response(self) -> None:
        """state['answer'] matches the content returned by the mock LLM."""
        from agents.graph import build_graph

        expected_answer = "Deterministic smoke-test response."
        mock_provider = _make_mock_provider(expected_answer)

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve_chroma),
            patch("agents.nodes.generate.get_provider", return_value=mock_provider),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-gate-2c"}}
            result = await graph.ainvoke(_make_initial_state(), config=config)

        assert result.get("answer") == expected_answer, (
            f"Expected answer {expected_answer!r}, got {result.get('answer')!r}"
        )


# ---------------------------------------------------------------------------
# Gate 3 — 'docs' is a list (may be empty in test environment)
# ---------------------------------------------------------------------------

class TestGate3DocsIsList:
    """The 'docs' field in the returned state must be a list."""

    @pytest.mark.asyncio
    async def test_docs_is_list(self) -> None:
        """state['docs'] is a list instance."""
        from agents.graph import build_graph

        mock_provider = _make_mock_provider()

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve_chroma),
            patch("agents.nodes.generate.get_provider", return_value=mock_provider),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-gate-3a"}}
            result = await graph.ainvoke(_make_initial_state(), config=config)

        assert isinstance(result.get("docs"), list), (
            f"state['docs'] must be list, got {type(result.get('docs'))}"
        )

    @pytest.mark.asyncio
    async def test_docs_list_with_documents(self) -> None:
        """When retrieve stub returns Documents, state['docs'] contains Document instances."""
        from agents.graph import build_graph

        mock_provider = _make_mock_provider()

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve_chroma),
            patch("agents.nodes.generate.get_provider", return_value=mock_provider),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-gate-3b"}}
            result = await graph.ainvoke(_make_initial_state(), config=config)

        docs: list[Document] = result.get("docs", [])
        assert len(docs) >= 1, "Stub returns one Document; state['docs'] should have at least one"
        assert all(isinstance(d, Document) for d in docs), (
            "All elements of state['docs'] must be Document instances"
        )

    @pytest.mark.asyncio
    async def test_docs_is_list_even_when_empty(self) -> None:
        """state['docs'] is still a list when retrieve stub returns an empty list."""
        from agents.graph import build_graph

        mock_provider = _make_mock_provider()

        def stub_retrieve_empty(state: dict[str, Any]) -> dict[str, Any]:
            return {"docs": [], "retrieval_source": "bm25"}

        with (
            patch("agents.graph.retrieve_node", side_effect=stub_retrieve_empty),
            patch("agents.nodes.generate.get_provider", return_value=mock_provider),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-gate-3c"}}
            result = await graph.ainvoke(_make_initial_state(), config=config)

        assert isinstance(result.get("docs"), list), (
            "state['docs'] must be a list even when empty"
        )
        assert result.get("docs") == [], "Stub returned empty list; state['docs'] must be []"


# ---------------------------------------------------------------------------
# Gate 4 — 'retrieval_source' is exactly 'chroma' or 'bm25'
# ---------------------------------------------------------------------------

class TestGate4RetrievalSource:
    """The 'retrieval_source' field must be exactly 'chroma' or 'bm25'."""

    @pytest.mark.asyncio
    async def test_retrieval_source_is_chroma(self) -> None:
        """state['retrieval_source'] is 'chroma' when retrieve stub signals chroma path."""
        from agents.graph import build_graph

        mock_provider = _make_mock_provider()

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve_chroma),
            patch("agents.nodes.generate.get_provider", return_value=mock_provider),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-gate-4a"}}
            result = await graph.ainvoke(_make_initial_state(), config=config)

        assert result.get("retrieval_source") in {"chroma", "bm25"}, (
            f"retrieval_source must be 'chroma' or 'bm25', got {result.get('retrieval_source')!r}"
        )
        assert result.get("retrieval_source") == "chroma", (
            f"Expected 'chroma' from chroma stub, got {result.get('retrieval_source')!r}"
        )

    @pytest.mark.asyncio
    async def test_retrieval_source_is_bm25(self) -> None:
        """state['retrieval_source'] is 'bm25' when retrieve stub signals bm25 fallback."""
        from agents.graph import build_graph

        mock_provider = _make_mock_provider()

        def stub_retrieve_bm25(state: dict[str, Any]) -> dict[str, Any]:
            return {
                "docs": [Document(page_content="BM25 fallback result.", metadata={})],
                "retrieval_source": "bm25",
            }

        with (
            patch("agents.graph.retrieve_node", side_effect=stub_retrieve_bm25),
            patch("agents.nodes.generate.get_provider", return_value=mock_provider),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-gate-4b"}}
            result = await graph.ainvoke(_make_initial_state(), config=config)

        assert result.get("retrieval_source") in {"chroma", "bm25"}, (
            f"retrieval_source must be 'chroma' or 'bm25', got {result.get('retrieval_source')!r}"
        )
        assert result.get("retrieval_source") == "bm25", (
            f"Expected 'bm25' from BM25 stub, got {result.get('retrieval_source')!r}"
        )

    @pytest.mark.asyncio
    async def test_retrieval_source_membership(self) -> None:
        """retrieval_source is always a member of the valid set {'chroma', 'bm25'}."""
        from agents.graph import build_graph

        mock_provider = _make_mock_provider()

        with (
            patch("agents.graph.retrieve_node", side_effect=_stub_retrieve_chroma),
            patch("agents.nodes.generate.get_provider", return_value=mock_provider),
        ):
            graph = build_graph(MemorySaver())
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-gate-4c"}}
            result = await graph.ainvoke(_make_initial_state(), config=config)

        assert result.get("retrieval_source") in {"chroma", "bm25"}, (
            f"retrieval_source {result.get('retrieval_source')!r} not in {{'chroma', 'bm25'}}"
        )


# ---------------------------------------------------------------------------
# Gate 5 — Conversation history threading via MemorySaver
# ---------------------------------------------------------------------------

class TestGate5ConversationHistoryThreading:
    """Second invocation with the same session_id must have non-empty conversation history.

    The MemorySaver checkpointer keyed by thread_id accumulates message history
    across turns.  The add_messages reducer on AgentState.messages handles
    appending; the test verifies that the second turn actually receives prior
    messages in state (i.e., the checkpointer was populated and replayed correctly).
    """

    @pytest.mark.asyncio
    async def test_second_turn_has_non_empty_history(self) -> None:
        """After two turns with the same thread_id, the second turn sees prior messages.

        Implementation: a shared MemorySaver and graph instance are used for both
        turns.  A capture stub records the state received by generate_node on each
        turn.  After turn 2, state['messages'] must contain messages from turn 1
        — demonstrating that MemorySaver replayed the checkpoint correctly.
        """
        from agents.graph import build_graph

        captured_states: list[dict[str, Any]] = []

        def stub_retrieve(state: dict[str, Any]) -> dict[str, Any]:
            return {"docs": [], "retrieval_source": "bm25"}

        mock_llm = MagicMock()

        async def capture_ainvoke(messages: list) -> AIMessage:
            return AIMessage(content="History threading answer.")

        mock_llm.ainvoke = capture_ainvoke

        # We need to capture what generate_node sees in state["messages"] on
        # each turn.  We patch get_provider at the import site in nodes.generate
        # and also insert a wrapper to capture the state via retrieve_node's
        # returned state that will flow into generate_node.
        # Approach: patch generate_node itself at the graph level with a capture stub
        # that records state["messages"] before returning the expected output.

        async def capture_generate(state: dict[str, Any]) -> dict[str, Any]:
            captured_states.append({"messages": list(state["messages"])})
            return {
                "messages": [AIMessage(content="History threading answer.")],
                "answer": "History threading answer.",
            }

        shared_checkpointer = MemorySaver()

        with (
            patch("agents.graph.retrieve_node", side_effect=stub_retrieve),
            patch("agents.graph.generate_node", side_effect=capture_generate),
        ):
            graph = build_graph(shared_checkpointer)

            session_config: dict[str, Any] = {
                "configurable": {"thread_id": "smoke-threading-test"}
            }

            # Turn 1
            await graph.ainvoke(
                _make_initial_state("first question"),
                config=session_config,
            )
            # Turn 2 — same thread_id; MemorySaver must replay turn 1 checkpoint
            await graph.ainvoke(
                _make_initial_state("second question"),
                config=session_config,
            )

        assert len(captured_states) == 2, (
            f"Expected exactly 2 generate_node invocations, got {len(captured_states)}"
        )

        second_turn_messages: list = captured_states[1]["messages"]
        assert len(second_turn_messages) > 1, (
            "Second turn state['messages'] must contain more than one message "
            "(prior turn messages must be replayed from MemorySaver checkpoint). "
            f"Got {len(second_turn_messages)} message(s)."
        )

    @pytest.mark.asyncio
    async def test_second_turn_history_contains_prior_human_message(self) -> None:
        """Turn 1's HumanMessage appears in turn 2's state['messages']."""
        from agents.graph import build_graph

        captured_states: list[dict[str, Any]] = []

        def stub_retrieve(state: dict[str, Any]) -> dict[str, Any]:
            return {"docs": [], "retrieval_source": "chroma"}

        async def capture_generate(state: dict[str, Any]) -> dict[str, Any]:
            captured_states.append({"messages": list(state["messages"])})
            return {
                "messages": [AIMessage(content="Turn answer.")],
                "answer": "Turn answer.",
            }

        shared_checkpointer = MemorySaver()

        with (
            patch("agents.graph.retrieve_node", side_effect=stub_retrieve),
            patch("agents.graph.generate_node", side_effect=capture_generate),
        ):
            graph = build_graph(shared_checkpointer)
            config: dict[str, Any] = {"configurable": {"thread_id": "smoke-history-content-test"}}

            await graph.ainvoke(_make_initial_state("first question"), config=config)
            await graph.ainvoke(_make_initial_state("second question"), config=config)

        second_turn_messages: list = captured_states[1]["messages"]
        human_messages: list[HumanMessage] = [
            m for m in second_turn_messages if isinstance(m, HumanMessage)
        ]
        ai_messages: list[AIMessage] = [
            m for m in second_turn_messages if isinstance(m, AIMessage)
        ]

        assert len(human_messages) >= 2, (
            f"Second turn must have at least 2 HumanMessages (turn 1 + turn 2), "
            f"got {len(human_messages)}"
        )
        assert len(ai_messages) >= 1, (
            f"Second turn must have at least 1 AIMessage (turn 1 response), "
            f"got {len(ai_messages)}"
        )

    @pytest.mark.asyncio
    async def test_different_session_ids_do_not_share_history(self) -> None:
        """Two distinct thread_ids produce independent conversation histories."""
        from agents.graph import build_graph

        captured_states: list[dict[str, Any]] = []

        def stub_retrieve(state: dict[str, Any]) -> dict[str, Any]:
            return {"docs": [], "retrieval_source": "bm25"}

        async def capture_generate(state: dict[str, Any]) -> dict[str, Any]:
            captured_states.append({"messages": list(state["messages"])})
            return {
                "messages": [AIMessage(content="Isolated answer.")],
                "answer": "Isolated answer.",
            }

        shared_checkpointer = MemorySaver()

        with (
            patch("agents.graph.retrieve_node", side_effect=stub_retrieve),
            patch("agents.graph.generate_node", side_effect=capture_generate),
        ):
            graph = build_graph(shared_checkpointer)

            # Session A — turn 1
            await graph.ainvoke(
                _make_initial_state("session A question"),
                config={"configurable": {"thread_id": "smoke-session-A"}},
            )
            # Session B — different thread_id; must not see session A's history
            await graph.ainvoke(
                _make_initial_state("session B question"),
                config={"configurable": {"thread_id": "smoke-session-B"}},
            )

        session_b_messages: list = captured_states[1]["messages"]
        human_messages: list[HumanMessage] = [
            m for m in session_b_messages if isinstance(m, HumanMessage)
        ]
        # Session B has only its own HumanMessage — no bleed from session A
        assert len(human_messages) == 1, (
            f"Session B must have exactly 1 HumanMessage (its own), "
            f"got {len(human_messages)}. Session A's history must not bleed through."
        )
