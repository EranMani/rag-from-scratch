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
    Output: {}   — node does not modify AgentState on most paths.
            {"gate_just_passed": str} — emitted when mastery_level crosses a phase gate boundary.

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

_LEVEL_ORDER: dict[str, int] = {"novice": 0, "beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
_GATE_THRESHOLDS: dict[str, int] = {"phase_1": 2, "phase_2": 3, "phase_3": 4}


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
    is_passive_delta: bool = state.get("is_passive_delta", False)
    session_question_counts: dict[str, int] = state.get("session_question_counts") or {}
    session_count: int | None = None
    if not is_passive_delta and len(topic_scores_delta) == 1:
        active_slug = next(iter(topic_scores_delta))
        active_score = topic_scores_delta[active_slug]
        # The minimum-session guard prevents a single lucky correct answer from
        # inflating mastery on a brand-new topic. It must NOT block wrong-answer
        # penalisation (score=0.0) — failing an MCQ should always register.
        #
        # The guard only applies when the topic has NO prior session history. Once a
        # topic has been answered in any previous session (history is non-empty), single
        # correct answers update the score immediately. Without this check the counter
        # resets to 0 on every page load (new LangGraph thread_id), permanently blocking
        # updates for returning learners who have already demonstrated competence.
        if active_score > 0.0:
            prior_history = current_profile.get("session_history", {}).get(active_slug, [])
            if not prior_history:
                session_count = session_question_counts.get(active_slug)

    previous_level: str | None = current_profile.get("mastery_level")

    score_update: TopicScoreUpdate = compute_topic_scores(
        current_profile,
        topic_scores_delta,
        is_passive=is_passive_delta,
        session_question_count=session_count,
    )

    # Ratchet: mastery_level only advances, never regresses.
    # The scoring formula (0.7 × current + 0.3 × best_prior) can drop a Phase-1
    # topic below its gate threshold on a single partial answer — mathematically,
    # 0.7×0.5 + 0.3×x ≥ 0.70 requires x ≥ 1.167 (impossible). Remediation
    # questions are for practice, not re-assessment of earned phase gates.
    computed_level = score_update["mastery_level"]
    prev_rank = _LEVEL_ORDER.get(previous_level or "novice", 0)
    comp_rank = _LEVEL_ORDER.get(computed_level, 0)
    if previous_level and comp_rank < prev_rank:
        final_mastery_level = previous_level
        logger.info(
            "update_profile_node: mastery regression blocked for user_id=%s "
            "(%s → %s); retaining %s",
            user_id, previous_level, computed_level, final_mastery_level,
        )
    else:
        final_mastery_level = computed_level

    update_profile(
        user_id,
        topic_scores=score_update["topic_scores"],
        session_history=score_update["session_history"],
        strengths=score_update["strengths"],
        gaps=score_update["gaps"],
        mastery_level=final_mastery_level,
        interaction_count=interaction_count + 1,
        last_activity_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.debug(
        "update_profile_node: updated profile for user_id=%s — "
        "interaction_count=%d mastery_level=%s",
        user_id,
        interaction_count + 1,
        final_mastery_level,
    )

    old_rank = prev_rank
    new_rank = _LEVEL_ORDER.get(final_mastery_level, 0)

    gate_just_passed: str | None = None
    for gate_name, threshold in _GATE_THRESHOLDS.items():
        if old_rank < threshold <= new_rank:
            gate_just_passed = gate_name
            break  # only the highest crossed gate

    return {"gate_just_passed": gate_just_passed} if gate_just_passed else {}
