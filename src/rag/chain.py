"""
chain.py — RAG pipeline utilities.

run_rag_pipeline() and the SessionMemory import were removed in Commit 10.
Conversation history is managed by LangGraph's MemorySaver checkpointer
(keyed by thread_id / session_id); the graph is streamed via astream_events()
in app/api/routes/chat.py.

ChatResponse is the typed schema for the SSE 'done' event payload.
build_chat_response extracts the relevant fields from the final AgentState dict
returned by the LangGraph 'on_chain_end' event, producing a ChatResponse instance
ready for JSON serialisation.

The Redis query-level cache (rag.cache.redis_cache) is retained here for import
convenience by pipeline utilities that pre-warm or invalidate cache entries.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ChatResponse(BaseModel):
    """Typed schema for the SSE 'done' event payload.

    Fields:
        answer:          The full generated answer text.
        user_level:      Mastery level used for this turn (from AgentState).
        assessed_topics: Sparse topic→score-delta dict from assess_node.
                         Empty dict when assessment did not run or errored.
        test_question:   Curriculum question selected by assess_node for this
                         turn, or None when no question was selected.
        is_mcq:          True when test_question is MCQ format (A/B/C/D options).
    """

    answer: str = ""
    user_level: str | None = None
    assessed_topics: dict[str, float] = {}
    test_question: str | None = None
    is_mcq: bool = False


def build_chat_response(state: dict[str, Any]) -> ChatResponse:
    """Extract ChatResponse fields from the final AgentState output dict.

    Called inside the generate_stream() generator after the LangGraph
    'on_chain_end' event fires.  Guards against missing keys so that a partial
    or error state still produces a well-formed response.
    """
    return ChatResponse(
        answer=state.get("answer", ""),
        user_level=state.get("user_level"),
        assessed_topics=state.get("topic_scores_delta", {}),
        test_question=state.get("pending_test_question"),
        is_mcq=bool(state.get("is_mcq", False)),
    )
