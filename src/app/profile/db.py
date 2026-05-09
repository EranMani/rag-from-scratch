import sqlite3
from pathlib import Path
from app.core.config import settings


def _connect() -> sqlite3.Connection:
    path = Path(settings.sqlite_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_profile_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id                TEXT PRIMARY KEY,
                user_id           TEXT NOT NULL UNIQUE,
                mastery_level     TEXT NOT NULL DEFAULT 'novice',
                interaction_count INTEGER NOT NULL DEFAULT 0,
                topic_scores      TEXT NOT NULL DEFAULT '{}',
                strengths         TEXT NOT NULL DEFAULT '[]',
                gaps              TEXT NOT NULL DEFAULT '[]',
                last_activity_at  TEXT,
                created_at        TEXT NOT NULL,
                updated_at        TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()
