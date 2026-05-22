import logging

from langchain_core.prompts import ChatPromptTemplate

from agents.state import VALID_MODULE_SLUGS, PassiveAssessmentOutput
from rag.providers import get_provider

from .constants import _PASSIVE_CONFIDENCE_THRESHOLD, _PASSIVE_LEVEL_SCORE

logger = logging.getLogger(__name__)

_PASSIVE_SYSTEM = """\
You analyze a learner's question to infer their RAG knowledge level.

Valid topic slugs: embeddings_and_similarity, rag_pipeline_architecture,
chunking_strategies, vector_databases, retrieval_methods, context_and_prompting,
langchain_fundamentals, evaluation_and_metrics, production_patterns.

Return relevant_slug (the single most relevant slug, or null if unclear),
inferred_level (novice/beginner/intermediate/advanced/expert), and
confidence (0.0-1.0). Base level on vocabulary and specificity in the question.\
"""

_PASSIVE_HUMAN = "Question: {question}"

_passive_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages([
    ("system", _PASSIVE_SYSTEM),
    ("human", _PASSIVE_HUMAN),
])

_LEVEL_ORDER: dict[str, int] = {
    "novice": 0, "beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4
}


def _validated_passive_delta(
    result: PassiveAssessmentOutput, user_level: str
) -> tuple[dict[str, float], bool]:
    """Returns (delta, should_redirect). should_redirect is True when question is 2+ levels above user."""
    if result.relevant_slug is None:
        return {}, False

    if result.relevant_slug not in VALID_MODULE_SLUGS:
        logger.warning(
            "passive_assessment: slug '%s' not in VALID_MODULE_SLUGS — ignoring",
            result.relevant_slug,
        )
        return {}, False

    if result.confidence < _PASSIVE_CONFIDENCE_THRESHOLD:
        return {}, False

    question_rank = _LEVEL_ORDER.get(result.inferred_level, 0)
    user_rank = _LEVEL_ORDER.get(user_level, 0)
    if question_rank > user_rank + 1:
        return {}, True

    score = _PASSIVE_LEVEL_SCORE.get(user_level, 0.0)
    return ({result.relevant_slug: score} if score > 0.0 else {}), False


async def _run_passive_assessment(
    question: str, user_level: str
) -> tuple[dict[str, float], bool, bool]:
    """Infer knowledge level from the user's natural query (no formal test).

    Returns (delta, is_rag_related, should_redirect).
    On exception, returns ({}, True, False) — permissive fallback avoids suppressing the knowledge check.
    """
    try:
        llm = get_provider().get_llm()
        chain = _passive_prompt | llm.with_structured_output(PassiveAssessmentOutput)
        result: PassiveAssessmentOutput = await chain.ainvoke({"question": question})
        is_rag_related = result.relevant_slug is not None
        delta, should_redirect = _validated_passive_delta(result, user_level)
        return delta, is_rag_related, should_redirect
    except Exception:
        logger.warning("passive_assessment: LLM call failed — continuing with empty delta", exc_info=True)
        return {}, True, False
