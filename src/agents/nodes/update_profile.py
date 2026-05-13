"""
update_profile_node — LangGraph node that persists topic score deltas to the user profile.

Flow Diagram:
                    ┌────────────────────┐
                    │ update_profile_node │
                    └─────────┬──────────┘
                              │
                    ┌─────────┴──────────┐
                    │  user_id is None?  │
                    └─────────┬──────────┘
                     Yes │          │ No
                      ▼            ▼
                  ┌───────┐   ┌───────────────────┐
                  │ EXIT  │   │get_profile_by_user │
                  │  {}   │   └────────┬──────────┘
                  └───────┘            │
                              ┌────────┴──────────┐
                              │  profile is None? │
                              └────────┬──────────┘
                               Yes │        │ No
                                ▼          ▼
                            ┌───────┐  ┌──────────────────┐
                            │ EXIT  │  │ assessment_error? │
                            │  {}   │  └────────┬─────────┘
                            └───────┘   Yes │        │ No
                                         ▼          ▼
                              ┌────────────────┐ ┌────────────────────┐
                              │ update_profile │ │compute_topic_scores│
                              │(count++ only)  │ │  (merge delta)     │
                              └───────┬────────┘ └────────┬───────────┘
                                      │                   │
                                      ▼                   ▼
                                  ┌───────┐     ┌───────────────┐
                                  │ EXIT  │     │ update_profile │
                                  │  {}   │     │(scores + count)│
                                  └───────┘     └───────┬───────┘
                                                        │
                                                        ▼
                                                    ┌───────┐
                                                    │ EXIT  │
                                                    │  {}   │
                                                    └───────┘

Node contract:
    Input:  AgentState.user_id             (str | None)    — None for anonymous
            AgentState.assessment_error    (bool)          — True skips score write
            AgentState.topic_scores_delta  (dict[str, float]) — sparse per-turn delta
            AgentState.identified_gaps     (list[str])     — low-understanding slugs
    Output: {}   — node does not modify AgentState

Design notes:
- Synchronous node. Called from asyncio.to_thread() at the graph invocation level in
  chat.py — do not introduce nested thread dispatch or asyncio calls here.
- Fast-exit paths return {} without touching the DB:
    1. user_id is None (anonymous user — no profile to update)
    2. profile row does not exist (creation is the auth layer's responsibility)
- assessment_error=True: only increments interaction_count (eventual consistency).
- compute_topic_scores receives the full profile dict (not just profile['topic_scores']).
  get_profile_by_user_id already deserializes topic_scores from JSON; do NOT call
  json.loads() on it before passing it here.
- last_activity_at is always set on successful write.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from agents.state import AgentState
from app.profile.db import get_profile_by_user_id, update_profile
from app.profile.scoring import TopicScoreUpdate, compute_topic_scores

logger = logging.getLogger(__name__)


def update_profile_node(state: AgentState) -> dict[str, Any]:
    """Persist topic score deltas to the user profile DB. See module docstring for contract."""

    user_id: str | None = state.get("user_id")
    assessment_error: bool = state.get("assessment_error", False)

    # Fast-exit path 1: anonymous user
    if user_id is None:
        logger.debug("update_profile_node: user_id is None — skipping profile update")
        return {}

    # Fetch the current profile row (needed for both happy path and error path)
    current_profile: dict | None = get_profile_by_user_id(user_id)
    if current_profile is None:
        logger.warning(
            "update_profile_node: no profile found for user_id=%s — "
            "profile creation is the auth layer's responsibility; skipping update",
            user_id,
        )
        return {}

    interaction_count: int = current_profile.get("interaction_count", 0)

    # Error path: only bump interaction count, don't touch scores
    if assessment_error:
        logger.debug(
            "update_profile_node: assessment_error=True — incrementing interaction_count "
            "only for user_id=%s",
            user_id,
        )
        update_profile(
            user_id,
            interaction_count=interaction_count + 1,
            last_activity_at=datetime.now(timezone.utc).isoformat(),
        )
        return {}

    # Happy path: merge delta into existing scores and compute derived fields
    topic_scores_delta: dict[str, float] = state.get("topic_scores_delta", {})

    score_update: TopicScoreUpdate = compute_topic_scores(
        current_profile,
        topic_scores_delta,
    )

    update_profile(
        user_id,
        topic_scores=score_update["topic_scores"],
        session_history=score_update["session_history"],
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
