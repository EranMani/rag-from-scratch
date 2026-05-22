_VERDICT_SCORE: dict[str, float] = {
    "correct": 1.0,
    "partial": 0.5,
    "incorrect": 0.0,
}

# Rewards query sophistication with capped mastery increments (max 0.3)
_PASSIVE_LEVEL_SCORE: dict[str, float] = {
    "novice": 0.05,
    "beginner": 0.1,
    "intermediate": 0.2,
    "advanced": 0.25,
    "expert": 0.3,
}

# Minimum confidence to accept passive inference into the skill profile
_PASSIVE_CONFIDENCE_THRESHOLD: float = 0.4
