"""
generate_node — LangGraph node that generates an answer from retrieved context.

Node contract:
    Input:  AgentState.docs (list[Document])
            AgentState.messages (Annotated[list[BaseMessage], add_messages])
            AgentState.user_level (Literal["novice","beginner","intermediate","advanced","expert"])
    Output: {"messages": [AIMessage], "answer": str}

Design notes:
- Node is async. Uses `await llm.ainvoke()` so that when `graph.astream_events()`
  is wired in Commit 10, token-level `on_chat_model_stream` events fire automatically
  with zero changes to this node.
- `question` is NOT read here. The current user question is already the last
  HumanMessage in state["messages"]. `question` exists only for retrieve_node.
- `state["messages"]` contains the full conversation (prior turns + this turn's
  HumanMessage). The full list is forwarded to the LLM as conversational context.
- The SystemMessage is prepended (not appended) so the LLM sees it as the role
  framing before any user content.
- LLM is obtained via get_provider().get_llm() — this honours the OpenAI circuit
  breaker → Ollama fallback chain. No LLM is instantiated directly.
- Return dict contains exactly {"messages": ..., "answer": ...} — no other keys.
  add_messages reducer in AgentState APPENDS the returned [AIMessage]; it does not
  replace the existing message list.
"""

import logging

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage

from agents.state import AgentState
from rag.providers import get_provider

logger = logging.getLogger(__name__)


async def generate_node(state: AgentState) -> dict:
    """LangGraph node: generate an answer using retrieved docs and message history.

    Builds a SystemMessage with the retrieved context and user level, then calls
    the LLM with the full conversation history. The AIMessage response is returned
    so the add_messages reducer can append it to state["messages"].
    """
    if not state["docs"]:
        logger.warning("generate_node: docs list is empty — generating with no retrieved context, trace_id=%s", state.get("trace_id"))

    context: str = "\n\n".join(doc.page_content for doc in state["docs"])
    user_level: str = state.get("user_level", "novice")  # type: ignore[call-overload]

    system_msg = SystemMessage(content=(
        "You are an expert on RAG systems. Answer using ONLY the provided context.\n"
        f"Adapt your explanation depth to the user's level: {user_level}.\n\n"
        f"Context:\n{context}"
    ))

    llm = get_provider().get_llm()

    # state["messages"] contains the full conversation: prior turns + current HumanMessage.
    # Prepending system_msg gives the LLM role framing before the dialogue.
    messages: list[BaseMessage] = [system_msg] + list(state["messages"])

    response: BaseMessage = await llm.ainvoke(messages)
    assert isinstance(response, AIMessage), f"Expected AIMessage from LLM, got {type(response)}"

    return {
        "messages": [response],   # add_messages appends — does not replace
        "answer": response.content,  # kept for assess_node and SSE done event
    }
