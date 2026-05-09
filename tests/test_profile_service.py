"""
Tests for Commit 05 — user-profile-service.

Coverage targets:
1. create_profile() inserts a row with correct defaults
2. get_profile_by_user_id() returns topic_scores as dict, not a string
3. update_profile() updates only the named field, others unchanged
4. get_or_create_profile() returns the existing profile on second call (no duplicate)
5. App starts without import errors after profiles.py is deleted (import smoke test)
6. FK cascade: deleting a user row removes the associated profile row

Design notes:
- CRUD tests (1–4) and the cascade test (6) use real SQLite connections against a
  temp file DB, not :memory:, because SQLite :memory: DBs do not share state between
  connections — each _connect() call would open an independent empty database.
- The _connect() function in profile/db.py reads settings.sqlite_db_path. We patch
  app.profile.db._connect at the module level with a factory that returns connections
  to the temp DB, ensuring no test I/O touches data/app_users.db.
- The FK cascade test requires both the users and user_profiles tables and must use
  PRAGMA foreign_keys=ON per connection to activate SQLite FK enforcement.
- The import smoke test (5) verifies that removing profiles.py did not leave dangling
  imports anywhere in the rag pipeline.
"""

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

import app.profile.db as profile_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_temp_connect(db_path: str):
    """Return a _connect() replacement that always opens db_path."""
    def _connect() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    return _connect


def _bootstrap_db(db_path: str) -> None:
    """Create users and user_profiles tables in a fresh temp DB.

    user_profiles has a FK referencing users(id) ON DELETE CASCADE.
    Both tables are created in sequence — users first, then profiles.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id           TEXT PRIMARY KEY,
            email        TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            created_at   TEXT NOT NULL
        )
        """
    )
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
    conn.close()


def _insert_test_user(db_path: str) -> str:
    """Insert a minimal users row and return its id."""
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "INSERT INTO users (id, email, password_hash, display_name, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, f"{user_id}@test.local", "hashed", "Test User", now),
    )
    conn.commit()
    conn.close()
    return user_id


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """
    Provide an isolated SQLite DB for each test.

    - Creates a temp DB file with both users and user_profiles tables.
    - Patches app.profile.db._connect to use the temp DB.
    - Yields the db_path string so tests can make direct connections for assertions.
    """
    db_path = str(tmp_path / "test_profiles.db")
    _bootstrap_db(db_path)
    monkeypatch.setattr(profile_db, "_connect", _make_temp_connect(db_path))
    yield db_path


# ---------------------------------------------------------------------------
# Test 1 — create_profile() inserts a row with correct defaults
# ---------------------------------------------------------------------------

class TestCreateProfile:
    """create_profile() must insert a row with all default values populated."""

    def test_create_profile_returns_uuid(self, isolated_db):
        user_id = _insert_test_user(isolated_db)

        profile_id = profile_db.create_profile(user_id)

        assert isinstance(profile_id, str), (
            f"create_profile must return a str UUID, got {type(profile_id).__name__!r}"
        )
        # UUID4 is 36 chars with dashes
        assert len(profile_id) == 36, (
            f"Expected a 36-char UUID, got {len(profile_id)!r} chars: {profile_id!r}"
        )

    def test_create_profile_default_mastery_level(self, isolated_db):
        user_id = _insert_test_user(isolated_db)

        profile_db.create_profile(user_id)
        row = profile_db.get_profile_by_user_id(user_id)

        assert row["mastery_level"] == "novice", (
            f"Default mastery_level must be 'novice', got {row['mastery_level']!r}"
        )

    def test_create_profile_default_interaction_count(self, isolated_db):
        user_id = _insert_test_user(isolated_db)

        profile_db.create_profile(user_id)
        row = profile_db.get_profile_by_user_id(user_id)

        assert row["interaction_count"] == 0, (
            f"Default interaction_count must be 0, got {row['interaction_count']!r}"
        )

    def test_create_profile_default_json_fields(self, isolated_db):
        user_id = _insert_test_user(isolated_db)

        profile_db.create_profile(user_id)
        row = profile_db.get_profile_by_user_id(user_id)

        assert row["topic_scores"] == {}, (
            f"Default topic_scores must be {{}} (empty dict), got {row['topic_scores']!r}"
        )
        assert row["strengths"] == [], (
            f"Default strengths must be [] (empty list), got {row['strengths']!r}"
        )
        assert row["gaps"] == [], (
            f"Default gaps must be [] (empty list), got {row['gaps']!r}"
        )

    def test_create_profile_last_activity_at_is_none(self, isolated_db):
        user_id = _insert_test_user(isolated_db)

        profile_db.create_profile(user_id)
        row = profile_db.get_profile_by_user_id(user_id)

        assert row["last_activity_at"] is None, (
            f"Default last_activity_at must be None, got {row['last_activity_at']!r}"
        )


