import logging
from typing import Any

from langchain_core.messages import AIMessage

from agents.mcq_utils import load_mcq_question as _load_mcq_question
from agents.state import AgentState

from .passive import _run_passive_assessment
from .results import _build_test_result
from .slug_selection import _select_mcq_question_index, _select_test_slug

logger = logging.getLogger(__name__)


async def _select_test_question(state: AgentState) -> dict[str, Any]:
    """Run passive assessment then select and load a curriculum question."""
    passive_delta, is_rag_related = await _run_passive_assessment(state.get("question") or "")
    gaps = state.get("identified_gaps") or []

    if not is_rag_related:
        return _build_test_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=False,
            test_mode=False,
        )

    slug = _select_test_slug(state)
    if slug is None:
        logger.warning("assess_node: no valid slug available for test selection")
        return _build_test_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=True,
            test_mode=False,
        )

    try:
        q_idx = _select_mcq_question_index(state, slug)
        display_text, correct_answer = _load_mcq_question(slug, q_idx)
    except (FileNotFoundError, ValueError) as exc:
        logger.warning("assess_node: failed to load MCQ question for slug '%s': %s", slug, exc)
        return _build_test_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=True,
            test_mode=False,
        )

    return _build_test_result(
        topic_scores_delta=passive_delta,
        identified_gaps=gaps,
        assessment_error=False,
        test_mode=True,
        pending_test_question=display_text,
        pending_test_slug=slug,
        is_mcq=True,
        pending_mcq_correct_answer=correct_answer,
        messages=[AIMessage(content=f"\n\n{display_text}")],
    )
