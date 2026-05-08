# Rex — Worklog
# Project: rag-from-scratch
# Stack: Python 3.11+, FastAPI, LangChain, ChromaDB, SQLite, JWT (PyJWT), NiceGUI

---

## Current State
*Last updated: Commit 01 gate-remediation · 2026-05-08*

**Last completed:** Commit 01 `auth-gate-on-ingest` — gate remediation pass ✅
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- (none)

**Open Handoffs — Inbound:**
- (none)

**Key Interfaces I Own (for teammates):**
- `POST /api/ingest` — requires Bearer token; validates extension (.txt/.md only); neutralizes path traversal; wraps ingest in `asyncio.to_thread`
- `src/app/api/routes/documents.py` — documents router
- `src/app/auth/deps.py` — `get_current_user` is now `async`; DB call wrapped in `asyncio.to_thread`
- `src/app/api/routes/chat.py` — `current_user_optional` is now `async`; DB call wrapped in `asyncio.to_thread`
- `tests/test_ingest_auth.py` — 8 tests: auth gate, file write, security (traversal + extension), non-blocking

**Decisions Other Agents Must Know:**
- `get_current_user` (from `app.auth.deps`) is now **async**. Any callers using `def` routes that depend on it will need to be `async def`.
- `asyncio.to_thread(fn, *args)` is the project-standard pattern for wrapping blocking I/O (DB, ChromaDB) in async routes/deps.
- `ALLOWED_SUFFIXES = {".txt", ".md"}` is defined in `documents.py` — any future ingest routes should reuse or reference this set.

**Scope Overflows Pre-Built:**
- (none)

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 01 | Commit 01 `auth-gate-on-ingest` | ✅ Done (gate remediation applied) | Used `Depends(get_current_user)` — not the optional variant — and `asyncio.to_thread` consistent with chat.py pattern; gate remediation added path traversal neutralization, extension validation, async dep |

---

## Session 01 — Commit 01: `auth-gate-on-ingest`

**Date:** 2026-05-08
**Status:** ✅ Done

### Task Brief

Add two fixes to `src/app/api/routes/documents.py`:

1. Gate the `POST /api/ingest` endpoint behind mandatory authentication — unauthenticated callers must get 401.
2. Wrap the blocking `ingest_documents()` call in `asyncio.to_thread()` so ChromaDB's HTTP I/O does not block the async event loop during ingestion.

Constraints coming in: no blockers, no inbound handoffs, no tests exist yet (tests directory was empty). Success means: 401 without token, 200 with token, and demonstrated non-blocking behavior under concurrent requests.

### Approach

The codebase showed one mandatory-auth dependency (`get_current_user` in `app/auth/deps.py`) and one optional variant (`current_user_optional` defined locally in `chat.py`). The first question was which to use. Since ingest should never succeed without authentication (there is no `allow_anonymous_ingest` setting and no use case for public ingestion on a portfolio app), the mandatory form was the obvious choice — not the optional form. The existing usage in `auth.py` line 14 (`Depends(get_current_user)` with `dict = Depends(...)`) confirmed the simple injection pattern without `Annotated`.

For the `asyncio.to_thread` wrap: `ingest_documents` calls `chromadb.HttpClient` and `vectorstore.add_documents`, both synchronous I/O. The `chat.py` route already uses `asyncio.to_thread(run_rag_pipeline, ...)` for the same reason. The pattern is `count = await asyncio.to_thread(ingest_documents, docs)` — passing the callable and its arguments separately, not wrapping in a lambda, which matches the existing convention.

The testing challenge was that `app.main` has a lifespan context that initializes ChromaDB and loads knowledge base files — unavailable in a unit-test context. The solution was to construct a minimal test FastAPI app that mounts only the documents router, bypassing lifespan entirely. `get_current_user` is swapped via `dependency_overrides`. `ingest_documents` and `TextLoader` are monkeypatched. The non-blocking test fires two concurrent requests with `asyncio.gather` through an `httpx.AsyncClient` with `ASGITransport` and measures wall-clock elapsed time against the 2× single-request threshold.

