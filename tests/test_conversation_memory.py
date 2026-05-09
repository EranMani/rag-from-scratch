"""
Tests for Commit 03 — conversation-memory-integration.

Coverage targets (Quinn NEEDS ADDITIONS — three required tests):

A. format_history empty session
   First-turn safety: format_history on a session with no messages must return
   "" (empty string, not None, no KeyError). A None here would corrupt the
   prompt silently.

B. format_history truncation at 10 messages
   The messages[-10:] slice is the only mechanism preventing unbounded token
   growth. Verified at the boundary: 6 human+assistant turns (12 messages) →
   only 10 lines appear in the output, the first 2 are absent.

C. generate() passes history key to chain invocation
   Core wiring test: the conversation_history string must reach chain.invoke()
   as the "history" key. A future rename or missed argument would fail silently
   without this guard.

Design notes:
- Tests A and B require no mocks — SessionMemory is a plain Python class with
  no external dependencies.
- Test C patches get_provider() and the module-level RAG_PROMPT so no live LLM,
  no network call, and no ChromaDB access is needed. The LCEL | chain composes
  MagicMock objects; chain.invoke() is a MagicMock whose call_args is inspectable.
"""

from unittest.mock import MagicMock, patch

from rag.memory.conversation import SessionMemory
from rag.pipeline.generator import generate


# ---------------------------------------------------------------------------
# Test A — format_history returns "" for a session with no messages
# ---------------------------------------------------------------------------

class TestFormatHistoryEmptySession:
    """format_history on an unknown session must return an empty string, never None."""

    def test_empty_session_returns_empty_string(self):
        memory = SessionMemory()

        result = memory.format_history("s1")

        assert result == "", (
            f"format_history('s1') on an empty session must return '' (empty string), "
            f"got {result!r}. A None or missing-key error here would silently corrupt "
            "the prompt on the first turn of every conversation."
        )

    def test_empty_session_returns_str_not_none(self):
        """Explicit type guard — callers concatenate this into a prompt string."""
        memory = SessionMemory()

        result = memory.format_history("never-seen-session-id")

        assert isinstance(result, str), (
            f"format_history must return str, got {type(result).__name__!r}. "
            "Prompt templates expect a str for the {history} slot."
        )


# ---------------------------------------------------------------------------
# Test B — format_history truncates to 10 messages at the boundary
# ---------------------------------------------------------------------------

class TestFormatHistoryTruncation:
    """messages[-10:] is the sole token-growth guard; must be verified at the boundary."""

    def _add_turns(self, memory: SessionMemory, session_id: str, n_turns: int) -> None:
        """Add n_turns human+assistant pairs to session_id (2*n_turns messages total)."""
        for i in range(n_turns):
            memory.add_human(session_id, f"question {i}")
            memory.add_assistant(session_id, f"answer {i}")

    def test_twelve_messages_yields_exactly_ten_lines(self):
        """
        6 turns = 12 messages added. format_history must return exactly 10 lines.
        The first 2 messages (question 0 / answer 0) must be absent from output.
        """
        memory = SessionMemory()
        session_id = "truncation-test"

        self._add_turns(memory, session_id, n_turns=6)  # 12 messages total

        result = memory.format_history(session_id)
        lines = result.splitlines()

        assert len(lines) == 10, (
            f"format_history must return exactly 10 lines when 12 messages exist "
            f"(messages[-10:] truncation). Got {len(lines)} lines.\n"
            f"Full output:\n{result}"
        )

    def test_first_two_messages_are_absent_after_truncation(self):
        """
        The two oldest messages (turn 0: question 0 / answer 0) must not appear
        in the formatted output once 12 messages have been stored.
        """
        memory = SessionMemory()
        session_id = "truncation-absent-test"

        self._add_turns(memory, session_id, n_turns=6)

        result = memory.format_history(session_id)

        assert "question 0" not in result, (
            "The oldest human message ('question 0') must be dropped by the "
            "messages[-10:] truncation. It was found in the output, meaning "
            "truncation is not working at the 10-message boundary.\n"
            f"Output:\n{result}"
        )
        assert "answer 0" not in result, (
            "The oldest assistant message ('answer 0') must be dropped by the "
            "messages[-10:] truncation. It was found in the output, meaning "
            "truncation is not working at the 10-message boundary.\n"
            f"Output:\n{result}"
        )

    def test_ten_messages_are_fully_present_below_boundary(self):
        """
        5 turns = 10 messages — exactly at the boundary. All must appear; nothing dropped.
        """
        memory = SessionMemory()
        session_id = "at-boundary-test"

        self._add_turns(memory, session_id, n_turns=5)  # exactly 10 messages

        result = memory.format_history(session_id)
        lines = result.splitlines()

        assert len(lines) == 10, (
            f"At exactly 10 messages, all 10 must appear. Got {len(lines)} lines."
        )
        # First turn must still be present — nothing dropped at the boundary
        assert "question 0" in result, (
            "With exactly 10 messages no truncation should occur; 'question 0' must be present."
        )


