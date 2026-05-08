"""
Tests for Commit 01 — auth-gate-on-ingest.

Coverage targets:
1. POST /api/ingest without a token → 401 Unauthorized
2. POST /api/ingest with a valid Bearer token → 200 {"status": "ok"}
3. The endpoint does not block other concurrent requests during ingestion
   (asyncio.to_thread ensures the event loop stays free while ingest runs)

Design notes:
- The FastAPI app imports NiceGUI and a lifespan that touches ChromaDB and
  BM25 at startup. Both would need Docker and data files. We bypass lifespan
  entirely by constructing a lightweight test app that only mounts the
  documents router.
- get_current_user is overridden via FastAPI's dependency_overrides so no
  real JWT or SQLite is required.
- ingest_documents is monkeypatched to a fast stub so ChromaDB is never hit.
- File I/O (write_bytes, TextLoader.load) is patched so no real filesystem
  writes or reads occur.
"""

import asyncio
import io
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.documents import router
from app.auth.deps import get_current_user

# ---------------------------------------------------------------------------
# Minimal test app — documents router only, no lifespan
# ---------------------------------------------------------------------------

_test_app = FastAPI()
_test_app.include_router(router)

_FAKE_USER = {
    "id": "test-user-id",
    "email": "rex@example.com",
    "display_name": "Rex",
    "password_hash": "hashed",
    "created_at": "2026-01-01T00:00:00+00:00",
}


async def _override_get_current_user():
    """Dependency override: always returns a fake authenticated user."""
    return _FAKE_USER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_upload_bytes(content: bytes = b"hello world") -> io.BytesIO:
    return io.BytesIO(content)


# ---------------------------------------------------------------------------
# Test 1 — No token → 401
# ---------------------------------------------------------------------------

class TestIngestUnauthenticated:
    """Without authentication, /api/ingest must refuse with 401."""

    def test_no_token_returns_401(self):
        # No dependency override — get_current_user runs for real and will
        # reject because there is no Authorization header.
        client = TestClient(_test_app, raise_server_exceptions=False)
        response = client.post(
            "/api/ingest",
            files={"file": ("note.txt", _make_upload_bytes(), "text/plain")},
        )
        assert response.status_code == 401, (
            f"Expected 401 Unauthorized, got {response.status_code}: {response.text}"
        )

    def test_invalid_token_returns_401(self):
        client = TestClient(_test_app, raise_server_exceptions=False)
        response = client.post(
            "/api/ingest",
            files={"file": ("note.txt", _make_upload_bytes(), "text/plain")},
            headers={"Authorization": "Bearer not.a.real.token"},
        )
        assert response.status_code == 401, (
            f"Expected 401 for invalid token, got {response.status_code}: {response.text}"
        )


# ---------------------------------------------------------------------------
# Test 2 — Valid token → 200 {"status": "ok"}
# ---------------------------------------------------------------------------

class TestIngestAuthenticated:
    """With a valid token, /api/ingest must accept the file and return ok."""

    def test_authenticated_upload_returns_ok(self, tmp_path, monkeypatch):
        # Override uploads dir so no 'data/uploads' folder is needed.
        monkeypatch.setattr(
            "app.api.routes.documents.UPLOAD_DIR",
            tmp_path,
        )

        fake_docs = [MagicMock()]

        with (
            patch("app.api.routes.documents.TextLoader") as mock_loader_cls,
            patch("app.api.routes.documents.ingest_documents", return_value=3) as mock_ingest,
        ):
            mock_loader_cls.return_value.load.return_value = fake_docs

            _test_app.dependency_overrides[get_current_user] = _override_get_current_user
            try:
                client = TestClient(_test_app)
                response = client.post(
                    "/api/ingest",
                    files={"file": ("doc.txt", _make_upload_bytes(b"content"), "text/plain")},
                    headers={"Authorization": "Bearer fake-but-overridden"},
                )
            finally:
                _test_app.dependency_overrides.clear()

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        body = response.json()
        assert body["status"] == "ok"
        assert body["chunks_ingested"] == 3
        assert body["filename"] == "doc.txt"
        mock_ingest.assert_called_once_with(fake_docs)

    def test_authenticated_upload_writes_file(self, tmp_path, monkeypatch):
        """The uploaded bytes must be persisted before ingestion."""
        monkeypatch.setattr(
            "app.api.routes.documents.UPLOAD_DIR",
            tmp_path,
        )
        file_content = b"important document bytes"

        with (
            patch("app.api.routes.documents.TextLoader") as mock_loader_cls,
            patch("app.api.routes.documents.ingest_documents", return_value=1),
        ):
            mock_loader_cls.return_value.load.return_value = [MagicMock()]

            _test_app.dependency_overrides[get_current_user] = _override_get_current_user
            try:
                client = TestClient(_test_app)
                client.post(
                    "/api/ingest",
                    files={"file": ("saved.txt", io.BytesIO(file_content), "text/plain")},
                    headers={"Authorization": "Bearer fake-but-overridden"},
                )
            finally:
                _test_app.dependency_overrides.clear()

        written = (tmp_path / "saved.txt").read_bytes()
        assert written == file_content, "File bytes must be written before TextLoader is called"


