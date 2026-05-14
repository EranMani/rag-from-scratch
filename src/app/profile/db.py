"""
Long-Term Memory (LTM) store for the adaptive agent.

While LangGraph handles short-term memory (within a thread/session), this module
owns the persistent mastery state that spans weeks or months. It bridges the gap
between probabilistic AI assessments and deterministic user records, providing the
longitudinal data required for curriculum personalization and skill progression.

Core principle: A database for an AI agent is not a warehouse — it is a Feedback
Loop. Every interaction updates the Mastery Model (state), which informs the next
retrieval (output). This file is the engine that drives that loop.

Architecture — five design pillars:

1. Mastery Model (Knowledge as State):
    topic_scores (JSON) is the user's "Knowledge Map" — high-dimensional skill
    tracking without rigid SQL columns. mastery_level is the behavioral anchor
    that dictates how the LLM adjusts tone and complexity (see adaptive-prompting).
    strengths & gaps are pre-computed heuristic filters so the agent doesn't
    re-analyze the full history every turn.

2. Long-Term Memory Persistence:
    session_history and last_activity_at enable spaced repetition and
    context-aware greetings based on time since last interaction.
    interaction_count is the "confidence denominator" — a high topic score after
    100 turns is statistically meaningful; after 1 turn it's a lucky guess.

3. Structural Guardrails (AI Safety Net):
    _ALLOWED_PROFILE_COLUMNS acts as a hard allowlist. If the LLM hallucinates
    an update to a non-existent field, the system rejects it before SQL is built.
    _deserialize_row ensures the agent always receives clean Python objects,
    preventing type errors during the LLM's reasoning phase.

4. Concurrency (WAL & Async Pattern):
    WAL mode allows simultaneous reads/writes — essential for frequent "assess
    and update" cycles. asyncio.to_thread (called upstream in the API layer)
    keeps the event loop free while this synchronous SQLite code executes.

5. Idempotent State Management:
    get_or_create_profile guarantees the agent never encounters a "memory-less"
    user, silently handling race conditions. migrate_topic_slugs lets the
    curriculum evolve (add/rename topics) without losing existing user progress.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

# Allowlist of columns the agent is permitted to update.
# frozenset is immutable — no code path can expand the attack surface at runtime.
# Any column not listed here is rejected before SQL is constructed.
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
    # Row object — supports both row['email'] key access and row[0] index access
    conn.row_factory = sqlite3.Row
    # NOTE: Allows to read from the database while being written to it, avoiding it being locked
    # When running commit, the changes are saved into a helper called wal-file
    # It allows the agent to keep reading from the main db without waiting for the writing to be fully complete
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_profile_db() -> None:
    """Create the user_profiles table if it doesn't exist. Safe to call on every startup.

    Key schema decisions:
        user_id UNIQUE  — one profile per user (1:1 with the identity in auth/db.py).
        FOREIGN KEY ... ON DELETE CASCADE — deleting a user auto-removes their mastery data.
        JSON columns (topic_scores, strengths, gaps) — NoSQL-like flexibility for
            high-dimensional skill tracking within a relational integrity shell.
    """
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
        # Idempotent column migration for DBs created before session_history existed.
        # ALTER TABLE fails if the column is already there — the try/except makes it safe
        # to re-run on every startup. DEFAULT '{}' ensures json.loads() won't crash on
        # existing rows that never had this column.
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
    """Convert a raw sqlite3.Row into a Python dict the agent graph can consume.

    JSON columns are parsed back into native Python types (dict/list) so that
    downstream LLM logic and graph nodes receive structured objects — never raw
    strings that would cause type errors during reasoning.
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
    """Partial update — persist only the columns passed as kwargs.

    This is the LTM writer: everything the agent learns about the user during a
    session is safely committed to disk here.

    Raises ValueError if called with no fields or with column names outside
    _ALLOWED_PROFILE_COLUMNS (the hallucination guard).
    """
    if not fields:
        raise ValueError(
            f"update_profile called with no fields for user_id='{user_id}' — "
            "pass at least one keyword argument to update."
        )

    # Set difference identifies any column names the LLM might hallucinate.
    # Sets are optimized for membership tests — O(1) per lookup.
    invalid = set(fields) - _ALLOWED_PROFILE_COLUMNS
    if invalid:
        raise ValueError(
            f"update_profile: unknown column(s) {invalid!r} — "
            f"allowed: {_ALLOWED_PROFILE_COLUMNS}"
        )

    # JSON columns must be serialized to TEXT before SQLite can store them
    for json_col in ("topic_scores", "session_history", "strengths", "gaps"):
        if json_col in fields:
            fields[json_col] = json.dumps(fields[json_col])

    fields["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Build SET clause dynamically: "mastery_level = ?, interaction_count = ?"
    # Parameterized ? placeholders prevent SQL injection
    set_clause = ", ".join(f"{col} = ?" for col in fields)
    values = list(fields.values()) + [user_id]

    with _connect() as conn:
        conn.execute(
            f"UPDATE user_profiles SET {set_clause} WHERE user_id = ?",
            values,
        )
        conn.commit()


def get_or_create_profile(user_id: str) -> dict:
    """Guarantee a valid profile exists — the agent never encounters a "memory-less" user.

    Handles the race condition where two concurrent requests for the same user both
    see profile=None and try to INSERT simultaneously. The loser's IntegrityError is
    caught silently, and both callers end up reading the same row.
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
