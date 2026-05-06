import json
from pathlib import Path
from datetime import datetime
from app.core.logging_config import logger

PROFILES_DIR = Path("data/user_profiles")
PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def load_profile(user_id: str) -> dict:
    """Load user profile from JSON file"""
    path = PROFILES_DIR / f"{user_id}.json"
    if path.exists():
        with open(path) as f:
            profile = json.load(f)

        logger.info("Profile loaded — returning user", extra={"user_id": user_id})
        return profile
    
    return {"user_id": user_id, "first_seen": datetime.now().isoformat(), "query_count": 0}

def save_profile(user_id: str, profile: dict) -> None:
    """Persist user profile to JSON"""
    # Add time update and increment query count by 1
    profile["last_seen"] = datetime.now().isoformat()
    profile["query_count"] = profile.get("query_count", 0) + 1

    # Get json file and write update to it
    path = PROFILES_DIR / f"{user_id}.json"
    with open(path, "w") as f:
        json.dump(profile, f, indent=2)
