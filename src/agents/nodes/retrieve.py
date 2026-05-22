"""
retrieve_node — LangGraph node wrapping the existing retrieve() function.

Node contract:
    Input:  AgentState.question (str)
    Output: {"docs": list[Document]}

Only reads `question` from state.  Only writes `docs`.
"""

"""
NOTE: Serves as the information retrieval station within the RAG pipeline
Read the user question from the state -> execute the retrieval function -> return relevant docs
Use circuit breaker to determine retrieval path (semantic or bm25)
"""

from langchain_core.documents import Document

from agents.state import AgentState
from rag.pipeline.retriever import retrieve


def retrieve_node(state: AgentState) -> dict:
    """LangGraph node: retrieve relevant documents for the current question."""
    docs: list[Document] = retrieve(state["question"])
    return {"docs": docs}