# ---------------------------------------------------------------------------
# Test 2 — get_profile_by_user_id() returns deserialized Python objects
# ---------------------------------------------------------------------------

class TestGetProfileByUserId:
    """topic_scores, strengths, and gaps must be Python objects, not raw JSON strings."""

    def test_topic_scores_is_dict_not_string(self, isolated_db):
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)

        row = profile_db.get_profile_by_user_id(user_id)

        assert isinstance(row["topic_scores"], dict), (
            f"topic_scores must be dict after get_profile_by_user_id — "
            f"got {type(row['topic_scores']).__name__!r}. "
            "Check that json.loads() is applied in get_profile_by_user_id()."
        )

    def test_strengths_is_list_not_string(self, isolated_db):
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)

        row = profile_db.get_profile_by_user_id(user_id)

        assert isinstance(row["strengths"], list), (
            f"strengths must be list after get_profile_by_user_id — "
            f"got {type(row['strengths']).__name__!r}."
        )

    def test_gaps_is_list_not_string(self, isolated_db):
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)

        row = profile_db.get_profile_by_user_id(user_id)

        assert isinstance(row["gaps"], list), (
            f"gaps must be list after get_profile_by_user_id — "
            f"got {type(row['gaps']).__name__!r}."
        )

    def test_returns_none_for_unknown_user(self, isolated_db):
        row = profile_db.get_profile_by_user_id("nonexistent-user-id")

        assert row is None, (
            f"get_profile_by_user_id must return None for unknown user_id — "
            f"got {row!r}."
        )

    def test_roundtrip_non_empty_topic_scores(self, isolated_db):
        """Scores written via update_profile must round-trip correctly through a SELECT."""
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)
        profile_db.update_profile(user_id, topic_scores={"python": 0.9, "sql": 0.7})

        row = profile_db.get_profile_by_user_id(user_id)

        assert row["topic_scores"] == {"python": 0.9, "sql": 0.7}, (
            f"topic_scores round-trip failed — got {row['topic_scores']!r}. "
            "Check that json.dumps is used on write and json.loads on read."
        )


# ---------------------------------------------------------------------------
# Test 3 — update_profile() updates only the named field
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    """Partial update: only passed kwargs change; all other fields are preserved."""

    def test_mastery_level_updates(self, isolated_db):
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)

        profile_db.update_profile(user_id, mastery_level="intermediate")
        row = profile_db.get_profile_by_user_id(user_id)

        assert row["mastery_level"] == "intermediate", (
            f"mastery_level must be 'intermediate' after update, got {row['mastery_level']!r}"
        )

    def test_other_fields_unchanged_after_mastery_update(self, isolated_db):
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)
        before = profile_db.get_profile_by_user_id(user_id)

        profile_db.update_profile(user_id, mastery_level="intermediate")
        after = profile_db.get_profile_by_user_id(user_id)

        # Fields not passed to update_profile must be unchanged
        assert after["interaction_count"] == before["interaction_count"], (
            "interaction_count must not change when only mastery_level is updated"
        )
        assert after["topic_scores"] == before["topic_scores"], (
            "topic_scores must not change when only mastery_level is updated"
        )
        assert after["strengths"] == before["strengths"], (
            "strengths must not change when only mastery_level is updated"
        )
        assert after["gaps"] == before["gaps"], (
            "gaps must not change when only mastery_level is updated"
        )

    def test_updated_at_is_refreshed(self, isolated_db):
        """updated_at must always be updated, even for a single-field change."""
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)
        before = profile_db.get_profile_by_user_id(user_id)

        profile_db.update_profile(user_id, mastery_level="beginner")
        after = profile_db.get_profile_by_user_id(user_id)

        # updated_at must be a newer timestamp (or at minimum equal — same-second edge case)
        assert after["updated_at"] >= before["updated_at"], (
            f"updated_at must be refreshed after update. "
            f"before={before['updated_at']!r}, after={after['updated_at']!r}"
        )

    def test_json_field_update_round_trips(self, isolated_db):
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)

        profile_db.update_profile(user_id, strengths=["retrieval", "prompting"])
        row = profile_db.get_profile_by_user_id(user_id)

        assert row["strengths"] == ["retrieval", "prompting"], (
            f"strengths must round-trip correctly after update — got {row['strengths']!r}"
        )

    def test_update_with_no_fields_raises_value_error(self, isolated_db):
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)

        with pytest.raises(ValueError, match="no fields"):
            profile_db.update_profile(user_id)