# ---------------------------------------------------------------------------
# Test C — generate() passes conversation_history as "history" to chain.invoke()
# ---------------------------------------------------------------------------

class TestGeneratePassesHistoryToChain:
    """
    Core wiring: generate() must forward conversation_history as the "history"
    key in the dict passed to chain.invoke(). A rename or missed argument would
    fail silently at runtime, corrupting every multi-turn response.

    Patching strategy:
    - patch get_provider() → mock provider whose get_llm() returns a MagicMock LLM.
      The LCEL | chain composes MagicMock objects; chain.invoke() becomes a
      MagicMock automatically, making call_args inspectable.
    - patch LLM_CALLS (prometheus counter) so the .labels().inc() side-effect
      in generator.py does not require a live metrics registry.
    - No live LLM, no network, no ChromaDB.
    """

    def test_history_key_reaches_chain_invoke(self):
        conversation_history = "Human: prior\nAssistant: answer"

        mock_llm = MagicMock()
        # chain.invoke() must return a str; configure the terminal mock
        # so the LCEL chain's final .invoke() yields a string, not a MagicMock.
        # Because MagicMock.__or__ returns a MagicMock, chaining
        # RAG_PROMPT | mock_llm | StrOutputParser() produces a chain object
        # whose .invoke() is a MagicMock. We set its return_value to a string.
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "generated answer"

        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = mock_llm
        mock_provider.provider_name.return_value = "mock"

        # Patch RAG_PROMPT so that RAG_PROMPT | llm | parser returns our mock_chain.
        # RAG_PROMPT.__or__(llm) → intermediate; intermediate.__or__(parser) → mock_chain.
        mock_intermediate = MagicMock()
        mock_intermediate.__or__ = MagicMock(return_value=mock_chain)

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_intermediate)

        with (
            patch("rag.pipeline.generator.get_provider", return_value=mock_provider),
            patch("rag.pipeline.generator.RAG_PROMPT", mock_prompt),
            patch("rag.pipeline.generator.LLM_CALLS") as mock_metric,
        ):
            mock_metric.labels.return_value.inc.return_value = None

            result = generate(
                question="test question",
                docs=[],
                conversation_history=conversation_history,
            )

        # Verify chain.invoke() was called exactly once
        mock_chain.invoke.assert_called_once()

        # Extract the dict that was passed to chain.invoke()
        call_args = mock_chain.invoke.call_args
        # call_args is a call object; positional arg 0 is the input dict
        invoke_dict = call_args[0][0]

        assert "history" in invoke_dict, (
            f"chain.invoke() must receive a 'history' key. "
            f"Keys present: {list(invoke_dict.keys())}. "
            "Check that generate() passes conversation_history as history= "
            "in the invoke dict."
        )
        assert invoke_dict["history"] == conversation_history, (
            f"chain.invoke() received history={invoke_dict['history']!r} "
            f"but expected {conversation_history!r}. "
            "The conversation_history argument is not being forwarded correctly."
        )

    def test_generate_returns_chain_output(self):
        """Sanity check: generate() must return the string the chain produces."""
        expected_answer = "This is the generated answer."

        mock_llm = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = expected_answer

        mock_intermediate = MagicMock()
        mock_intermediate.__or__ = MagicMock(return_value=mock_chain)

        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_intermediate)

        mock_provider = MagicMock()
        mock_provider.get_llm.return_value = mock_llm
        mock_provider.provider_name.return_value = "mock"

        with (
            patch("rag.pipeline.generator.get_provider", return_value=mock_provider),
            patch("rag.pipeline.generator.RAG_PROMPT", mock_prompt),
            patch("rag.pipeline.generator.LLM_CALLS") as mock_metric,
        ):
            mock_metric.labels.return_value.inc.return_value = None

            result = generate(
                question="any question",
                docs=[],
                conversation_history="",
            )

        assert result == expected_answer, (
            f"generate() must return the string produced by chain.invoke(). "
            f"Got {result!r}, expected {expected_answer!r}."
        )
