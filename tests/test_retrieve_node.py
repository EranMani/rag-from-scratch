"""
Tests for Commit 08 — langgraph-retrieve-node.

Coverage targets (3 spec gates):

Gate 1: Node receives an AgentState with a question and returns state with
        docs populated (list[Document], at least 1 item when retriever returns results).
Gate 2: retrieval_source is set to 'chroma' or 'bm25' on every invocation.
        Sub-cases:
          2a — chroma circuit breaker available before and after → 'chroma'
          2b — chroma circuit breaker NOT available before call → 'bm25'
          2c — chroma circuit breaker available before but trips during call → 'bm25'
Gate 3: Node does not raise on an empty question — returns empty docs list.

Design notes:
- retrieve() is patched at the agents.nodes.retrieve import site so the node
  never touches ChromaDB, BM25, or any app infrastructure.
- chroma_cb.is_available() is patched to control which retrieval path appears
  to have been taken, allowing deterministic source-label assertions.
- AgentState is a TypedDict — we construct it as a plain dict for test inputs.
  Only `question` is strictly required for retrieve_node; other fields are set
  to sentinel values to satisfy the TypedDict contract.
- The node return dict is checked for exact keys: only 'docs' and 'retrieval_source'
  should be present (domain boundary enforcement).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(question: str) -> dict[str, Any]:
    """Construct a minimal AgentState dict for retrieve_node testing."""
    return {
        "messages": [],
        "question": question,
        "user_id": None,
        "docs": [],
        "retrieval_source": "",
        "answer": "",
        "user_level": "beginner",
        "topic_scores_delta": {},
        "identified_gaps": [],
        "assessment_error": False,
        "trace_id": "test-trace",
        "latency_ms": 0,
        "cache_hit": "miss",
    }


def _make_docs(n: int) -> list[Document]:
    """Return a list of n dummy Document objects."""
    return [Document(page_content=f"chunk {i}", metadata={"source": "test"}) for i in range(n)]


# ---------------------------------------------------------------------------
# Gate 1 — Node returns docs populated when retriever returns results
# ---------------------------------------------------------------------------

class TestGate1DocsPopulated:
    """Node receives AgentState with a question and returns docs populated."""

    def test_docs_returned_as_list_of_documents(self) -> None:
        """Return value contains 'docs' key with list[Document]."""
        fake_docs = _make_docs(3)
        state = _make_state("What is RAG?")

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=fake_docs),
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
        ):
            mock_cb.is_available.return_value = True

            from agents.nodes.retrieve import retrieve_node
            result = retrieve_node(state)

        assert "docs" in result
        assert isinstance(result["docs"], list)
        assert len(result["docs"]) == 3
        for doc in result["docs"]:
            assert isinstance(doc, Document)

    def test_question_passed_to_retriever(self) -> None:
        """Node passes the state question directly to retrieve()."""
        fake_docs = _make_docs(2)
        state = _make_state("How does chunking work?")

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=fake_docs) as mock_retrieve,
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
        ):
            mock_cb.is_available.return_value = True

            from agents.nodes.retrieve import retrieve_node
            retrieve_node(state)

        mock_retrieve.assert_called_once_with("How does chunking work?")

    def test_return_dict_contains_exactly_docs_and_retrieval_source(self) -> None:
        """Node returns only 'docs' and 'retrieval_source' — no extra keys."""
        fake_docs = _make_docs(1)
        state = _make_state("What is a vector store?")

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=fake_docs),
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
        ):
            mock_cb.is_available.return_value = True

            from agents.nodes.retrieve import retrieve_node
            result = retrieve_node(state)

        assert set(result.keys()) == {"docs", "retrieval_source"}


# ---------------------------------------------------------------------------
# Gate 2 — retrieval_source is 'chroma' or 'bm25' on every invocation
# ---------------------------------------------------------------------------

class TestGate2RetrievalSource:
    """retrieval_source is always exactly 'chroma' or 'bm25'."""

    def test_2a_chroma_available_before_and_after_yields_chroma(self) -> None:
        """CB available both sides → Chroma succeeded → source is 'chroma'."""
        state = _make_state("Tell me about embeddings")

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=_make_docs(2)),
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
        ):
            # Available before the call, available after the call
            mock_cb.is_available.return_value = True

            from agents.nodes.retrieve import retrieve_node
            result = retrieve_node(state)

        assert result["retrieval_source"] == "chroma"

    def test_2b_chroma_not_available_before_yields_bm25(self) -> None:
        """CB not available before the call → BM25 ran directly → source is 'bm25'."""
        state = _make_state("Tell me about embeddings")

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=_make_docs(1)),
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
        ):
            # Not available before OR after
            mock_cb.is_available.return_value = False

            from agents.nodes.retrieve import retrieve_node
            result = retrieve_node(state)

        assert result["retrieval_source"] == "bm25"

    def test_2c_chroma_trips_during_call_yields_bm25(self) -> None:
        """CB available before but OPEN after (tripped mid-call) → source is 'bm25'."""
        state = _make_state("Tell me about embeddings")

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=_make_docs(1)),
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
        ):
            # Available before, not available after (CB tripped during retrieve)
            mock_cb.is_available.side_effect = [True, False]

            from agents.nodes.retrieve import retrieve_node
            result = retrieve_node(state)

        assert result["retrieval_source"] == "bm25"

    def test_retrieval_source_is_string(self) -> None:
        """retrieval_source is always a str, not None or other type."""
        state = _make_state("question")

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=[]),
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
        ):
            mock_cb.is_available.return_value = True

            from agents.nodes.retrieve import retrieve_node
            result = retrieve_node(state)

        assert isinstance(result["retrieval_source"], str)
        assert result["retrieval_source"] in ("chroma", "bm25")


# ---------------------------------------------------------------------------
# Gate 3 — Empty question does not raise; returns empty docs list
# ---------------------------------------------------------------------------

class TestGate3EmptyQuestion:
    """Node does not raise on empty question string; returns empty docs."""

    def test_empty_question_returns_empty_docs(self) -> None:
        """retrieve() called with '' → node returns empty list without raising."""
        state = _make_state("")

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=[]),
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
        ):
            mock_cb.is_available.return_value = True

            from agents.nodes.retrieve import retrieve_node
            result = retrieve_node(state)

        assert result["docs"] == []
        assert isinstance(result["docs"], list)

    def test_empty_question_passes_empty_string_to_retriever(self) -> None:
        """Empty question is forwarded verbatim to retrieve(); node does not filter it."""
        state = _make_state("")

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=[]) as mock_retrieve,
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
        ):
            mock_cb.is_available.return_value = True

            from agents.nodes.retrieve import retrieve_node
            retrieve_node(state)

        mock_retrieve.assert_called_once_with("")

    def test_empty_question_still_sets_retrieval_source(self) -> None:
        """retrieval_source is still set even when question is empty."""
        state = _make_state("")

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=[]),
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
        ):
            mock_cb.is_available.return_value = False

            from agents.nodes.retrieve import retrieve_node
            result = retrieve_node(state)

        assert result["retrieval_source"] == "bm25"

    def test_empty_question_does_not_raise(self) -> None:
        """Explicit no-exception assertion for the spec gate condition."""
        state = _make_state("")

        with (
            patch("agents.nodes.retrieve.retrieve", return_value=[]),
            patch("agents.nodes.retrieve.chroma_cb") as mock_cb,
        ):
            mock_cb.is_available.return_value = True

            from agents.nodes.retrieve import retrieve_node
            try:
                retrieve_node(state)
            except Exception as exc:
                pytest.fail(f"retrieve_node raised on empty question: {exc}")