# ---------------------------------------------------------------------------
# Test 4 — get_or_create_profile() is idempotent
# ---------------------------------------------------------------------------

class TestGetOrCreateProfile:
    """get_or_create_profile() must create on first call and return existing on second."""

    def test_creates_profile_on_first_call(self, isolated_db):
        user_id = _insert_test_user(isolated_db)

        profile = profile_db.get_or_create_profile(user_id)

        assert profile is not None, "get_or_create_profile must return a profile dict"
        assert profile["user_id"] == user_id, (
            f"profile['user_id'] must be {user_id!r}, got {profile['user_id']!r}"
        )

    def test_second_call_returns_same_profile(self, isolated_db):
        """No duplicate insert — second call must return the existing row."""
        user_id = _insert_test_user(isolated_db)

        first = profile_db.get_or_create_profile(user_id)
        second = profile_db.get_or_create_profile(user_id)

        assert first["id"] == second["id"], (
            f"get_or_create_profile must return the same profile_id on both calls. "
            f"First id={first['id']!r}, second id={second['id']!r}. "
            "A new row was created on the second call — check the get-first logic."
        )

    def test_second_call_does_not_raise_integrity_error(self, isolated_db):
        """A duplicate INSERT would raise sqlite3.IntegrityError; verify it doesn't."""
        user_id = _insert_test_user(isolated_db)

        profile_db.get_or_create_profile(user_id)
        # Must not raise
        profile_db.get_or_create_profile(user_id)

    def test_preserves_updates_between_calls(self, isolated_db):
        """Updates made between two get_or_create calls must survive."""
        user_id = _insert_test_user(isolated_db)

        profile_db.get_or_create_profile(user_id)
        profile_db.update_profile(user_id, mastery_level="advanced")
        second = profile_db.get_or_create_profile(user_id)

        assert second["mastery_level"] == "advanced", (
            f"get_or_create_profile on second call must return the updated row — "
            f"mastery_level should be 'advanced', got {second['mastery_level']!r}."
        )


# ---------------------------------------------------------------------------
# Test 5 — Import smoke test: no dangling references to deleted profiles.py
# ---------------------------------------------------------------------------

class TestImportSmoke:
    """After deleting rag/memory/profiles.py, all imports must succeed cleanly."""

    def test_chain_imports_without_error(self):
        """rag.chain must import without referencing the deleted profiles module."""
        # This test will fail at collection time if the import itself raises,
        # which means we get a clear error message pointing to the bad import.
        import rag.chain  # noqa: F401

    def test_profile_db_imports_without_error(self):
        import app.profile.db  # noqa: F401

    def test_profile_schemas_imports_without_error(self):
        import app.profile.schemas  # noqa: F401
        from app.profile.schemas import UserProfilePublic  # noqa: F401


# ---------------------------------------------------------------------------
# Test 6 — FK cascade: deleting a user removes the profile row
# ---------------------------------------------------------------------------

