"""
Scoring constants for verdict evaluation, passive mastery increments,
and the confidence threshold for accepting passive skill inference.
"""

# Open-ended questions only — MCQ uses binary scoring
_VERDICT_SCORE: dict[str, float] = {
    "correct": 1.0,
    "partial": 0.5,
    "incorrect": 0.0,
}

# Score added to a topic when the user engages at their current mastery level
_PASSIVE_LEVEL_SCORE: dict[str, float] = {
    "novice": 0.05,
    "beginner": 0.1,
    "intermediate": 0.2,
    "advanced": 0.25,
    "expert": 0.3,
}

# Minimum confidence in the slug inference to update the skill profile
_PASSIVE_CONFIDENCE_THRESHOLD: float = 0.4
