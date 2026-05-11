"""
Pure-function scoring service for profile mastery computation.

Nova's update_profile_node imports compute_topic_scores and TopicScoreUpdate
from this module. No DB access, no FastAPI imports, no side effects.

Scoring formula (authoritative source: knowledge-base/curriculum/gates.md):
  session_score = mean(question_scores_in_session)  -- computed by assess_node
  topic_score = 0.7 * session_score + 0.3 * best_prior_session_score
  If no prior session: topic_score = session_score
  Topics with no sessions: score = None (not 0.0)
"""

from __future__ import annotations

import logging
from typing import Literal, TypedDict

logger = logging.getLogger(__name__)

# Phase gate definitions (from knowledge-base/curriculum/gates.md)
_PHASE_1_TOPICS: frozenset[str] = frozenset({"embeddings_and_similarity", "rag_pipeline_architecture"})
_PHASE_2_TOPICS: frozenset[str] = frozenset({"chunking_strategies", "vector_databases", "retrieval_methods", "context_and_prompting"})
_PHASE_3_TOPICS: frozenset[str] = frozenset({"evaluation_and_metrics", "production_patterns"})

_PHASE_1_THRESHOLD: float = 0.70
_PHASE_2_INDIVIDUAL_THRESHOLD: float = 0.70
_PHASE_2_MEAN_THRESHOLD: float = 0.75
_PHASE_3_THRESHOLD: float = 0.75


class TopicScoreUpdate(TypedDict):
    topic_scores: dict[str, float | None]
    session_history: dict[str, list[float]]
    strengths: list[str]
    gaps: list[str]
    mastery_level: Literal["novice", "beginner", "intermediate", "advanced", "expert"]


def _phase_1_passed(scores: dict[str, float | None]) -> bool:
    """True if all Phase 1 topic scores >= 0.70. None always fails."""
    for slug in _PHASE_1_TOPICS:
        s = scores.get(slug)
        if s is None or s < _PHASE_1_THRESHOLD:
            return False
    return True


def _phase_2_passed(scores: dict[str, float | None]) -> bool:
    """True if all Phase 2 per-topic scores >= 0.70 AND mean >= 0.75. None always fails."""
    topic_scores: list[float] = []
    for slug in _PHASE_2_TOPICS:
        s = scores.get(slug)
        if s is None or s < _PHASE_2_INDIVIDUAL_THRESHOLD:
            return False
        topic_scores.append(s)
    if not topic_scores:
        return False
    return (sum(topic_scores) / len(topic_scores)) >= _PHASE_2_MEAN_THRESHOLD


def _phase_3_passed(scores: dict[str, float | None]) -> bool:
    """True if all Phase 3 topic scores >= 0.75. None always fails."""
    for slug in _PHASE_3_TOPICS:
        s = scores.get(slug)
        if s is None or s < _PHASE_3_THRESHOLD:
            return False
    return True


def get_mastery_level(
    topic_scores: dict[str, float | None],
) -> Literal["novice", "beginner", "intermediate", "advanced", "expert"]:
    """Return mastery level from phase gate state. Evaluated expert → novice; first match wins.

    None scores are excluded from phase computations — they are not treated as 0.0.
    """
    p1 = _phase_1_passed(topic_scores)
    p2 = _phase_2_passed(topic_scores)
    p3 = _phase_3_passed(topic_scores)

    if p1 and p2 and p3:
        return "expert"
    if p1 and p2:
        return "advanced"
    if p1:
        return "intermediate"
    # beginner: at least one Phase 1 topic has a non-null score, phase_1 not passed
    if any(topic_scores.get(slug) is not None for slug in _PHASE_1_TOPICS):
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