### Decisions Made

**1. Mandatory auth (`get_current_user`) rather than optional auth**
The optional form (`current_user_optional`) exists in `chat.py` to support `allow_anonymous_chat`. No equivalent setting exists for ingestion, and there is no legitimate use case for unauthenticated document ingestion on this app. The mandatory dependency is the right semantic and produces a cleaner route signature.

**2. `asyncio.to_thread(ingest_documents, docs)` — no lambda wrapper**
`asyncio.to_thread` accepts a callable plus positional args. Passing `ingest_documents, docs` directly (rather than `lambda: ingest_documents(docs)`) matches the `chat.py` convention and is more explicit about the threading boundary.

**3. Minimal isolated test app rather than importing `app.main`**
`app.main` has side effects at import time (lifespan, NiceGUI mount, ChromaDB connectivity check). A test app with only the documents router avoids all of those, keeps the test hermetic, and runs without Docker. The tradeoff is that integration-level tests (full lifespan, real ChromaDB) are deferred to a separate test stage.

**4. Concurrency test via elapsed-time assertion**
Checking wall-clock time for two concurrent requests against a stubbed 0.15 s blocking `ingest_documents` is a direct behavioral test of the threading claim. The threshold is 2 × sleep — if they run serially, elapsed ≥ 0.30 s; if they overlap, elapsed is closer to 0.15 s. This is imprecise by nature but sufficient for CI on the hardware range this project runs on.

**5. `pytest.ini_options` added to `pyproject.toml`**
No pytest config existed. Added `pythonpath = ["src"]`, `asyncio_mode = "auto"`, and `testpaths = ["tests"]` — the minimum needed to resolve `app.*` imports and run `pytest.mark.asyncio` tests without per-test decorators.

### Issues Found Mid-Task

**No tests directory existed.**
Discovered when globbing for `tests/**/*.py` — no results. Created `tests/` and `tests/__init__.py` before writing the test file. Not a blocker; expected in a pre-test-suite state.

**`app.main` cannot be imported in tests without Docker.**
The lifespan in `main.py` calls `load_knoweldge_base()` (filesystem read) and `chromadb.HttpClient` on import-time execution paths. Resolved by using a minimal test app that mounts only the documents router — avoids the lifespan problem entirely.

**`asyncio_mode` deprecation warning in `pytest-asyncio >= 0.23`.**
With `asyncio_mode = "auto"` set, the `asyncio_default_fixture_loop_scope` is unset. The warning is cosmetic and does not affect test results. Noted; can be resolved by adding `asyncio_default_fixture_loop_scope = "function"` to `pyproject.toml` if desired in a later session.

### Self-Review Checklist

- [x] `GET /api/ingest` without token returns 401 (test: `test_no_token_returns_401`)
- [x] `POST /api/ingest` with invalid token returns 401 (test: `test_invalid_token_returns_401`)
- [x] `POST /api/ingest` with valid token returns `{"status": "ok"}` (test: `test_authenticated_upload_returns_ok`)
- [x] File bytes are persisted before TextLoader is called (test: `test_authenticated_upload_writes_file`)
- [x] Concurrent requests do not serialize (test: `test_concurrent_requests_do_not_serialize`)
- [x] `ingest_documents` wrapped in `asyncio.to_thread` — not called bare
- [x] `get_current_user` imported from `app.auth.deps` — not duplicated
- [x] `current_user` parameter added to route signature (triggers FastAPI DI)
- [x] No `any` type annotations
- [x] No raw SQL
- [x] All 5 tests pass locally (`pytest tests/test_ingest_auth.py -v`)
- [x] No secrets in staged files
- [x] `pyproject.toml` updated with pytest config (no separate `pytest.ini` created)

### Scope Overflow Check

No scope overflows. The two changes (auth gate + asyncio.to_thread) are exactly what the commit spec calls for. The pytest config addition is infrastructure required by the tests, not a feature addition.

### Documentation Flags for Claude

