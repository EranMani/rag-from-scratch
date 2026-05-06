import json
from pathlib import Path
from datetime import datetime
from app.core.logging_config import logger

PROFILES_DIR = Path("data/user_profiles")
PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def load_profile(user_id: str) -> dict:
    pass