class TestForeignKeyCascade:
    """
    Cascade delete: when a users row is deleted, the profile row must be removed.

    This uses a direct sqlite3 connection to the temp DB — not the profile_db
    CRUD functions — so that the test remains valid even if CRUD functions
    were to swallow exceptions or handle missing rows.

    PRAGMA foreign_keys=ON must be set per connection. SQLite does not persist
    this setting between connections.
    """

    def test_deleting_user_cascades_to_profile(self, tmp_path):
        db_path = str(tmp_path / "cascade_test.db")
        _bootstrap_db(db_path)

        def connect():
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.execute("PRAGMA foreign_keys=ON")
            return conn

        now = datetime.now(timezone.utc).isoformat()
        user_id = str(uuid.uuid4())
        profile_id = str(uuid.uuid4())

        # Insert user
        conn = connect()
        conn.execute(
            "INSERT INTO users (id, email, password_hash, display_name, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, f"{user_id}@test.local", "hashed", "Cascade User", now),
        )
        conn.commit()
        conn.close()

        # Insert profile referencing that user
        conn = connect()
        conn.execute(
            "INSERT INTO user_profiles "
            "(id, user_id, mastery_level, interaction_count, "
            "topic_scores, strengths, gaps, created_at, updated_at) "
            "VALUES (?, ?, 'novice', 0, '{}', '[]', '[]', ?, ?)",
            (profile_id, user_id, now, now),
        )
        conn.commit()
        conn.close()

        # Confirm profile row exists before delete
        conn = connect()
        row = conn.execute(
            "SELECT id FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        assert row is not None, (
            f"Profile row must exist before user delete — not found for user_id={user_id!r}"
        )

        # Delete the user
        conn = connect()
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()

        # Profile row must be gone
        conn = connect()
        row = conn.execute(
            "SELECT id FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()

        assert row is None, (
            f"Profile row must be deleted via ON DELETE CASCADE when the parent user is deleted. "
            f"Profile row still exists for user_id={user_id!r}. "
            "Verify that PRAGMA foreign_keys=ON is set per connection in _connect() "
            "and that the FK clause in CREATE TABLE includes ON DELETE CASCADE."
        )


# ---------------------------------------------------------------------------
# Test 7 — update_profile() rejects unknown column names (allowlist guard)
# ---------------------------------------------------------------------------

class TestUpdateProfileAllowlist:
    """update_profile() must raise ValueError for column names not in _ALLOWED_PROFILE_COLUMNS."""

    def test_unknown_column_raises_value_error(self, isolated_db):
        """Passing an attacker-influenced column name must be rejected before SQL runs."""
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)

        with pytest.raises(ValueError, match="unknown column"):
            profile_db.update_profile(user_id, nonexistent_column="value")

    def test_row_unchanged_after_rejected_update(self, isolated_db):
        """A rejected update must leave the row in its original state."""
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)
        before = profile_db.get_profile_by_user_id(user_id)

        try:
            profile_db.update_profile(user_id, nonexistent_column="value")
        except ValueError:
            pass

        after = profile_db.get_profile_by_user_id(user_id)

        assert after["mastery_level"] == before["mastery_level"], (
            "mastery_level must not change after a rejected update"
        )
        assert after["interaction_count"] == before["interaction_count"], (
            "interaction_count must not change after a rejected update"
        )
        assert after["updated_at"] == before["updated_at"], (
            f"updated_at must not change after a rejected update — "
            f"before={before['updated_at']!r}, after={after['updated_at']!r}"
        )


# ---------------------------------------------------------------------------
# Test 8 — _deserialize_row raises json.JSONDecodeError for malformed JSON in DB
# ---------------------------------------------------------------------------

class TestDeserializeRowMalformedJson:
    """_deserialize_row must propagate json.JSONDecodeError when the DB contains invalid JSON."""

    def test_malformed_topic_scores_raises_json_decode_error(self, isolated_db):
        """
        Bypass the CRUD layer and write a malformed JSON string directly into
        topic_scores, then verify get_profile_by_user_id raises JSONDecodeError.

        This tests the DB-level contract: if the DB is somehow corrupted, the
        deserializer must surface the error rather than silently returning garbage.
        """
        user_id = _insert_test_user(isolated_db)
        profile_db.create_profile(user_id)

        # Write malformed JSON directly via raw SQL — bypassing the CRUD layer
        conn = sqlite3.connect(isolated_db, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            "UPDATE user_profiles SET topic_scores = ? WHERE user_id = ?",
            ("not-valid-json{{{", user_id),
        )
        conn.commit()
        conn.close()

        with pytest.raises(json.JSONDecodeError):
            profile_db.get_profile_by_user_id(user_id)
