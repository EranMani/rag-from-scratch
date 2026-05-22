import logging

from agents.prompts.assessment import passive_prompt
from agents.state import VALID_MODULE_SLUGS, PassiveAssessmentOutput
from rag.providers import get_provider

from .constants import _PASSIVE_CONFIDENCE_THRESHOLD, _PASSIVE_LEVEL_SCORE

logger = logging.getLogger(__name__)

_LEVEL_ORDER: dict[str, int] = {
    "novice": 0, "beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4
}


def _compute_passive_delta(
    result: PassiveAssessmentOutput, user_level: str
) -> tuple[dict[str, float], bool]:
    """Returns (delta, should_redirect). should_redirect is True when question is 2+ levels above user."""
    # None is a valid LLM response meaning "not RAG-related" — not an error
    if result.relevant_slug is None:
        return {}, False

    # Slug returned but not in the known set — LLM hallucination, ignore silently
    if result.relevant_slug not in VALID_MODULE_SLUGS:
        logger.warning(
            "passive_assessment: slug '%s' not in VALID_MODULE_SLUGS — ignoring",
            result.relevant_slug,
        )
        return {}, False

    # Low confidence — signal too weak to update the profile
    if result.confidence < _PASSIVE_CONFIDENCE_THRESHOLD:
        return {}, False

    # Question is 2+ levels above user — redirect instead of scoring
    question_rank = _LEVEL_ORDER.get(result.inferred_level, 0)
    user_rank = _LEVEL_ORDER.get(user_level, 0)
    if question_rank > user_rank + 1:
        return {}, True

    # Update the score according to user mastery level
    score = _PASSIVE_LEVEL_SCORE.get(user_level, 0.0)
    return ({result.relevant_slug: score} if score > 0.0 else {}), False


async def _invoke_model(question: str) -> PassiveAssessmentOutput:
    llm = get_provider().get_llm()
    chain = passive_prompt | llm.with_structured_output(PassiveAssessmentOutput)
    result: PassiveAssessmentOutput = await chain.ainvoke({"question": question})
    return result

async def run_passive_assessment(
    question: str, user_level: str
) -> tuple[dict[str, float], bool, bool]:
    """Infer knowledge level from the user's natural query (no formal test).

    Returns (delta, is_rag_related, should_redirect):
    - delta: topic score update to apply to the knowledge profile. Empty when
      the question is off-topic, low confidence, or a redirect is warranted.
    - is_rag_related: False skips test selection entirely in the caller.
    - should_redirect: True prepends a soft redirect message before the test question.

    On exception, returns ({}, True, False) — is_rag_related=True is intentionally
    permissive: a failed LLM call should not suppress the knowledge check.
    """
    try:
        model_response = await _invoke_model(question)

        is_rag_related = model_response.relevant_slug is not None
        
        delta, should_redirect = _compute_passive_delta(model_response, user_level)
        return delta, is_rag_related, should_redirect
    except Exception:
        logger.warning("passive_assessment: LLM call failed — continuing with empty delta", exc_info=True)
        return {}, True, False
