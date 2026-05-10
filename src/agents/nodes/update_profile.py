"""
update_profile_node — LangGraph node that persists topic score deltas to the user profile.

Node contract:
    Input:  AgentState.user_id             (str | None)    — None for anonymous
            AgentState.assessment_error    (bool)          — True skips profile write
            AgentState.topic_scores_delta  (dict[str, float]) — sparse per-turn delta
            AgentState.identified_gaps     (list[str])     — low-understanding slugs
    Output: {}   — node does not modify AgentState

Design notes:
- Synchronous node.  Called from asyncio.to_thread() at the graph invocation level in
  chat.py — do not introduce nested thread dispatch or asyncio calls here.
- Two fast-exit paths return {} without touching the DB:
    1. user_id is None (anonymous user — no profile to update)
    2. assessment_error is True (fallback path — empty delta; eventual consistency design)
- If the profile row does not exist for user_id, the node logs a warning and exits
  cleanly.  Profile creation is the responsibility of the auth layer (Commit 06),
  not this node.
- compute_topic_scores receives the full profile dict (not just profile['topic_scores']).
  get_profile_by_user_id already deserializes topic_scores from JSON; do NOT call
  json.loads() on it before passing it here.
- interaction_count is passed to compute_topic_scores even though the scoring formula
  does not use it — it belongs to the function contract (Commit 14).
- last_activity_at is always set on successful write (Commit 05 Mira handoff).
"""

import logging
from datetime import datetime, timezone
from typing import Any

from agents.state import AgentState
from app.profile.db import get_profile_by_user_id, update_profile
from app.profile.scoring import TopicScoreUpdate, compute_topic_scores

logger = logging.getLogger(__name__)


def update_profile_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: merge topic_scores_delta into the persistent user profile.

    Returns an empty dict — this node does not modify any AgentState fields.
    All side effects are DB writes via update_profile().
    """
    user_id: str | None = state.get("user_id")  # type: ignore[call-overload]
    assessment_error: bool = state.get("assessment_error", False)  # type: ignore[call-overload]

    # Fast-exit path 1: anonymous user
    if user_id is None:
        logger.debug("update_profile_node: user_id is None — skipping profile update")
        return {}

    # Fast-exit path 2: assessment failed — do not persist a bad delta
    if assessment_error:
        logger.debug(
            "update_profile_node: assessment_error=True — skipping profile update "
            "for user_id=%s",
            user_id,
        )
        return {}

    # Fetch the current profile row
    current_profile: dict | None = get_profile_by_user_id(user_id)
    if current_profile is None:
        logger.warning(
            "update_profile_node: no profile found for user_id=%s — "
            "profile creation is the auth layer's responsibility; skipping update",
            user_id,
        )
        return {}

    # Merge delta into existing scores and compute derived fields
    topic_scores_delta: dict[str, float] = state.get(  # type: ignore[call-overload]
        "topic_scores_delta", {}
    )
    interaction_count: int = current_profile.get("interaction_count", 0)

    score_update: TopicScoreUpdate = compute_topic_scores(
        current_profile,
        topic_scores_delta,
        interaction_count,
    )

    # Persist all updated fields in a single DB write.
    # AgentState.identified_gaps maps to the DB column "gaps".
    # score_update["gaps"] is the low-score set derived from merged topic_scores;
    # identified_gaps from the LLM assessment is the per-turn signal — we write the
    # scoring-derived gaps (score_update["gaps"]) which reflects the full merged state.
    update_profile(
        user_id,
        topic_scores=score_update["topic_scores"],
        strengths=score_update["strengths"],
        gaps=score_update["gaps"],
        mastery_level=score_update["mastery_level"],
        interaction_count=interaction_count + 1,
        last_activity_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.debug(
        "update_profile_node: updated profile for user_id=%s — "
        "interaction_count=%d mastery_level=%s",
        user_id,
        interaction_count + 1,
        score_update["mastery_level"],
    )

    return {}
