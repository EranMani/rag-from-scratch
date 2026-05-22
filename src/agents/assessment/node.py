from typing import Any

from agents.state import AgentState

from .evaluation import evaluate_answer
from .test_delivery import select_test_question


def _is_evaluation_mode(state: AgentState) -> bool:
    """State-gate: returns True only when a question is pending and the user has responded."""
    pending = state.get("pending_test_question")
    if not pending:
        return False

    messages = state.get("messages") or []
    if not messages:
        return False

    last = messages[-1]
    return getattr(last, "type", None) == "human"


async def assess_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: routes to evaluation or question selection based on state."""
    if _is_evaluation_mode(state):
        return await evaluate_answer(state)
    return await select_test_question(state)
