"""
Tests for Commit 09 — langgraph-generate-node.

Coverage targets (5 spec gates):

Gate 1: Node returns a dict with 'answer' (str) and 'messages' containing an AIMessage.
Gate 2: add_messages contract — the returned 'messages' list contains exactly one AIMessage
        (the reducer handles appending; the node just returns the new message).
Gate 3: First turn — state with messages=[HumanMessage("first question")], no prior history.
        Node runs without error and returns a non-empty answer.
Gate 4: Second turn — state with messages=[HumanMessage("q1"), AIMessage("a1"), HumanMessage("q2")].
        Node receives full history and returns answer.
Gate 5: get_provider() used — LLM is obtained from get_provider(), not instantiated directly.
        Mock get_provider() at the import site in the node; verify it is called.

Design notes:
- generate_node is async; asyncio_mode = "auto" in pyproject.toml means @pytest.mark.asyncio
  is optional, but it is included explicitly for clarity.
- get_provider() is patched at the import site: "agents.nodes.generate.get_provider".
  The mock returns a provider whose get_llm() returns a mock BaseChatModel. The mock
  BaseChatModel's ainvoke() is an AsyncMock that returns a synthetic AIMessage.
- No real LLM, no real API calls, no real provider initialisation occurs in any test.
- AgentState is a TypedDict — constructed as a plain dict for test inputs.
- Only the fields generate_node reads are strictly required (docs, messages, user_level).
  Remaining fields are set to sentinel values to satisfy the TypedDict contract.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(
    messages: list,
    docs: list[Document] | None = None,
    user_level: str = "beginner",
) -> dict[str, Any]:
    """Construct a minimal AgentState dict for generate_node testing."""
    return {
        "messages": messages,
        "question": messages[-1].content if messages else "",
        "user_id": None,
        "docs": docs if docs is not None else [
            Document(page_content="RAG stands for Retrieval-Augmented Generation.", metadata={}),
        ],
        "retrieval_source": "chroma",
        "answer": "",
        "user_level": user_level,
        "topic_scores_delta": {},
        "identified_gaps": [],
        "assessment_error": False,
        "trace_id": "test-trace-09",
        "latency_ms": 0,
        "cache_hit": "miss",
    }


def _make_mock_provider(ai_response: str = "This is the generated answer.") -> MagicMock:
    """Return a mock provider whose get_llm().ainvoke() returns a synthetic AIMessage."""
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content=ai_response))

    mock_provider = MagicMock()
    mock_provider.get_llm.return_value = mock_llm

    return mock_provider


# ---------------------------------------------------------------------------
# Gate 1 — Returns answer (str) and messages containing an AIMessage
# ---------------------------------------------------------------------------

class TestGate1ReturnShape:
    """Node return dict must contain 'answer' (str) and 'messages' with an AIMessage."""

    @pytest.mark.asyncio
    async def test_returns_answer_key_as_string(self) -> None:
        """Return dict contains 'answer' key whose value is a non-empty str."""
        state = _make_state([HumanMessage("What is RAG?")])
        mock_provider = _make_mock_provider("RAG is retrieval-augmented generation.")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            result = await generate_node(state)

        assert "answer" in result
        assert isinstance(result["answer"], str)
        assert result["answer"] == "RAG is retrieval-augmented generation."

    @pytest.mark.asyncio
    async def test_returns_messages_key_with_ai_message(self) -> None:
        """Return dict contains 'messages' key with at least one AIMessage."""
        state = _make_state([HumanMessage("What is RAG?")])
        mock_provider = _make_mock_provider("Some answer.")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            result = await generate_node(state)

        assert "messages" in result
        assert isinstance(result["messages"], list)
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        assert len(ai_messages) >= 1

    @pytest.mark.asyncio
    async def test_return_dict_contains_exactly_messages_and_answer(self) -> None:
        """Return dict contains exactly 'messages' and 'answer' — no extra keys."""
        state = _make_state([HumanMessage("What is a vector store?")])
        mock_provider = _make_mock_provider("A vector store holds embeddings.")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            result = await generate_node(state)

        assert set(result.keys()) == {"messages", "answer"}

    @pytest.mark.asyncio
    async def test_answer_matches_ai_message_content(self) -> None:
        """The 'answer' field matches the content of the AIMessage in 'messages'."""
        expected = "Context-grounded explanation of chunking."
        state = _make_state([HumanMessage("Explain chunking.")])
        mock_provider = _make_mock_provider(expected)

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            result = await generate_node(state)

        ai_msg = next(m for m in result["messages"] if isinstance(m, AIMessage))
        assert result["answer"] == ai_msg.content == expected


# ---------------------------------------------------------------------------
# Gate 2 — add_messages contract: returned 'messages' contains exactly one AIMessage
# ---------------------------------------------------------------------------

class TestGate2AddMessagesContract:
    """The returned 'messages' list contains exactly one AIMessage (the new response).

    The add_messages reducer in AgentState appends what the node returns to the
    existing message list — the node only returns the new message(s), not the full
    accumulated history. Returning exactly one AIMessage is the correct contract.
    """

    @pytest.mark.asyncio
    async def test_returned_messages_contains_exactly_one_ai_message(self) -> None:
        """Node returns exactly one AIMessage in its 'messages' list."""
        state = _make_state([HumanMessage("Tell me about embeddings.")])
        mock_provider = _make_mock_provider("Embeddings map tokens to vectors.")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            result = await generate_node(state)

        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage)]
        assert len(ai_messages) == 1, (
            f"Node should return exactly 1 AIMessage; got {len(ai_messages)}"
        )

    @pytest.mark.asyncio
    async def test_returned_messages_list_has_length_one(self) -> None:
        """Node returns a list with exactly one message — the new AIMessage."""
        state = _make_state([HumanMessage("What is BM25?")])
        mock_provider = _make_mock_provider("BM25 is a ranking function.")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            result = await generate_node(state)

        assert len(result["messages"]) == 1

    @pytest.mark.asyncio
    async def test_node_does_not_return_input_human_message(self) -> None:
        """Node does not echo back the input HumanMessage — only the new AIMessage."""
        state = _make_state([HumanMessage("Do not repeat me.")])
        mock_provider = _make_mock_provider("Only the answer.")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            result = await generate_node(state)

        human_in_output = [m for m in result["messages"] if isinstance(m, HumanMessage)]
        assert len(human_in_output) == 0, (
            "Node must not return the input HumanMessage; the reducer handles accumulation."
        )


# ---------------------------------------------------------------------------
# Gate 3 — First turn: single HumanMessage, no prior history
# ---------------------------------------------------------------------------

class TestGate3FirstTurn:
    """First-turn scenario: state contains only one HumanMessage, no prior history."""

    @pytest.mark.asyncio
    async def test_first_turn_returns_answer(self) -> None:
        """Node processes a single-message state without error and returns a string answer."""
        state = _make_state([HumanMessage("What is retrieval-augmented generation?")])
        mock_provider = _make_mock_provider("RAG combines retrieval with generation.")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            result = await generate_node(state)

        assert result["answer"] == "RAG combines retrieval with generation."

    @pytest.mark.asyncio
    async def test_first_turn_does_not_raise(self) -> None:
        """Node does not raise when there is no prior conversation history."""
        state = _make_state([HumanMessage("first question")])
        mock_provider = _make_mock_provider("first answer")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            try:
                await generate_node(state)
            except Exception as exc:
                pytest.fail(f"generate_node raised on first turn: {exc}")

    @pytest.mark.asyncio
    async def test_first_turn_docs_joined_into_context(self) -> None:
        """Multiple docs are joined with double newlines in the system message context."""
        docs = [
            Document(page_content="Doc A content.", metadata={}),
            Document(page_content="Doc B content.", metadata={}),
        ]
        state = _make_state([HumanMessage("Summarise docs.")], docs=docs)
        mock_provider = _make_mock_provider("Summary answer.")

        captured_messages: list = []

        async def capture_ainvoke(messages: list) -> AIMessage:
            captured_messages.extend(messages)
            return AIMessage(content="Summary answer.")

        mock_llm = MagicMock()
        mock_llm.ainvoke = capture_ainvoke
        mock_provider_obj = MagicMock()
        mock_provider_obj.get_llm.return_value = mock_llm

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider_obj):
            from agents.nodes.generate import generate_node
            await generate_node(state)

        system_msg = captured_messages[0]
        assert "Doc A content." in system_msg.content
        assert "Doc B content." in system_msg.content


# ---------------------------------------------------------------------------
# Gate 4 — Second turn: full conversation history forwarded to LLM
# ---------------------------------------------------------------------------

class TestGate4SecondTurn:
    """Second-turn scenario: state contains prior HumanMessage + AIMessage + new HumanMessage."""

    @pytest.mark.asyncio
    async def test_second_turn_returns_answer(self) -> None:
        """Node processes multi-turn history without error and returns string answer."""
        state = _make_state([
            HumanMessage("q1"),
            AIMessage("a1"),
            HumanMessage("q2"),
        ])
        mock_provider = _make_mock_provider("answer to q2")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            result = await generate_node(state)

        assert result["answer"] == "answer to q2"

    @pytest.mark.asyncio
    async def test_second_turn_full_history_passed_to_llm(self) -> None:
        """All messages from state (prior turns + current) are forwarded to the LLM."""
        state = _make_state([
            HumanMessage("q1"),
            AIMessage("a1"),
            HumanMessage("q2"),
        ])

        captured_messages: list = []

        async def capture_ainvoke(messages: list) -> AIMessage:
            captured_messages.extend(messages)
            return AIMessage(content="answer to q2")

        mock_llm = MagicMock()
        mock_llm.ainvoke = capture_ainvoke
        mock_provider_obj = MagicMock()
        mock_provider_obj.get_llm.return_value = mock_llm

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider_obj):
            from agents.nodes.generate import generate_node
            await generate_node(state)

        # First message is the SystemMessage (prepended by node)
        # Remaining messages are state["messages"] in order
        from langchain_core.messages import SystemMessage
        assert isinstance(captured_messages[0], SystemMessage)
        assert isinstance(captured_messages[1], HumanMessage)
        assert captured_messages[1].content == "q1"
        assert isinstance(captured_messages[2], AIMessage)
        assert captured_messages[2].content == "a1"
        assert isinstance(captured_messages[3], HumanMessage)
        assert captured_messages[3].content == "q2"

    @pytest.mark.asyncio
    async def test_second_turn_does_not_raise(self) -> None:
        """Node does not raise when processing multi-turn conversation history."""
        state = _make_state([
            HumanMessage("q1"),
            AIMessage("a1"),
            HumanMessage("q2"),
        ])
        mock_provider = _make_mock_provider("a2")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            try:
                await generate_node(state)
            except Exception as exc:
                pytest.fail(f"generate_node raised on second turn: {exc}")


# ---------------------------------------------------------------------------
# Gate 5 — get_provider() is used; LLM not instantiated directly
# ---------------------------------------------------------------------------

class TestGate5GetProviderUsed:
    """LLM is obtained via get_provider(), not instantiated directly in the node."""

    @pytest.mark.asyncio
    async def test_get_provider_is_called(self) -> None:
        """get_provider() is called exactly once per node invocation."""
        state = _make_state([HumanMessage("Test question.")])
        mock_provider = _make_mock_provider("Test answer.")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider) as mock_gp:
            from agents.nodes.generate import generate_node
            await generate_node(state)

        mock_gp.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_llm_called_on_provider(self) -> None:
        """get_provider() result has get_llm() called on it to obtain the model."""
        state = _make_state([HumanMessage("Another question.")])
        mock_provider = _make_mock_provider("Another answer.")

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            await generate_node(state)

        mock_provider.get_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_user_level_falls_back_to_default_prompt(self) -> None:
        """generate_node with an unrecognised user_level completes without raising
        and uses DEFAULT_PROMPT framing (contains 'Answer using ONLY the provided context')."""
        state = _make_state(
            [HumanMessage("What is RAG?")],
            user_level="not_a_real_level",
        )

        captured_messages: list = []

        async def capture_ainvoke(messages: list) -> AIMessage:
            captured_messages.extend(messages)
            return AIMessage(content="Fallback answer.")

        mock_llm = MagicMock()
        mock_llm.ainvoke = capture_ainvoke
        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = mock_llm

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            result = await generate_node(state)  # must not raise

        from langchain_core.messages import SystemMessage
        assert isinstance(captured_messages[0], SystemMessage), (
            "First message passed to LLM must be a SystemMessage"
        )
        assert "Answer using ONLY the provided context" in captured_messages[0].content, (
            "DEFAULT_PROMPT content must appear when user_level is unrecognised"
        )
        assert result["answer"] == "Fallback answer."

    @pytest.mark.asyncio
    async def test_ainvoke_called_on_llm(self) -> None:
        """The async ainvoke() method is called on the LLM — not invoke()."""
        state = _make_state([HumanMessage("Async question.")])
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="Async answer."))
        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = mock_llm

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            await generate_node(state)

        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_system_message_contains_user_level(self) -> None:
        """SystemMessage forwarded to LLM contains the user_level from state."""
        state = _make_state(
            [HumanMessage("Explain vectors.")],
            user_level="expert",
        )

        captured_messages: list = []

        async def capture_ainvoke(messages: list) -> AIMessage:
            captured_messages.extend(messages)
            return AIMessage(content="Expert answer.")

        mock_llm = MagicMock()
        mock_llm.ainvoke = capture_ainvoke
        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = mock_llm

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            await generate_node(state)

        from langchain_core.messages import SystemMessage
        assert isinstance(captured_messages[0], SystemMessage)
        assert "expert" in captured_messages[0].content

    @pytest.mark.asyncio
    async def test_default_user_level_novice_when_missing(self) -> None:
        """When user_level is absent from state, node defaults to 'novice'."""
        # Build state without user_level key to simulate a missing field.
        state: dict[str, Any] = {
            "messages": [HumanMessage("Question without level.")],
            "question": "Question without level.",
            "user_id": None,
            "docs": [Document(page_content="Some context.", metadata={})],
            "retrieval_source": "chroma",
            "answer": "",
            # user_level intentionally omitted
            "topic_scores_delta": {},
            "identified_gaps": [],
            "assessment_error": False,
            "trace_id": "test-trace-no-level",
            "latency_ms": 0,
            "cache_hit": "miss",
        }

        captured_messages: list = []

        async def capture_ainvoke(messages: list) -> AIMessage:
            captured_messages.extend(messages)
            return AIMessage(content="Answer.")

        mock_llm = MagicMock()
        mock_llm.ainvoke = capture_ainvoke
        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = mock_llm

        with patch("agents.nodes.generate.get_provider", return_value=mock_provider):
            from agents.nodes.generate import generate_node
            result = await generate_node(state)

        from langchain_core.messages import SystemMessage
        assert isinstance(captured_messages[0], SystemMessage)
        assert "complete beginner" in captured_messages[0].content
        assert result["answer"] == "Answer."
