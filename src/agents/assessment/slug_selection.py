from agents.mcq_utils import get_mcq_count
from agents.state import VALID_MODULE_SLUGS, AgentState
from app.profile.scoring import PHASE_1_TOPICS, PHASE_2_TOPICS, PHASE_3_TOPICS

_ALL_TOPICS: frozenset[str] = PHASE_1_TOPICS | PHASE_2_TOPICS | PHASE_3_TOPICS

_LEVEL_TO_PHASE: dict[str, frozenset[str]] = {
    "novice":       PHASE_1_TOPICS,
    "beginner":     PHASE_1_TOPICS,
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


def _select_test_slug(state: AgentState) -> str | None:
    """Pick the next MCQ topic slug for this learner.

    Order: intermediate Phase 1 gaps → any eligible gap → first eligible slug in _ORDERED_SLUGS.
    Returns None if no valid slug matches.
    """
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


def _select_mcq_question_index(state: AgentState, slug: str) -> int:
    """Deterministically select a question index based on conversation depth."""
    messages = state.get("messages") or []
    mcq_count = get_mcq_count(slug)
    return len(messages) % mcq_count
