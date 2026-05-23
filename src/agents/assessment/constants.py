"""
Scoring constants for verdict evaluation, passive mastery increments,
and the confidence threshold for accepting passive skill inference.
"""

_PASSIVE_SCORE_BASE: float = 0.05
_PASSIVE_SCORE_MID: float = 0.07
_PASSIVE_SCORE_EXPERT: float = 0.1

# Open-ended questions only — MCQ uses binary scoring
_VERDICT_SCORE: dict[str, float] = {
    "correct": 1.0,
    "partial": 0.5,
    "incorrect": 0.0,
}

# Score added to a topic when the user engages at their current mastery level
_PASSIVE_LEVEL_SCORE: dict[str, float] = {
    "novice": _PASSIVE_SCORE_BASE,
    "intermediate": _PASSIVE_SCORE_MID,
    "advanced": _PASSIVE_SCORE_MID,
    "expert": _PASSIVE_SCORE_EXPERT,
}

# Minimum confidence in the slug inference to update the skill profile
_PASSIVE_CONFIDENCE_THRESHOLD: float = 0.4
