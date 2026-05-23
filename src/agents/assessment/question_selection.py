import random

from agents.mcq_utils import get_mcq_count, get_open_question_count
from agents.state import VALID_MODULE_SLUGS, AgentState
from app.profile.scoring import PHASE_1_TOPICS, PHASE_2_TOPICS, PHASE_3_TOPICS

_ALL_TOPICS: frozenset[str] = PHASE_1_TOPICS | PHASE_2_TOPICS | PHASE_3_TOPICS

_LEVEL_TO_PHASE: dict[str, frozenset[str]] = {
    "novice":       PHASE_1_TOPICS,
    "intermediate": PHASE_2_TOPICS,
    "advanced":     PHASE_3_TOPICS,
    "expert":       _ALL_TOPICS,
}

# Canonical ordering: Phase 1 first, Phase 3 last
_ORDERED_SLUGS: list[str] = [
    "embeddings_and_similarity",
    "rag_pipeline_architecture",
    "chunking_strategies",
    "vector_databases",
    "retrieval_methods",
    "context_and_prompting",
    "langchain_fundamentals",
    "evaluation_and_metrics",
    "production_patterns",
]


# Open-question probability by level: novice=0%, intermediate=20%, advanced=40%, expert=70%
_OPEN_PROB: dict[str, float] = {
    "novice":       0.0,
    "intermediate": 0.2,
    "advanced":     0.4,
    "expert":       0.7,
}


def select_question_type(user_level: str) -> str:
    """Return 'mcq' or 'open' based on level-weighted probability."""
    prob = _OPEN_PROB.get(user_level, 0.0)
    if prob == 0.0:
        return "mcq"
    return "open" if random.random() < prob else "mcq"


def select_mcq_question(state: AgentState) -> tuple[str, int] | None:
    """Select the next MCQ topic and question variant for this learner.

    Returns (slug, question_index) or None if no valid slug matches.
    """
    slug = _select_slug(state)
    if slug is None:
        return None
    messages = state.get("messages") or []
    return slug, len(messages) % get_mcq_count(slug)


def select_open_question(state: AgentState) -> tuple[str, int] | None:
    """Select the next open question topic and index for this learner.

    Returns (slug, question_index) or None if no valid slug matches.
    """
    slug = _select_slug(state)
    if slug is None:
        return None
    messages = state.get("messages") or []
    return slug, len(messages) % get_open_question_count(slug)


def _select_slug(state: AgentState) -> str | None:
    user_level: str = state.get("user_level") or "novice"
    eligible: frozenset[str] = _LEVEL_TO_PHASE.get(user_level, PHASE_1_TOPICS)
    gaps: list[str] = state.get("identified_gaps") or []

    # Intermediate learners normally test Phase 2 topics; weak Phase 1 gaps still get Phase 1 MCQs first
    if user_level == "intermediate" and gaps:
        for slug in gaps:
            if slug in PHASE_1_TOPICS and slug in VALID_MODULE_SLUGS:
                return slug

    if gaps:
        for slug in gaps:
            if slug in eligible and slug in VALID_MODULE_SLUGS:
                return slug

    for slug in _ORDERED_SLUGS:
        if slug in eligible and slug in VALID_MODULE_SLUGS:
            return slug
    return None