# ---------------------------------------------------------------------------
# Test 3 — Security: path traversal and file type validation
# ---------------------------------------------------------------------------

class TestIngestSecurity:
    """Security-layer validation: path traversal and disallowed file types must be rejected."""

    def test_path_traversal_is_neutralized(self, tmp_path, monkeypatch):
        """
        A filename containing ../ must NOT escape the upload directory.

        Path(file.filename).name strips all directory components including ../,
        so '../../evil.txt' becomes 'evil.txt' and is written safely inside
        UPLOAD_DIR. The file must NOT appear outside the upload dir.
        """
        monkeypatch.setattr(
            "app.api.routes.documents.UPLOAD_DIR",
            tmp_path,
        )

        with (
            patch("app.api.routes.documents.TextLoader") as mock_loader_cls,
            patch("app.api.routes.documents.ingest_documents", return_value=1),
        ):
            mock_loader_cls.return_value.load.return_value = [MagicMock()]

            _test_app.dependency_overrides[get_current_user] = _override_get_current_user
            try:
                client = TestClient(_test_app, raise_server_exceptions=False)
                response = client.post(
                    "/api/ingest",
                    files={"file": ("../../evil.txt", _make_upload_bytes(b"pwned"), "text/plain")},
                    headers={"Authorization": "Bearer fake-but-overridden"},
                )
            finally:
                _test_app.dependency_overrides.clear()

        # The traversal is stripped; the file is written safely inside UPLOAD_DIR
        # as 'evil.txt' and the request succeeds.
        assert response.status_code == 200, (
            f"Expected 200 (traversal neutralized to safe name), got {response.status_code}: {response.text}"
        )
        # The file must exist inside tmp_path (not escaped to the parent).
        assert (tmp_path / "evil.txt").exists(), (
            "Sanitized file must be written inside UPLOAD_DIR"
        )
        # Crucially: nothing must have been written OUTSIDE tmp_path.
        assert not (tmp_path.parent / "evil.txt").exists(), (
            "Path traversal write must not escape UPLOAD_DIR"
        )

    def test_disallowed_extension_returns_400(self, tmp_path, monkeypatch):
        """A .py file must be rejected with 400 before any write or ingestion occurs."""
        monkeypatch.setattr(
            "app.api.routes.documents.UPLOAD_DIR",
            tmp_path,
        )

        _test_app.dependency_overrides[get_current_user] = _override_get_current_user
        try:
            client = TestClient(_test_app, raise_server_exceptions=False)
            response = client.post(
                "/api/ingest",
                files={"file": ("script.py", _make_upload_bytes(b"import os"), "text/plain")},
                headers={"Authorization": "Bearer fake-but-overridden"},
            )
        finally:
            _test_app.dependency_overrides.clear()

        assert response.status_code == 400, (
            f"Expected 400 for .py extension, got {response.status_code}: {response.text}"
        )
        assert not (tmp_path / "script.py").exists(), (
            "Disallowed-extension file must not be written to disk"
        )

    def test_empty_filename_returns_400(self, tmp_path, monkeypatch):
        """
        An empty filename must be rejected with 400 before any write occurs.

        The files= shorthand in TestClient drops the filename field entirely when
        given an empty string, causing FastAPI to return 422 before the route runs.
        We send a raw multipart body with filename="" in Content-Disposition so the
        request reaches the route and the guard at documents.py:23 can fire.
        """
        monkeypatch.setattr(
            "app.api.routes.documents.UPLOAD_DIR",
            tmp_path,
        )

        # Build a valid multipart body whose content-disposition carries filename=""
        raw_body = (
            b"--boundary123\r\n"
            b'Content-Disposition: form-data; name="file"; filename=""\r\n'
            b"Content-Type: text/plain\r\n"
            b"\r\n"
            b"some data\r\n"
            b"--boundary123--\r\n"
        )

        _test_app.dependency_overrides[get_current_user] = _override_get_current_user
        try:
            client = TestClient(_test_app, raise_server_exceptions=False)
            response = client.post(
                "/api/ingest",
                content=raw_body,
                headers={
                    "Content-Type": "multipart/form-data; boundary=boundary123",
                    "Authorization": "Bearer fake-but-overridden",
                },
            )
        finally:
            _test_app.dependency_overrides.clear()

        assert response.status_code == 400, (
            f"Expected 400 for empty filename, got {response.status_code}: {response.text}"
        )
        assert response.json()["detail"] == "Invalid filename"
        assert list(tmp_path.iterdir()) == [], (
            "No file must be written for an empty filename"
        )

    def test_allowed_md_extension_accepted(self, tmp_path, monkeypatch):
        """.md files must be accepted (regression guard after extension validation added)."""
        monkeypatch.setattr(
            "app.api.routes.documents.UPLOAD_DIR",
            tmp_path,
        )

        with (
            patch("app.api.routes.documents.TextLoader") as mock_loader_cls,
            patch("app.api.routes.documents.ingest_documents", return_value=2),
        ):
            mock_loader_cls.return_value.load.return_value = [MagicMock()]

            _test_app.dependency_overrides[get_current_user] = _override_get_current_user
            try:
                client = TestClient(_test_app)
                response = client.post(
                    "/api/ingest",
                    files={"file": ("readme.md", _make_upload_bytes(b"# Hello"), "text/plain")},
                    headers={"Authorization": "Bearer fake-but-overridden"},
                )
            finally:
                _test_app.dependency_overrides.clear()

        assert response.status_code == 200, (
            f"Expected 200 for .md file, got {response.status_code}: {response.text}"
        )


