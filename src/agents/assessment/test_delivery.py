import logging
import random
from typing import Any

from langchain_core.messages import AIMessage

from agents.mcq_utils import get_mcq_blocks_for_difficulty, load_mcq_question_for_difficulty, load_open_question
from agents.state import AgentState

from .passive import run_passive_assessment
from .question_generation import generate_questions
from .results import build_selection_result
from .question_selection import select_mcq_question_for_level, select_open_question, select_question_type

logger = logging.getLogger(__name__)

_REDIRECT_MESSAGE = (
    "I can see you're eager to get ahead — that's great! "
    "Let's make sure the foundations are solid first. "
    "Here's a question that matches your current level:"
)


async def select_test_question(state: AgentState) -> dict[str, Any]:
    """Run passive assessment then select and deliver a curriculum question.

    Returns an empty messages list (no question) when the user's input is not RAG-related.
    Routes to MCQ or open delivery based on level-weighted probability.
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

    question_type = select_question_type(user_level)

    if question_type == "open":
        return await deliver_open_question(state, passive_delta, gaps, should_redirect)

    selection = select_mcq_question_for_level(state)
    if selection is None:
        logger.warning("assess_node: no valid slug available for test selection")
        return build_selection_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=True,
        )

    slug, q_idx = selection
    mastery_level: str | None = state.get("user_level")

    display_question_text, correct_answer = await _deliver_mcq(
        state, slug, q_idx, mastery_level
    )
    if display_question_text is None:
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
        generated_question_pool=state.get("generated_question_pool"),
    )


async def _deliver_mcq(
    state: AgentState,
    slug: str,
    q_idx: int,
    mastery_level: str | None,
) -> tuple[str | None, str | None]:
    """Return (display_text, correct_answer) from the generated pool or the bank.

    On first call for this (slug, mastery_level), attempts LLM synthesis and caches
    the pool in state. Falls back to the bank silently on any failure.
    Returns (None, None) if even the bank load fails.
    """
    cache_key = f"{slug}:{mastery_level or 'none'}"
    pool: dict[str, list] = state.get("generated_question_pool") or {}

    if cache_key not in pool:
        # Cache miss — attempt generation
        try:
            bank_blocks = get_mcq_blocks_for_difficulty(slug, mastery_level)
            generated = await generate_questions(slug, mastery_level or "novice", bank_blocks)
            pool = {**pool, cache_key: generated}
            # Write updated pool back into state via the returned dict (LangGraph merge)
            state["generated_question_pool"] = pool  # type: ignore[index]
        except Exception as exc:
            logger.warning(
                "_deliver_mcq: generation failed for slug='%s' level='%s' — falling back to bank: %s",
                slug, mastery_level, exc,
            )

    generated_pool = pool.get(cache_key)
    if generated_pool:
        # Sample a question from the generated pool
        q = random.choice(generated_pool)
        stem = q["question"]
        opts_text = "\n".join(f"{k}. {v}" for k, v in sorted(q["options"].items()))
        display_text = f"Knowledge check: {stem}\n\n{opts_text}"
        return display_text, q["correct"]

    # Fall back to bank
    try:
        return load_mcq_question_for_difficulty(slug, q_idx, mastery_level)
    except (FileNotFoundError, ValueError) as exc:
        logger.warning("_deliver_mcq: bank fallback failed for slug='%s': %s", slug, exc)
        return None, None


async def deliver_open_question(
    state: AgentState,
    passive_delta: dict,
    gaps: list,
    should_redirect: bool,
) -> dict:
    """Select and deliver an open-ended curriculum question."""
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
