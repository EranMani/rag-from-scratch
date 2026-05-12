from pydantic import BaseModel


class UserProfilePublic(BaseModel):
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
