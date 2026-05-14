"""
Pydantic schemas — the public contract for the user's knowledge state.

These schemas define how both the frontend and the AI agent see the user's
mastery data. Pydantic validates every value coming out of profile/db.py before
it reaches the client, ensuring malformed or corrupted DB rows never leak into
the response or into the agent's reasoning.

Relationship to the system:
    profile/db.py (raw storage) → _deserialize_row → UserProfilePublic (typed output)

    The agent graph also consumes these same fields (via get_or_create_profile)
    to decide adaptive prompting level and curriculum next-steps.
"""


from pydantic import BaseModel


class UserProfilePublic(BaseModel):
    """Safe outbound representation of a user's mastery profile.

    Excludes the internal profile `id` (primary key) — only `user_id` is exposed.
    This follows Least Privilege: the client and agent receive exactly the fields
    they need to render the dashboard or personalize the next turn, nothing more.

    Field roles:
        mastery_level     — behavioral anchor (drives adaptive-prompting tone)
        interaction_count — confidence denominator for topic scores
        topic_scores      — the Knowledge Map (None = unassessed, float = scored)
        session_history   — per-topic score progression over time (for charts/spaced repetition)
        strengths / gaps  — pre-computed heuristic filters for curriculum decisions
        last_activity_at  — enables recency-aware greetings and review triggers
    """
    user_id: str
    mastery_level: str
    interaction_count: int
    topic_scores: dict[str, float | None]
    session_history: dict[str, list[float]]
    strengths: list[str]
    gaps: list[str]
    last_activity_at: str | None
    created_at: str
    updated_at: str
