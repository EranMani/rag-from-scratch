"""
Tests for Commit 06 — profile-api-route.

Coverage targets:
1. GET /api/profile/me with valid token → 200, response shape matches UserProfilePublic fields
2. GET /api/profile/me without token → 401
3. GET /api/profile/me with invalid/malformed token → 401
4. Register a user then immediately GET /api/profile/me → 200, mastery_level == "novice",
   topic_scores == {}
5. GET /api/profile/me when profile is missing for a valid user → 404
6. Register with duplicate email → 409, create_profile is never called

Design notes:
- A lightweight test app mounts only the auth and profile routers. The lifespan
  that would start ChromaDB/BM25/Redis is bypassed entirely.
- Both app.auth.db._connect and app.profile.db._connect are patched to a factory
  targeting a shared temp-file DB. SQLite :memory: cannot be used here because
  each _connect() call would open an independent, empty database — all state would
  be invisible across calls.
- The temp DB is bootstrapped with both tables (users first, then user_profiles with
  the FK referencing users.id ON DELETE CASCADE) before any test runs.
- Tokens are produced by create_access_token — the same function the production route
  uses — so they are structurally valid. For the invalid-token tests we pass a raw
  string that is not a signed JWT.
- Test 5 (missing profile) injects a user directly into the DB then creates a token
  for that user_id without ever calling create_profile, ensuring no profile row exists
  while a valid users row does.
- Test 6 (duplicate email) registers once, then registers again with the same email and
  verifies the 409. The call count on create_profile is checked via patch to confirm
  it is never invoked for the second (rejected) request.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.auth.db as auth_db
import app.profile.db as profile_db
from app.api.routes.auth import router as auth_router
from app.api.routes.profile import router as profile_router
from app.auth.tokens import create_access_token


# ---------------------------------------------------------------------------
# DB bootstrap helpers — mirrors the pattern in test_profile_service.py
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

    users must be created before user_profiles because user_profiles has a
    FK referencing users(id) ON DELETE CASCADE.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name  TEXT,
            created_at    TEXT NOT NULL
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


def _insert_user_directly(db_path: str, email: str | None = None) -> tuple[str, str]:
    """Insert a users row directly and return (user_id, email).

    Used for test 5 where we need a valid user with NO corresponding profile row.
    """
    user_id = str(uuid.uuid4())
    email = email or f"{user_id}@test.local"
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "INSERT INTO users (id, email, password_hash, display_name, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, email, "hashed", "Test User", now),
    )
    conn.commit()
    conn.close()
    return user_id, email


# ---------------------------------------------------------------------------
# Fixture: isolated test app + DB
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_setup(tmp_path, monkeypatch):
    """Provide an isolated FastAPI test client with both auth and profile routers.

    - Creates a temp DB file with both tables.
    - Patches app.auth.db._connect and app.profile.db._connect to the temp DB.
    - Yields a dict: {"client": TestClient, "db_path": str}
    """
    db_path = str(tmp_path / "test_profile_api.db")
    _bootstrap_db(db_path)

    monkeypatch.setattr(auth_db, "_connect", _make_temp_connect(db_path))
    monkeypatch.setattr(profile_db, "_connect", _make_temp_connect(db_path))

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(profile_router)

    client = TestClient(app, raise_server_exceptions=False)
    yield {"client": client, "db_path": db_path}


# ---------------------------------------------------------------------------
# Test 1 — Valid token → 200, shape matches UserProfilePublic
# ---------------------------------------------------------------------------

class TestGetProfileAuthenticated:
    """GET /api/profile/me with a valid token must return 200 with the correct shape."""

    def test_valid_token_returns_200(self, api_setup):
        client = api_setup["client"]

        reg = client.post(
            "/api/auth/register",
            json={"email": "alice@example.com", "password": "password123", "display_name": "Alice"},
        )
        assert reg.status_code == 200, f"Register failed: {reg.text}"

        token = reg.json()["access_token"]
        resp = client.get("/api/profile/me", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 200, (
            f"Expected 200 for authenticated profile request, got {resp.status_code}: {resp.text}"
        )

    def test_response_shape_matches_user_profile_public(self, api_setup):
        """All fields declared on UserProfilePublic must be present in the response."""
        client = api_setup["client"]

        reg = client.post(
            "/api/auth/register",
            json={"email": "bob@example.com", "password": "password123", "display_name": "Bob"},
        )
        assert reg.status_code == 200, f"Register failed: {reg.text}"

        token = reg.json()["access_token"]
        resp = client.get("/api/profile/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

        body = resp.json()
        expected_fields = {
            "user_id",
            "mastery_level",
            "interaction_count",
            "topic_scores",
            "strengths",
            "gaps",
            "last_activity_at",
            "created_at",
            "updated_at",
        }
        missing = expected_fields - set(body.keys())
        assert not missing, (
            f"Response is missing fields required by UserProfilePublic: {missing!r}. "
            f"Got keys: {set(body.keys())!r}"
        )


# ---------------------------------------------------------------------------
# Test 2 — No token → 401
# ---------------------------------------------------------------------------

class TestGetProfileNoToken:
    """GET /api/profile/me without an Authorization header must return 401."""

    def test_no_token_returns_401(self, api_setup):
        client = api_setup["client"]

        resp = client.get("/api/profile/me")

        assert resp.status_code == 401, (
            f"Expected 401 Unauthorized without a token, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Test 3 — Invalid/malformed token → 401
# ---------------------------------------------------------------------------

class TestGetProfileInvalidToken:
    """GET /api/profile/me with a structurally invalid token must return 401."""

    def test_malformed_token_returns_401(self, api_setup):
        client = api_setup["client"]

        resp = client.get(
            "/api/profile/me",
            headers={"Authorization": "Bearer not.a.real.token"},
        )

        assert resp.status_code == 401, (
            f"Expected 401 for malformed token, got {resp.status_code}: {resp.text}"
        )

    def test_garbage_token_returns_401(self, api_setup):
        """A completely random string in the Bearer slot must be rejected."""
        client = api_setup["client"]

        resp = client.get(
            "/api/profile/me",
            headers={"Authorization": "Bearer aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
        )

        assert resp.status_code == 401, (
            f"Expected 401 for garbage token, got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Test 4 — Register then GET /api/profile/me → 200, default values
# ---------------------------------------------------------------------------

class TestProfileDefaultsAfterRegistration:
    """A profile created at registration must have mastery_level='novice' and topic_scores={}."""

    def test_mastery_level_is_novice(self, api_setup):
        client = api_setup["client"]

        reg = client.post(
            "/api/auth/register",
            json={"email": "charlie@example.com", "password": "password123", "display_name": "Charlie"},
        )
        assert reg.status_code == 200, f"Register failed: {reg.text}"

        token = reg.json()["access_token"]
        resp = client.get("/api/profile/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"Profile fetch failed: {resp.text}"

        body = resp.json()
        assert body["mastery_level"] == "novice", (
            f"mastery_level must be 'novice' immediately after registration, "
            f"got {body['mastery_level']!r}"
        )

    def test_topic_scores_is_empty_dict(self, api_setup):
        client = api_setup["client"]

        reg = client.post(
            "/api/auth/register",
            json={"email": "diana@example.com", "password": "password123", "display_name": "Diana"},
        )
        assert reg.status_code == 200, f"Register failed: {reg.text}"

        token = reg.json()["access_token"]
        resp = client.get("/api/profile/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"Profile fetch failed: {resp.text}"

        body = resp.json()
        assert body["topic_scores"] == {}, (
            f"topic_scores must be {{}} immediately after registration, "
            f"got {body['topic_scores']!r}"
        )


# ---------------------------------------------------------------------------
# Test 5 — Valid user, no profile row → 404
# ---------------------------------------------------------------------------

class TestGetProfileMissingProfile:
    """When a valid user exists but no profile row exists, the route must return 404."""

    def test_missing_profile_returns_404(self, api_setup):
        """Inject a user row directly without creating a profile, then fetch /me."""
        client = api_setup["client"]
        db_path = api_setup["db_path"]

        # Insert a user directly — no create_profile called, so no profile row exists.
        user_id, email = _insert_user_directly(db_path)

        # Build a valid token for this user_id using the production token factory.
        token = create_access_token(sub=user_id, extra={"email": email})

        resp = client.get("/api/profile/me", headers={"Authorization": f"Bearer {token}"})

        assert resp.status_code == 404, (
            f"Expected 404 when profile row is absent for a valid user, "
            f"got {resp.status_code}: {resp.text}"
        )

    def test_missing_profile_detail_does_not_expose_user_id(self, api_setup):
        """The 404 detail must not contain the user_id (Sage MEDIUM: avoid leaking internal IDs)."""
        client = api_setup["client"]
        db_path = api_setup["db_path"]

        user_id, email = _insert_user_directly(db_path, email="sage-check@example.com")
        token = create_access_token(sub=user_id, extra={"email": email})

        resp = client.get("/api/profile/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

        detail = resp.json().get("detail", "")
        assert user_id not in detail, (
            f"404 detail must not expose user_id. "
            f"user_id={user_id!r} found in detail={detail!r}. "
            "Remove any f-string interpolation of user_id from the HTTPException detail."
        )
        assert "Re-register" not in detail, (
            "404 detail must not suggest 'Re-register' — that endpoint would return 409. "
            f"Got detail={detail!r}"
        )


# ---------------------------------------------------------------------------
# Test 6 — Duplicate email → 409, create_profile never called
# ---------------------------------------------------------------------------

class TestDuplicateEmailRegistration:
    """Registering with a duplicate email must return 409 and never call create_profile."""

    def test_duplicate_email_returns_409(self, api_setup):
        client = api_setup["client"]

        # First registration — must succeed.
        first = client.post(
            "/api/auth/register",
            json={"email": "duplicate@example.com", "password": "password123", "display_name": "First"},
        )
        assert first.status_code == 200, f"First register failed unexpectedly: {first.text}"

        # Second registration with the same email — must return 409.
        second = client.post(
            "/api/auth/register",
            json={"email": "duplicate@example.com", "password": "different456", "display_name": "Second"},
        )
        assert second.status_code == 409, (
            f"Expected 409 Conflict for duplicate email, got {second.status_code}: {second.text}"
        )

    def test_duplicate_email_create_profile_not_called(self, api_setup):
        """create_profile must not be called when create_user is never reached (email check fires first)."""
        client = api_setup["client"]

        # First registration.
        first = client.post(
            "/api/auth/register",
            json={"email": "dup2@example.com", "password": "password123", "display_name": "Orig"},
        )
        assert first.status_code == 200, f"First register failed: {first.text}"

        # Patch create_profile in the route module's namespace to track calls.
        with patch("app.api.routes.auth.create_profile") as mock_create_profile:
            second = client.post(
                "/api/auth/register",
                json={"email": "dup2@example.com", "password": "other456", "display_name": "Dup"},
            )

        assert second.status_code == 409, (
            f"Expected 409 for duplicate email, got {second.status_code}: {second.text}"
        )
        assert mock_create_profile.call_count == 0, (
            "create_profile must never be called when registration is rejected due to duplicate email. "
            f"create_profile was called {mock_create_profile.call_count} time(s)."
        )