# ---------------------------------------------------------------------------
# Test 4 — asyncio.to_thread: event loop stays free during ingestion
# ---------------------------------------------------------------------------

class TestIngestNonBlocking:
    """
    Verify that ingest_documents runs in a thread, not blocking the event loop.

    Strategy: replace ingest_documents with a stub that sleeps for 0.1 s
    (simulating I/O). We fire two concurrent requests and check that the
    total elapsed time is < 1.5 * single-request time — i.e. they overlapped.
    A purely blocking implementation would take ≥ 2 * single-request time.

    This test uses asyncio directly and an async HTTPX client to fire both
    requests concurrently against the in-process ASGI app.
    """

    @pytest.mark.asyncio
    async def test_concurrent_requests_do_not_serialize(self, tmp_path, monkeypatch):
        import httpx

        monkeypatch.setattr(
            "app.api.routes.documents.UPLOAD_DIR",
            tmp_path,
        )

        SLEEP_SECONDS = 0.15  # simulated blocking I/O

        def _slow_ingest(docs):
            time.sleep(SLEEP_SECONDS)
            return 1

        with (
            patch("app.api.routes.documents.TextLoader") as mock_loader_cls,
            patch("app.api.routes.documents.ingest_documents", side_effect=_slow_ingest),
        ):
            mock_loader_cls.return_value.load.return_value = [MagicMock()]

            _test_app.dependency_overrides[get_current_user] = _override_get_current_user
            try:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=_test_app),
                    base_url="http://test",
                ) as client:
                    start = time.perf_counter()
                    r1, r2 = await asyncio.gather(
                        client.post(
                            "/api/ingest",
                            files={"file": ("a.txt", b"alpha", "text/plain")},
                            headers={"Authorization": "Bearer fake"},
                        ),
                        client.post(
                            "/api/ingest",
                            files={"file": ("b.txt", b"beta", "text/plain")},
                            headers={"Authorization": "Bearer fake"},
                        ),
                    )
                    elapsed = time.perf_counter() - start
            finally:
                _test_app.dependency_overrides.clear()

        assert r1.status_code == 200, f"Request 1 failed: {r1.text}"
        assert r2.status_code == 200, f"Request 2 failed: {r2.text}"

        # If ingest blocked the event loop, elapsed ≥ 2 * SLEEP_SECONDS.
        # With asyncio.to_thread both sleeps run in threads and overlap.
        max_serial_time = 2 * SLEEP_SECONDS
        assert elapsed < max_serial_time, (
            f"Requests appear to have run serially: elapsed={elapsed:.3f}s, "
            f"expected < {max_serial_time:.3f}s (2 × {SLEEP_SECONDS}s). "
            "Check that ingest_documents is wrapped in asyncio.to_thread."
        )
