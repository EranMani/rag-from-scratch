"""
Pure-function scoring service for profile mastery computation.

Nova's update_profile_node (Commit 15) imports compute_topic_scores and
TopicScoreUpdate from this module. No DB access, no FastAPI imports, no side effects.
"""

from typing import TypedDict


class TopicScoreUpdate(TypedDict):
    topic_scores: dict[str, float]
    strengths: list[str]
    gaps: list[str]
    mastery_level: str


def get_mastery_level(topic_scores: dict[str, float]) -> str:
    """Return mastery level string from average of all scores in topic_scores.

    Empty dict returns 'novice' — no scores means no knowledge.
    """
    if not topic_scores:
        return "novice"
    avg = sum(topic_scores.values()) / len(topic_scores)
    if avg < 0.2:
        return "novice"
    if avg < 0.4:
        return "beginner"
    if avg < 0.6:
        return "intermediate"
    if avg < 0.8:
        return "advanced"
    return "expert"


def compute_topic_scores(
    current_profile: dict,
    assessed_topics: dict[str, float],
    interaction_count: int,
) -> TopicScoreUpdate:
    """Merge assessed_topics deltas into current_profile['topic_scores'] and compute mastery.

    Invalid module slugs in assessed_topics are ignored gracefully — no exception raised.
    current_profile['topic_scores'] is expected to be dict[str, float] (already deserialized).
    interaction_count is accepted but not used in scoring computation; reserved for Nova's node.
    """
    merged: dict[str, float] = dict(current_profile.get("topic_scores", {}))
    for slug, score in assessed_topics.items():
        # Accept any float in [0.0, 1.0]; clamp silently to keep invariants
        if isinstance(score, (int, float)):
            merged[slug] = float(max(0.0, min(1.0, score)))

    strengths: list[str] = [slug for slug, score in merged.items() if score >= 0.7]
    gaps: list[str] = [slug for slug, score in merged.items() if score <= 0.3]
    mastery_level: str = get_mastery_level(merged)

    return TopicScoreUpdate(
        topic_scores=merged,
        strengths=strengths,
        gaps=gaps,
        mastery_level=mastery_level,
    )