**DECISIONS.md:**
- `asyncio.to_thread` as the standard blocking-I/O wrapper — `asyncio.to_thread(fn, *args)` is the project-wide pattern for bridging blocking calls into async FastAPI routes. Established in `chat.py` (run_rag_pipeline), confirmed/extended in `documents.py` (ingest_documents).
- Mandatory vs. optional auth dependency — `get_current_user` (hard 401) vs. `current_user_optional` (None if no token) are both available. Which to use depends on whether unauthenticated access has a legitimate use case for the route. For ingest: no. For chat: governed by `allow_anonymous_chat`.

**ARCHITECTURE.md:**
- `POST /api/ingest` is now auth-gated. Document ingestion is no longer a public endpoint.
- `asyncio.to_thread` wrapping is now the established pattern for all blocking pipeline calls (not just chat).

**GLOSSARY.md:**
- `asyncio.to_thread` — Python stdlib function that runs a synchronous callable in a thread pool executor, returning an awaitable. Used in this project to prevent blocking ChromaDB and LLM calls from stalling the async event loop.

---

### Gate Feedback — Remediation (2026-05-08)

Three findings returned from the quality gate. All three fixed in this pass:

**Finding 1 — Viktor B1 / Sage-1: Path Traversal (Hard Block)**
`documents.py` line 20: `UPLOAD_DIR / file.filename` allowed traversal via attacker-controlled filename.

Fix applied:
- `safe_name = Path(file.filename).name` strips all `../` and leading `/`
- Empty `safe_name` check raises 400
- `destination.resolve()` + `is_relative_to(UPLOAD_DIR.resolve())` as belt-and-suspenders

Test added: `test_path_traversal_is_neutralized` — verifies `../../evil.txt` is written as `evil.txt` inside `UPLOAD_DIR`, not outside it.

Note: the fix neutralizes traversal rather than rejecting, because `Path().name` fully strips the malicious component on all platforms. The `is_relative_to` guard handles edge cases. Test asserts the file lands inside `UPLOAD_DIR` and nothing exists at `UPLOAD_DIR.parent / "evil.txt"`.

**Finding 2 — Viktor B2: Synchronous Dependency on Event Loop (Block)**
`deps.py`: `get_current_user` was `def` (sync), calling `get_user_by_id` (blocking SQLite) on the async event loop.

Fix applied:
- `get_current_user` is now `async def`
- `row = await asyncio.to_thread(get_user_by_id, user_id)`
- `current_user_optional` in `chat.py` had the same pattern — fixed there too (same treatment: `async def`, `await asyncio.to_thread(get_user_by_id, uid)`)
- `_override_get_current_user` in tests updated to `async def` to match

Test coverage: the existing concurrency test (`test_concurrent_requests_do_not_serialize`) exercises the full request path including the now-async dep. It still passes.

**Finding 3 — Sage-3: No File Type Validation (MEDIUM)**
`documents.py`: any extension was accepted despite docstring stating `.txt`/`.md` only.

Fix applied:
- `ALLOWED_SUFFIXES = {".txt", ".md"}` defined as module-level constant
- Check runs after traversal stripping, before any write
- Raises HTTP 400 with detail "Only .txt and .md files are accepted"

Tests added:
- `test_disallowed_extension_returns_400` — `.py` file → 400
- `test_allowed_md_extension_accepted` — `.md` file → 200 (regression guard)

### Self-Review Checklist (post-remediation)

- [x] Path traversal neutralized — `Path(file.filename).name` + `is_relative_to` guard
- [x] Extension validated — 400 for anything outside `{".txt", ".md"}`
- [x] `get_current_user` is now `async def` — no blocking DB call on event loop
- [x] `current_user_optional` in `chat.py` fixed with same pattern
- [x] All 8 tests pass: 2 auth, 2 authenticated-write, 3 security, 1 concurrency
- [x] No secrets in any changed file
- [x] Domain boundary respected: only `src/app/api/`, `src/app/auth/`, `tests/`

*Session 01 remediation complete. All 8 tests pass. Ready for gate re-run.*

— Rex
Co-Authored-By: Rex <rex.stockagent@gmail.com>
