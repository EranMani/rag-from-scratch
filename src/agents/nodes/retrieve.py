"""
retrieve_node — LangGraph node wrapping the existing retrieve() function.

Node contract:
    Input:  AgentState.question (str)
    Output: {"docs": list[Document], "retrieval_source": str}

Only reads `question` from state.  Only writes `docs` and `retrieval_source`.
"""

from langchain_core.documents import Document

from agents.state import AgentState
from rag.pipeline.retriever import retrieve
from rag.resilience.circuit_breaker import chroma_cb


def retrieve_node(state: AgentState) -> dict:
    """LangGraph node: retrieve relevant documents for the current question.

    Wraps the existing retrieve() function and annotates which retrieval
    path was taken ('chroma' or 'bm25') by inspecting the circuit breaker
    state before and after the call.

    Determination logic:
    - If chroma_cb was NOT available before the call → BM25 ran directly.
    - If chroma_cb WAS available before the call but is OPEN after → Chroma
      failed mid-call, BM25 fallback activated → source is 'bm25'.
    - If chroma_cb WAS available before the call and is still available
      after → Chroma succeeded → source is 'chroma'.
    """
    question: str = state["question"]

    chroma_available_before: bool = chroma_cb.is_available()

    docs: list[Document] = retrieve(question)

    chroma_available_after: bool = chroma_cb.is_available()

    if chroma_available_before and chroma_available_after:
        retrieval_source: str = "chroma"
    else:
        retrieval_source = "bm25"

    return {"docs": docs, "retrieval_source": retrieval_source}
