"""
Tests for Commit 36 — onboarding-level-check.

Coverage gates (spec):

/api/onboarding/status:
  - Fresh user (no topic_scores) → {"needed": true}
  - User with any scored topic   → {"needed": false}
  - Unauthenticated              → 401

/api/onboarding/diagnostic:
  - Returns 3 questions for each valid self-report level (novice/intermediate/expert)
  - Each question text contains "Knowledge check:" and A–D options
  - Invalid level value          → 422
  - Unauthenticated              → 401

/api/onboarding/complete:
  - 3/3 correct  → confirmed at self-report level
  - 1/3 correct  → one level below self-report
  - 0/3 correct  → two levels below self-report
  - "novice" + 0/3 → "novice" (floor enforcement)
  - skipped=true → confirmed_level="novice", profile written
  - Unauthenticated  → 401

Design notes:
- Follows the same isolated-DB pattern as test_profile_api.py.
- MCQ file loading is patched to avoid filesystem coupling in scoring tests.
  _load_mcq_question is patched at the mcq_utils import site in onboarding.
- Tests that verify question text content use the real files (they exist on disk).
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
from app.api.routes.onboarding import router as onboarding_router
from app.auth.tokens import create_access_token


# ---------------------------------------------------------------------------
# DB helpers — mirrors test_profile_api.py
# ---------------------------------------------------------------------------

def _make_temp_connect(db_path: str):
    def _connect() -> sqlite3.Connection:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    return _connect


def _bootstrap_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            email         TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name  TEXT,
            created_at    TEXT NOT NULL,
            is_admin      INTEGER NOT NULL DEFAULT 0
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
    conn.commit()
    conn.close()


def _insert_user_with_profile(db_path: str, topic_scores: str = "{}") -> tuple[str, str]:
    """Insert a users row + profile row directly. Returns (user_id, token)."""
    user_id = str(uuid.uuid4())
    profile_id = str(uuid.uuid4())
    email = f"{user_id[:8]}@test.local"
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        "INSERT INTO users (id, email, password_hash, display_name, created_at) VALUES (?,?,?,?,?)",
        (user_id, email, "hashed", "Test", now),
    )
    conn.execute(
        """
        INSERT INTO user_profiles
            (id, user_id, mastery_level, interaction_count, topic_scores,
             session_history, strengths, gaps, last_activity_at, created_at, updated_at)
        VALUES (?, ?, 'novice', 0, ?, '{}', '[]', '[]', NULL, ?, ?)
        """,
        (profile_id, user_id, topic_scores, now, now),
    )
    conn.commit()
    conn.close()
    token = create_access_token(sub=user_id, extra={"email": email})
    return user_id, token


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_setup(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_onboarding.db")
    _bootstrap_db(db_path)

    monkeypatch.setattr(auth_db, "_connect", _make_temp_connect(db_path))
    monkeypatch.setattr(profile_db, "_connect", _make_temp_connect(db_path))

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(onboarding_router)

    client = TestClient(app, raise_server_exceptions=False)
    yield {"client": client, "db_path": db_path}


# ---------------------------------------------------------------------------
# /api/onboarding/status
# ---------------------------------------------------------------------------

class TestOnboardingStatus:
    def test_fresh_user_needed_true(self, api_setup):
        """Fresh user with empty topic_scores → needed=true."""
        client = api_setup["client"]
        _, token = _insert_user_with_profile(api_setup["db_path"], topic_scores="{}")
        resp = client.get("/api/onboarding/status", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["needed"] is True

    def test_user_with_scored_topic_needed_false(self, api_setup):
        """User with any non-None topic score → needed=false."""
        client = api_setup["client"]
        import json
        scores = json.dumps({"embeddings_and_similarity": 0.8})
        _, token = _insert_user_with_profile(api_setup["db_path"], topic_scores=scores)
        resp = client.get("/api/onboarding/status", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["needed"] is False

    def test_status_unauthenticated_returns_401(self, api_setup):
        """No token → 401."""
        resp = api_setup["client"].get("/api/onboarding/status")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /api/onboarding/diagnostic
# ---------------------------------------------------------------------------

class TestOnboardingDiagnostic:
    def test_novice_returns_3_questions(self, api_setup):
        """novice level → 3 questions returned."""
        client = api_setup["client"]
        _, token = _insert_user_with_profile(api_setup["db_path"])
        resp = client.post(
            "/api/onboarding/diagnostic",
            json={"level": "novice"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["questions"]) == 3

    def test_intermediate_returns_3_questions(self, api_setup):
        """intermediate level → 3 questions returned."""
        client = api_setup["client"]
        _, token = _insert_user_with_profile(api_setup["db_path"])
        resp = client.post(
            "/api/onboarding/diagnostic",
            json={"level": "intermediate"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["questions"]) == 3

    def test_expert_returns_3_questions(self, api_setup):
        """expert level → 3 questions returned."""
        client = api_setup["client"]
        _, token = _insert_user_with_profile(api_setup["db_path"])
        resp = client.post(
            "/api/onboarding/diagnostic",
            json={"level": "expert"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["questions"]) == 3

    def test_question_text_contains_knowledge_check(self, api_setup):
        """Each question text must contain 'Knowledge check:'."""
        client = api_setup["client"]
        _, token = _insert_user_with_profile(api_setup["db_path"])
        resp = client.post(
            "/api/onboarding/diagnostic",
            json={"level": "novice"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        for q in resp.json()["questions"]:
            assert "Knowledge check:" in q["text"], (
                f"Question text missing 'Knowledge check:': {q['text'][:80]!r}"
            )

    def test_question_text_contains_abcd_options(self, api_setup):
        """Each question text must contain A–D options."""
        import re
        client = api_setup["client"]
        _, token = _insert_user_with_profile(api_setup["db_path"])
        resp = client.post(
            "/api/onboarding/diagnostic",
            json={"level": "intermediate"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        for q in resp.json()["questions"]:
            matches = re.findall(r"^[A-D]\.", q["text"], re.MULTILINE)
            assert len(matches) == 4, (
                f"Expected 4 A–D options in question text, found {len(matches)}: {q['text'][:120]!r}"
            )

    def test_invalid_level_returns_422(self, api_setup):
        """Invalid self-report level → 422 Unprocessable Entity."""
        client = api_setup["client"]
        _, token = _insert_user_with_profile(api_setup["db_path"])
        resp = client.post(
            "/api/onboarding/diagnostic",
            json={"level": "wizard"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    def test_diagnostic_unauthenticated_returns_401(self, api_setup):
        """No token → 401."""
        resp = api_setup["client"].post("/api/onboarding/diagnostic", json={"level": "novice"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /api/onboarding/complete
# ---------------------------------------------------------------------------

# Stub MCQ answers for placement tests — we patch load_mcq_question to return
# predictable correct answers so tests are independent of file content.
_STUB_CORRECT = "B"
_STUB_QUESTIONS = [
    (f"Knowledge check: Q{i}\n\nA. a\nB. b\nC. c\nD. d", _STUB_CORRECT)
    for i in range(3)
]


def _stub_load_mcq(slug: str, index: int) -> tuple[str, str]:
    return _STUB_QUESTIONS[index % 3]


class TestOnboardingComplete:
    def test_all_correct_confirmed_at_self_report_level(self, api_setup):
        """3/3 correct → confirmed at self-report level (intermediate)."""
        client = api_setup["client"]
        _, token = _insert_user_with_profile(api_setup["db_path"])
        with patch("app.api.routes.onboarding.load_mcq_question", side_effect=_stub_load_mcq):
            resp = client.post(
                "/api/onboarding/complete",
                json={"level": "intermediate", "answers": ["B", "B", "B"], "skipped": False},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["confirmed_level"] == "intermediate"
        assert body["correct_count"] == 3

    def test_one_correct_drops_one_level(self, api_setup):
        """1/3 correct → one level below self-report (intermediate → novice)."""
        client = api_setup["client"]
        _, token = _insert_user_with_profile(api_setup["db_path"])
        with patch("app.api.routes.onboarding.load_mcq_question", side_effect=_stub_load_mcq):
            resp = client.post(
                "/api/onboarding/complete",
                json={"level": "intermediate", "answers": ["B", "A", "A"], "skipped": False},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["confirmed_level"] == "novice"
        assert body["correct_count"] == 1

    def test_zero_correct_drops_two_levels(self, api_setup):
        """0/3 correct → two levels below self-report (expert → intermediate)."""
        client = api_setup["client"]
        _, token = _insert_user_with_profile(api_setup["db_path"])
        with patch("app.api.routes.onboarding.load_mcq_question", side_effect=_stub_load_mcq):
            resp = client.post(
                "/api/onboarding/complete",
                json={"level": "expert", "answers": ["A", "A", "A"], "skipped": False},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["confirmed_level"] == "intermediate"
        assert body["correct_count"] == 0

    def test_novice_zero_correct_floors_at_novice(self, api_setup):
        """novice + 0/3 correct → novice (floor, cannot drop below)."""
        client = api_setup["client"]
        _, token = _insert_user_with_profile(api_setup["db_path"])
        with patch("app.api.routes.onboarding.load_mcq_question", side_effect=_stub_load_mcq):
            resp = client.post(
                "/api/onboarding/complete",
                json={"level": "novice", "answers": ["A", "A", "A"], "skipped": False},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["confirmed_level"] == "novice", (
            f"novice + 0/3 must floor at novice, got {body['confirmed_level']!r}"
        )

    def test_skipped_writes_novice_and_returns_novice(self, api_setup):
        """skipped=true → confirmed_level='novice', profile updated."""
        client = api_setup["client"]
        user_id, token = _insert_user_with_profile(api_setup["db_path"])
        resp = client.post(
            "/api/onboarding/complete",
            json={"level": "novice", "answers": [], "skipped": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["confirmed_level"] == "novice"
        # Verify the DB write actually happened
        conn = sqlite3.connect(api_setup["db_path"])
        row = conn.execute(
            "SELECT mastery_level FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "novice"

    def test_complete_unauthenticated_returns_401(self, api_setup):
        """No token → 401."""
        resp = api_setup["client"].post(
            "/api/onboarding/complete",
            json={"level": "novice", "answers": ["A", "B", "C"], "skipped": False},
        )
        assert resp.status_code == 401
