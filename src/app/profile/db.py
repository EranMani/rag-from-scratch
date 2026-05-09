import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from app.core.config import settings

# Allowlist of column names that update_profile() is permitted to write.
# Column names are interpolated into the SQL SET clause; this guard prevents
# a caller-supplied key from becoming a structural injection path.
_ALLOWED_PROFILE_COLUMNS: frozenset[str] = frozenset({
    "mastery_level",
    "interaction_count",
    "topic_scores",
    "strengths",
    "gaps",
    "last_activity_at",
})


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


def create_profile(user_id: str) -> str:
    """Insert a new profile row for user_id with default values. Returns the profile_id (UUID).

    Raises sqlite3.IntegrityError if a profile for user_id already exists or if user_id
    does not reference a valid users(id) row (FK violation).
    """
    profile_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO user_profiles
                (id, user_id, mastery_level, interaction_count,
                 topic_scores, strengths, gaps, last_activity_at,
                 created_at, updated_at)
            VALUES (?, ?, 'novice', 0, '{}', '[]', '[]', NULL, ?, ?)
            """,
            (profile_id, user_id, now, now),
        )
        conn.commit()
    return profile_id


def _deserialize_row(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row from user_profiles into a Python dict.

    topic_scores, strengths, and gaps are stored as JSON strings in the DB.
    They are deserialized here so callers never receive raw JSON strings.
    """
    d = dict(row)
    d["topic_scores"] = json.loads(d["topic_scores"])
    d["strengths"] = json.loads(d["strengths"])
    d["gaps"] = json.loads(d["gaps"])
    return d


def get_profile_by_user_id(user_id: str) -> dict | None:
    """Return the profile for user_id as a Python dict, or None if not found.

    topic_scores is returned as dict[str, float], strengths and gaps as list[str].
    """
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    return _deserialize_row(row)


def update_profile(user_id: str, **fields) -> None:
    """Partial update — only columns passed as kwargs are written.

    topic_scores, strengths, and gaps are automatically serialized to JSON strings
    before the UPDATE. updated_at is always refreshed.

    Raises ValueError if called with no fields to update.
    Raises ValueError if an unknown column name is passed (not in _ALLOWED_PROFILE_COLUMNS).
    """
    if not fields:
        raise ValueError(
            f"update_profile called with no fields for user_id='{user_id}' — "
            "pass at least one keyword argument to update."
        )

    invalid = set(fields) - _ALLOWED_PROFILE_COLUMNS
    if invalid:
        raise ValueError(
            f"update_profile: unknown column(s) {invalid!r} — "
            f"allowed: {_ALLOWED_PROFILE_COLUMNS}"
        )

    # Serialize JSON fields before writing
    for json_col in ("topic_scores", "strengths", "gaps"):
        if json_col in fields:
            fields[json_col] = json.dumps(fields[json_col])

    fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    values = list(fields.values()) + [user_id]

    with _connect() as conn:
        conn.execute(
            f"UPDATE user_profiles SET {set_clause} WHERE user_id = ?",
            values,
        )
        conn.commit()


def get_or_create_profile(user_id: str) -> dict:
    """Return the existing profile for user_id, creating one if it does not exist.

    Safe to call on every request — no duplicate inserts. The check-then-create
    is not wrapped in a transaction because user_profiles has a UNIQUE constraint
    on user_id; a race-condition duplicate insert would raise IntegrityError,
    not silently create a duplicate.
    """
    profile = get_profile_by_user_id(user_id)
    if profile is None:
        try:
            create_profile(user_id)
        except sqlite3.IntegrityError:
            pass  # concurrent insert won the race; fetch the winner's row
        profile = get_profile_by_user_id(user_id)
    return profile
