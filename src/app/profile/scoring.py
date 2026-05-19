"""
Scoring engine — deterministic rules that convert raw assessment scores into mastery levels.

The LLM evaluates answers (probabilistic), but this module decides the user's status
(deterministic). This separation ensures objectivity: the agent cannot "feel" that a
user is advanced — it must prove it through the numbers defined here.

Why this matters for the adaptive agent:
    The mastery_level produced here is the single most influential variable on the
    prompt. It drives the entire adaptive-prompting system:
        novice  → roadmap tone ("Let's start with what an Embedding is...")
        expert  → dense, skip basics ("Since you know Vector DBs, let's optimize retrieval...")

    These thresholds are the "syllabus" of the system — they define the professional
    standard required to progress through the learning journey in AgentCanvas.

Personalized curriculum example:
    If a user averages 0.72 across Phase 2 topics (threshold is 0.75), the agent can
    tell them: "You're close to the next level — let's strengthen Vector DBs to get
    you there." The numbers make this coaching specific and actionable.
"""

from __future__ import annotations

import logging
from typing import Literal, TypedDict

logger = logging.getLogger(__name__)

# Phase gate definitions (from knowledge-base/curriculum/gates.md).
# frozenset: immutable + O(1) membership lookup — safe and fast when the agent
# checks user progress multiple times per turn.
PHASE_1_TOPICS: frozenset[str] = frozenset({"embeddings_and_similarity", "rag_pipeline_architecture"})
PHASE_2_TOPICS: frozenset[str] = frozenset({"chunking_strategies", "vector_databases", "retrieval_methods", "context_and_prompting"})
PHASE_3_TOPICS: frozenset[str] = frozenset({"evaluation_and_metrics", "production_patterns"})

# Academic standards — the score a user must demonstrate to advance.
# These thresholds are the "syllabus gates" of the system.
_PHASE_1_THRESHOLD: float = 0.70       # Each Phase 1 topic must reach 70%
_PHASE_2_INDIVIDUAL_THRESHOLD: float = 0.70  # Each Phase 2 topic must reach 70% individually
_PHASE_2_MEAN_THRESHOLD: float = 0.75  # Phase 2 also requires 75% average across all topics
_PHASE_3_THRESHOLD: float = 0.75       # Higher bar — user is expected to demonstrate deep accuracy


class TopicScoreUpdate(TypedDict):
    """Typed payload returned from scoring to the agent graph and profile/db.py.

    TypedDict ensures every downstream consumer (profile_update_node, generate_node)
    receives exactly the shape it expects — no missing keys, no type surprises.
    """
    topic_scores: dict[str, float | None]       # slug → score (None = unassessed)
    session_history: dict[str, list[float]]     # slug → list of prior session scores
    strengths: list[str]                        # slugs scoring >= 0.7
    gaps: list[str]                             # slugs scoring <= 0.3
    mastery_level: Literal["novice", "beginner", "intermediate", "advanced", "expert"]


def _phase_1_passed(scores: dict[str, float | None]) -> bool:
    """True if all Phase 1 topic scores >= 0.70. None (unassessed) always fails."""
    for slug in PHASE_1_TOPICS:
        s = scores.get(slug)
        if s is None or s < _PHASE_1_THRESHOLD:
            return False
    return True


def _phase_2_passed(scores: dict[str, float | None]) -> bool:
    """True if every Phase 2 topic >= 0.70 AND their mean >= 0.75. None always fails.

    The dual gate (individual + average) requires both depth per topic AND breadth
    across the full RAG knowledge domain — pointed skill alone isn't enough.
    """
    topic_scores: list[float] = []
    for slug in PHASE_2_TOPICS:
        s = scores.get(slug)
        if s is None or s < _PHASE_2_INDIVIDUAL_THRESHOLD:
            return False
        topic_scores.append(s)
    if not topic_scores:
        return False
    return (sum(topic_scores) / len(topic_scores)) >= _PHASE_2_MEAN_THRESHOLD


def _phase_3_passed(scores: dict[str, float | None]) -> bool:
    """True if all Phase 3 topic scores >= 0.75. None always fails."""
    for slug in PHASE_3_TOPICS:
        s = scores.get(slug)
        if s is None or s < _PHASE_3_THRESHOLD:
            return False
    return True


def get_mastery_level(
    topic_scores: dict[str, float | None],
) -> Literal["novice", "beginner", "intermediate", "advanced", "expert"]:
    """Translate raw topic scores into a single mastery label for the agent.

    This label is the behavioral anchor that adaptive-prompting reads to select
    the correct prompt template. It turns dry numbers in the DB into a clear
    learning identity the agent uses to mentor each user personally.
    """
    p1 = _phase_1_passed(topic_scores)
    p2 = _phase_2_passed(topic_scores)
    p3 = _phase_3_passed(topic_scores)

    # Evaluate top-down: highest level first, fall through until one matches
    if p1 and p2 and p3:
        return "expert"
    if p1 and p2:
        return "advanced"
    if p1:
        return "intermediate"
    # beginner: at least one Phase 1 topic has a non-null score, phase_1 not passed
    if any(topic_scores.get(slug) is not None for slug in PHASE_1_TOPICS):
        return "beginner"
    return "novice"


def compute_topic_scores(
    current_profile: dict,
    topic_scores_delta: dict[str, float],
) -> TopicScoreUpdate:
    """Apply session scores from topic_scores_delta to current_profile using spaced-repetition formula.

    topic_scores_delta: {slug: session_score} — the current session's score per topic.
    These are absolute session scores (0.0–1.0), NOT deltas to be added to existing scores.

    Formula (from gates.md):
      topic_score = 0.7 * current_session_score + 0.3 * best_prior_session_score
      If no prior session: topic_score = current_session_score

    Slugs with non-float values in topic_scores_delta are flagged and skipped.
    Session scores outside [0.0, 1.0] are clamped before storage.
    """
    # Read existing state; session_history stores per-topic list of prior session scores
    merged: dict[str, float | None] = dict(current_profile.get("topic_scores", {}))
    history: dict[str, list[float]] = {
        k: list(v) for k, v in current_profile.get("session_history", {}).items()
    }

    for slug, session_score in topic_scores_delta.items():
        if not isinstance(session_score, (int, float)):
            logger.warning(
                "compute_topic_scores: non-numeric session score for slug=%r value=%r — skipped",
                slug, session_score,
            )
            continue

        current_session = float(max(0.0, min(1.0, session_score)))
        prior_sessions = history.get(slug, [])

        if prior_sessions:
            best_prior = max(prior_sessions)
            topic_score = 0.7 * current_session + 0.3 * best_prior
        else:
            topic_score = current_session

        merged[slug] = round(topic_score, 10)
        # Append current session score to history for future best_prior lookups
        history.setdefault(slug, []).append(current_session)

    strengths: list[str] = [
        slug for slug, score in merged.items()
        if score is not None and score >= 0.7
    ]
    gaps: list[str] = [
        slug for slug, score in merged.items()
        if score is not None and score <= 0.3
    ]
    mastery_level = get_mastery_level(merged)

    return TopicScoreUpdate(
        topic_scores=merged,
        session_history=history,
        strengths=strengths,
        gaps=gaps,
        mastery_level=mastery_level,
    )
