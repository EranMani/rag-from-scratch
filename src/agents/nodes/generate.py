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

import asyncio
import logging

from langchain_core.messages import AIMessage, BaseMessage

from agents.prompts import DEFAULT_PROMPT, PROMPT_TEMPLATES
from agents.state import AgentState
from app.profile.db import get_profile_by_user_id
from app.profile.scoring import PHASE_1_TOPICS, PHASE_2_TOPICS
from rag.providers import get_provider

logger = logging.getLogger(__name__)


async def generate_node(state: AgentState) -> dict:
    """LangGraph node: generate an answer using retrieved docs and message history.

    Builds a SystemMessage with the retrieved context and user level, then calls
    the LLM with the full conversation history. The AIMessage response is returned
    so the add_messages reducer can append it to state["messages"].
    """

    # Update log when no documents are found
    if not state["docs"]:
        logger.warning("generate_node: docs list is empty — generating with no retrieved context, trace_id=%s", state.get("trace_id"))

    # Combine documents with new-lines
    context: str = "\n\n".join(doc.page_content for doc in state["docs"])
    user_level: str = state.get("user_level", "novice")  # type: ignore[call-overload]

    # Proximity hint: surface near-passing topics (0.60–0.69) to guide generation
    user_id: str | None = state.get("user_id")
    if user_id:
        profile = await asyncio.to_thread(get_profile_by_user_id, user_id)
        if profile:
            near_threshold = PHASE_1_TOPICS | PHASE_2_TOPICS
            near_passing = [
                f"{slug} (score: {score:.2f}, threshold: 0.70)"
                for slug, score in (profile.get("topic_scores") or {}).items()
                if slug in near_threshold and isinstance(score, (int, float)) and 0.60 <= score < 0.70
            ]
            if near_passing:
                context += (
                    "\n\nNote: user is close to passing "
                    + ", ".join(near_passing)
                    + ". Reinforce this topic where natural."
                )

    # Fetch the correct prompt using the current level of the user
    template = PROMPT_TEMPLATES.get(user_level, DEFAULT_PROMPT)

    # Inject documents context into the system prompt
    system_msg = template.format_messages(context=context)[0]

    # Get the actual LLM model
    llm = get_provider().get_llm()

    # Assembe the system and conversation messages into final package to be set to the LLM
    messages: list[BaseMessage] = [system_msg] + list(state["messages"])

    """ 
    ainvoke is async operation, keeping the event loop alive while waiting for answer
    LLM calls are I/O heavy. Async allows to handle many requests with very few ram and processing
    NOTE: ainvoke supports streaming, getting the answer token by token
    """
    response: BaseMessage = await llm.ainvoke(messages)
    # AIMessage inherits from BaseMessage. Assert checks the response is actually a proper AI message
    assert isinstance(response, AIMessage), f"Expected AIMessage from LLM, got {type(response)}"

    return {
        "messages": [response],   # add_messages appends, does not replace
        "answer": response.content,  # kept for assess_node and SSE done event
    }
