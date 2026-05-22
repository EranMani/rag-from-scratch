import logging
from typing import Any

from langchain_core.messages import AIMessage

from agents.mcq_utils import load_mcq_question, load_open_question
from agents.state import AgentState

from .passive import run_passive_assessment
from .results import build_selection_result
from .question_selection import select_mcq_question, select_open_question

logger = logging.getLogger(__name__)

_REDIRECT_MESSAGE = (
    "I can see you're eager to get ahead — that's great! "
    "Let's make sure the foundations are solid first. "
    "Here's a question that matches your current level:"
)


async def select_test_question(state: AgentState) -> dict[str, Any]:
    """Run passive assessment then select and deliver a curriculum MCQ.

    Returns an empty messages list (no question) when the user's input is not RAG-related.
    """
    user_level = state.get("user_level") or "novice"
    passive_delta, is_rag_related, should_redirect = await run_passive_assessment(
        state.get("question") or "", user_level
    )
    gaps = state.get("identified_gaps") or []

    # General chat topic
    if not is_rag_related:
        return build_selection_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=False,
        )

    selection = select_mcq_question(state)
    if selection is None:
        logger.warning("assess_node: no valid slug available for test selection")
        return build_selection_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=True,
        )

    slug, q_idx = selection
    try:
        display_question_text, correct_answer = load_mcq_question(slug, q_idx)
    except (FileNotFoundError, ValueError) as exc:
        logger.warning("assess_node: failed to load MCQ question for slug '%s': %s", slug, exc)
        return build_selection_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=True,
        )

    messages = []
    if should_redirect:
        messages.append(AIMessage(content=_REDIRECT_MESSAGE))
    messages.append(AIMessage(content=f"\n\n{display_question_text}"))

    return build_selection_result(
        topic_scores_delta=passive_delta,
        identified_gaps=gaps,
        assessment_error=False,
        pending_test_question=display_question_text,
        pending_test_slug=slug,
        is_mcq=True,
        pending_mcq_correct_answer=correct_answer,
        messages=messages,
    )


async def deliver_open_question(
    state: AgentState,
    passive_delta: dict,
    gaps: list,
    should_redirect: bool,
) -> dict:
    """Select and deliver an open-ended curriculum question.

    Not wired into select_test_question yet — 45.3 adds the ratio logic.
    """
    selection = select_open_question(state)
    if selection is None:
        logger.warning("deliver_open_question: no valid slug available")
        return build_selection_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=True,
        )

    slug, q_idx = selection
    try:
        display_text = load_open_question(slug, q_idx)
    except (FileNotFoundError, ValueError) as exc:
        logger.warning("deliver_open_question: failed to load question for slug '%s': %s", slug, exc)
        return build_selection_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=True,
        )

    messages = []
    if should_redirect:
        messages.append(AIMessage(content=_REDIRECT_MESSAGE))
    messages.append(AIMessage(content=f"\n\n{display_text}"))

    return build_selection_result(
        topic_scores_delta=passive_delta,
        identified_gaps=gaps,
        assessment_error=False,
        pending_test_question=display_text,
        pending_test_slug=slug,
        is_mcq=False,
        messages=messages,
    )
