from langchain_core.documents import Document
from langgraph.checkpoint.memory import MemorySaver

from agents.graph import build_graph
from agents.state import AgentState, VALID_MODULE_SLUGS
from rag.pipeline import retriever


def test_agent_state_contains_current_core_fields():
    fields = set(AgentState.__annotations__)

    assert {
        "messages",
        "question",
        "user_id",
        "docs",
        "answer",
        "user_level",
        "topic_scores_delta",
        "identified_gaps",
        "assessment_error",
        "session_question_counts",
        "is_passive_delta",
    } <= fields
    assert "retrieval_source" not in fields


def test_graph_compiles_with_memory_saver():
    graph = build_graph(MemorySaver())

    assert graph is not None
    assert graph.config["recursion_limit"] == 10


def test_bm25_fallback_returns_documents_when_chroma_unavailable(monkeypatch):
    docs = [
        Document(page_content="LangGraph turns RAG into explicit state transitions."),
        Document(page_content="Redis stores cache entries for repeated queries."),
    ]
    retriever.set_bm25_fallback(docs)

    monkeypatch.setattr(retriever.chroma_cb, "is_available", lambda: False)

    results = retriever.retrieve("LangGraph state machine", k=1)

    assert len(results) == 1
    assert "LangGraph" in results[0].page_content
