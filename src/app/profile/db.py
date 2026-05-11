import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

# Allowlist of column names that update_profile() is permitted to write.
# Column names are interpolated into the SQL SET clause; this guard prevents
# a caller-supplied key from becoming a structural injection path.
_ALLOWED_PROFILE_COLUMNS: frozenset[str] = frozenset({
    "mastery_level",
    "interaction_count",
    "topic_scores",
    "session_history",
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
                session_history   TEXT NOT NULL DEFAULT '{}',
                strengths         TEXT NOT NULL DEFAULT '[]',
                gaps              TEXT NOT NULL DEFAULT '[]',
                last_activity_at  TEXT,
                created_at        TEXT NOT NULL,
                updated_at        TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        # Idempotent column add for existing DBs created before Commit 25
        try:
            conn.execute("ALTER TABLE user_profiles ADD COLUMN session_history TEXT NOT NULL DEFAULT '{}'")
        except sqlite3.OperationalError:
            pass  # column already exists
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

    topic_scores, session_history, strengths, and gaps are stored as JSON strings in the DB.
    They are deserialized here so callers never receive raw JSON strings.
    """
    d = dict(row)
    d["topic_scores"] = json.loads(d["topic_scores"])
    d["session_history"] = json.loads(d.get("session_history") or "{}")
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
    for json_col in ("topic_scores", "session_history", "strengths", "gaps"):
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


# ---------------------------------------------------------------------------
# 8-slug schema migration (Commit 25)
# ---------------------------------------------------------------------------

_MIGRATION_SENTINEL = "rag_pipeline_architecture"
_MIGRATE_FROM = "rag_fundamentals"
_DISCARD = "langchain"
_ADD_AT_ZERO: tuple[str, ...] = (
    "embeddings_and_similarity",
    "context_and_prompting",
    "evaluation_and_metrics",
)


def migrate_topic_slugs() -> None:
    """Idempotent migration: 6-slug → 8-slug topic_scores schema.

    Runs at startup after init_profile_db(). Skips any row that already has
    rag_pipeline_architecture present (idempotency check before any mutation).

    Migration rules:
      rag_fundamentals  → copied to rag_pipeline_architecture, then removed
      langchain         → discarded (value dropped)
      embeddings_and_similarity, context_and_prompting,
      evaluation_and_metrics    → added at 0.0 if absent
    """
    with _connect() as conn:
        rows = conn.execute("SELECT user_id, topic_scores FROM user_profiles").fetchall()

    if not rows:
        return

    updates: list[tuple[str, str]] = []
    for row in rows:
        scores: dict = json.loads(row["topic_scores"])

        # Idempotency: if sentinel key already present, this row is already migrated
        if _MIGRATION_SENTINEL in scores:
            continue

        # Copy rag_fundamentals value → rag_pipeline_architecture (or 0.0 if absent)
        scores[_MIGRATION_SENTINEL] = scores.pop(_MIGRATE_FROM, None)

        # Discard langchain
        scores.pop(_DISCARD, None)

        # Add new slugs at None (unassessed) if absent
        for slug in _ADD_AT_ZERO:
            scores.setdefault(slug, None)

        updates.append((json.dumps(scores), row["user_id"]))

    if not updates:
        return

    with _connect() as conn:
        conn.executemany(
            "UPDATE user_profiles SET topic_scores = ? WHERE user_id = ?",
            updates,
        )
        conn.commit()

    logger.info("migrate_topic_slugs: migrated %d profile row(s)", len(updates))
