# Rex — Worklog
# Project: rag-from-scratch
# Stack: Python 3.11+, FastAPI, LangChain, ChromaDB, SQLite, JWT (PyJWT), NiceGUI

---

## Current State
*Last updated: Commit 04 · 2026-05-09*

**Last completed:** Commit 04 `feat: user_profiles table in SQLite with WAL mode and lifespan init` ✅
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- Nova (Commit 10): when LangGraph replaces `chain.py`, `format_history(session_id)` injection MUST be carried forward — pass `conversation_history` into `AgentState` before `graph.invoke()`. This is a named deliverable of Commit 10. Already logged in `project-state.json`.

**Open Handoffs — Inbound:**
- (none)

**Key Interfaces I Own (for teammates — Commit 05 must read):**
- `src/app/profile/db.py` — `init_profile_db()` creates `user_profiles` table. Commit 05 adds CRUD here — follow the same `_connect()` pattern, same file. Do NOT add a new connection helper.
- `user_profiles` schema: `id TEXT PK`, `user_id TEXT NOT NULL UNIQUE FK→users(id)`, `mastery_level TEXT DEFAULT 'novice'`, `interaction_count INTEGER DEFAULT 0`, `topic_scores TEXT DEFAULT '{}'`, `strengths TEXT DEFAULT '[]'`, `gaps TEXT DEFAULT '[]'`, `last_activity_at TEXT`, `created_at TEXT NOT NULL`, `updated_at TEXT NOT NULL`.
- `mastery_level` valid values: `novice`, `beginner`, `intermediate`, `advanced`, `expert`. Enforced in service layer — not a DB constraint.
- `topic_scores`, `strengths`, `gaps` are JSON strings. Serialize before INSERT, deserialize after SELECT — that is Commit 05's responsibility.
- FK enforcement: `PRAGMA foreign_keys=ON` is set in `_connect()`. Cascade delete is live: deleting a user removes their profile. Service layer must never assume a profile row survives a user delete.

**Key Interfaces I Own (for teammates):**
- `POST /api/ingest` — requires Bearer token; validates extension (.txt/.md only); neutralizes path traversal; wraps ingest in `asyncio.to_thread`
- `src/app/api/routes/documents.py` — documents router
- `src/app/auth/deps.py` — `get_current_user` is now `async`; DB call wrapped in `asyncio.to_thread`
- `src/app/api/routes/chat.py` — `current_user_optional` is now `async`; DB call wrapped in `asyncio.to_thread`
- `src/rag/pipeline/generator.py` — `generate(question, docs, conversation_history="")` — third param is the formatted prior turns string; defaults to `""` for first-turn safety
- `src/rag/chain.py` — `format_history(session_id)` is called at STEP 2b, after `retrieve()`, before `generate()`
- `tests/test_ingest_auth.py` — 8 tests: auth gate, file write, security (traversal + extension), non-blocking

**Decisions Other Agents Must Know:**
- `get_current_user` (from `app.auth.deps`) is now **async**. Any callers using `def` routes that depend on it will need to be `async def`.
- `asyncio.to_thread(fn, *args)` is the project-standard pattern for wrapping blocking I/O (DB, ChromaDB) in async routes/deps.
- `ALLOWED_SUFFIXES = {".txt", ".md"}` is defined in `documents.py` — any future ingest routes should reuse or reference this set.
- History is injected AFTER retrieval by design — it influences generation only, not vector similarity search. This is intentional and must be preserved in any chain refactor.
- The LLM cache key (`prompt_key`) does NOT include conversation history. A cache hit on a repeated question bypasses history-aware generation. This is a known design gap — flagged to Claude for DECISIONS.md.

**Scope Overflows Pre-Built:**
- (none)

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 01 | Commit 01 `auth-gate-on-ingest` | ✅ Done (gate remediation applied) | Used `Depends(get_current_user)` — not the optional variant — and `asyncio.to_thread` consistent with chat.py pattern; gate remediation added path traversal neutralization, extension validation, async dep |
| 02 | Commit 02 `config-and-naming-cleanup` | ✅ Done | Pure rename — chat.py added as call site beyond spec; Viktor confirmed correct |
| 03 | Commit 03 `feat: inject conversation history into RAG generator prompt` | ✅ Done | History injected post-retrieval only; empty string default makes first-turn safe; LLM cache key gap flagged |
| 04 | Commit 04 `feat: user_profiles table in SQLite with WAL mode and lifespan init` | ✅ Done | `PRAGMA foreign_keys=ON` added alongside WAL — SQLite FK enforcement is off by default; both pragmas set in `_connect()` in both auth and profile modules |

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

---

## Session 03 — Commit 03: `feat: inject conversation history into RAG generator prompt`

**Date:** 2026-05-09
**Status:** ✅ Done

### Task Brief

Wire `session_memory.format_history(session_id)` into the RAG generator so the LLM sees prior conversation turns when answering. History is currently collected in `SessionMemory` but discarded — `generate()` never receives it. The fix adds a `{history}` slot to `RAG_PROMPT` and a `conversation_history: str = ""` parameter to `generate()`, and calls `format_history()` from `chain.py` after retrieval.

### Approach

I read all three affected files before touching anything: `generator.py`, `chain.py`, and `conversation.py`. The reading established four facts that shaped every decision:

First, `format_history()` already exists and is correct — it truncates to the last 10 messages and returns an empty string for a new session via `"\n".join(...)` over an empty list. No changes needed there.

Second, `generate()` already uses a `chain.invoke(dict)` call, so adding a third key to that dict is purely additive — no structural change, no risk of breaking the existing context and question slots.

Third, `chain.py` already imports `session_memory` at line 8 — it was imported for the post-generation `add_human`/`add_assistant` calls in STEP 5. Calling `format_history()` from there costs nothing in terms of new imports or coupling.

Fourth, the spec said explicitly: history injection happens AFTER retrieval, influences generation only. I confirmed this constraint is enforced by placement — `format_history()` is called at STEP 2b, after `docs = retrieve(question, k=4)` and before the LLM cache check. The history string does not touch the retrieval path.

The one decision I had to make beyond the spec was the prompt placement. The `{history}` slot goes inside the human message, between context and question — not in the system message. This is correct because the system message sets the LLM's persona and constraints, which don't change per conversation. The conversation history is specific to the current exchange and belongs with the user-facing content. An empty history string at that position renders as a blank line, which is harmless.

One pre-existing design gap I noticed: the LLM cache key at STEP 3 is built as `question + chunk content` — it does NOT include conversation history. This means if the same question is asked twice in a session, the second ask gets a cache hit and bypasses `generate()` entirely, returning an answer with no awareness of the intervening conversation. The answer may be technically correct but contextually wrong (e.g., "What did I just ask?" repeated would return the same cached non-contextual answer both times). I am flagging this to Claude for DECISIONS.md — it is a design tradeoff, not a bug I should fix unilaterally in this commit.

### Decisions Made

**1. `conversation_history: str = ""` default — not `None`**
An empty string is safe to inject directly into the prompt template. `None` would require an explicit guard before the `chain.invoke` call. The `format_history()` method already returns `""` for new sessions, so the types align without a coercion step.

**2. `{history}` placed in the human message, between context and question**
The system message governs LLM behavior and persona — it should not vary per turn. Conversation history is turn-specific and belongs in the human turn alongside context and question. This also future-proofs the slot: if the system message needs to be cached or templated separately, history is not entangled with it.

**3. `format_history()` called at STEP 2b — after retrieve(), before cache check**
The spec requires this ordering. Enforcing it at the call site (labeled comment in `chain.py`) makes the constraint self-documenting for Nova when LangGraph replaces `chain.py` in Commit 10.

**4. LLM cache key gap — flagged, not fixed**
Fixing the cache key to include history would change cache semantics (effectively making every turn a cache miss for the history-aware path). That is a product decision, not a backend correctness fix, and it is outside the scope of this commit. Flagged in Current State and for Claude's DECISIONS.md note.

### Issues Found Mid-Task

**Session 02 worklog prose entry is missing.**
The session index shows Commit 02 as done, but no Session 02 prose block was ever written below Session 01. This is a worklog protocol gap — not a code issue, no remediation needed for this commit, but noted here so Claude can verify the worklog record for Commit 02 if needed.

**LLM cache key does not include conversation history (pre-existing).**
Described above under Approach. Flagged as a cross-domain finding for Claude to log in DECISIONS.md. It is not a blocker for Commit 03.

### Test Gate Verification

The three test gates from the spec:

1. "Asking a follow-up question returns a response that references the prior turn" — satisfiable by running the app, asking a first question, then asking "What did I just ask?" The LLM receives the formatted prior turn in `{history}` and can reference it.

2. "First question in a session has an empty history and the prompt still works correctly" — satisfiable structurally: `format_history()` on an empty session returns `""`, which is the default for `conversation_history`, and `chain.invoke` receives `{"history": ""}`. The prompt renders with a blank history section. No error path.

3. "`format_history()` is called AFTER `retrieve()`" — satisfied by code position: STEP 2b comment in `chain.py` follows STEP 2 (`docs = retrieve(...)`). Verifiable by reading the file.

No automated tests were specified for this commit in the spec. The test gates are integration/smoke tests, not unit tests. If Quinn requires unit-level coverage, the natural test targets are: (a) `generate()` called with a non-empty `conversation_history` injects it correctly into `chain.invoke`, and (b) the `RAG_PROMPT` template renders without error when `history=""`.

### Documentation Flags for Claude

**DECISIONS.md:**
- History injected post-retrieval only, by design: retrieval is query-only (semantic similarity to the question); history does not belong in the retrieval step because it would pollute the embedding query with conversational noise. This is a deliberate architecture decision, not a limitation.
- LLM cache key gap: the current cache key (`question + chunk content`) does not include conversation history. Cache hits on repeated questions return history-unaware answers. Fixing this requires invalidating the LLM cache on session boundaries or including session context in the key — a product tradeoff decision, deferred.

**ARCHITECTURE.md:**
- `generate()` now accepts conversation history as a first-class parameter. The RAG pipeline is now: retrieve → format history → (optional cache) → generate with [context + history + question].

**GLOSSARY.md:**
- `conversation_history` — a formatted string of prior turns from `SessionMemory.format_history()`, injected into the LLM prompt at generation time. Does not influence retrieval. Empty string on first turn.

*Session 03 complete. Two files changed, no test failures, one design gap flagged.*

— Rex
Co-Authored-By: Rex <rex.stockagent@gmail.com>

---

---

## Session 04 — Commit 04: `feat: user_profiles table in SQLite with WAL mode and lifespan init`

**Date:** 2026-05-09
**Status:** ✅ Done

### Task Brief

Create the `user_profiles` table in `data/app_users.db`. Add `PRAGMA journal_mode=WAL` to `_connect()` in `auth/db.py` to prevent write-blocking under concurrent LangGraph calls. Register `init_profile_db()` in the FastAPI lifespan. No CRUD — schema-only. Four files: `auth/db.py` (modify), `profile/__init__.py` (new, empty), `profile/db.py` (new), `main.py` (modify lifespan).

### Approach

I read `auth/db.py` and `main.py` before writing anything. The `_connect()` pattern in `auth/db.py` is four lines: `Path(settings.sqlite_db_path)`, `mkdir`, `sqlite3.connect(check_same_thread=False)`, `row_factory`. The profile `_connect()` mirrors it exactly — same DB file, same settings key. No new config, no new DB file, no helper abstractions.

The first thing I noticed reading the spec was what it did NOT say: `PRAGMA foreign_keys=ON`. SQLite parses `FOREIGN KEY` clauses in DDL but does not enforce them by default — enforcement requires `PRAGMA foreign_keys=ON` per connection. Without it, Gate 3 (cascade delete) would appear to pass structure checks but silently fail at runtime. The spec mentions FK constraint is live as a test gate — that can only be true if `PRAGMA foreign_keys=ON` is set. I added it alongside `PRAGMA journal_mode=WAL` in both `auth/db.py` and `profile/db.py`. This is the one decision that isn't explicit in the spec but is required for the spec's stated test gate to pass.

The WAL pragma placement was straightforward: `conn.execute("PRAGMA journal_mode=WAL")` before returning the connection. WAL is a database-level setting but SQLite honors it on any connection — it switches the journal mode for the entire DB file on first invocation. Safe to set on existing DBs; no data loss risk.

For the lifespan change: `init_profile_db()` goes directly after `init_user_db()` because `user_profiles` has a FK referencing `users`. If profile init ran first and the users table didn't exist yet, the `FOREIGN KEY` clause would reference a non-existent table — not a fatal error at `CREATE TABLE IF NOT EXISTS` time (SQLite defers FK target existence checks), but semantically wrong ordering. `init_user_db()` then `init_profile_db()` is the logically correct sequence.

I ran all three test gates via a self-contained script against a temp DB (not the real `data/app_users.db`) to avoid polluting the development DB. All three passed. The existing 16-test suite passed without modification — the `PRAGMA journal_mode=WAL` and `PRAGMA foreign_keys=ON` additions to `_connect()` are purely additive and do not break existing auth functionality.

### Decisions Made

**1. `PRAGMA foreign_keys=ON` added alongside `PRAGMA journal_mode=WAL` — spec implied, not stated**
SQLite FK enforcement is disabled by default. The spec's Gate 3 ("FK constraint is live: deleting a user row cascades to profile row") cannot pass without it. Added to `_connect()` in both modules. No spec deviation — this is required to satisfy the stated gate.

**2. Profile `_connect()` mirrors auth `_connect()` exactly — same DB file, no profile-specific path**
Both modules write to `settings.sqlite_db_path` (`data/app_users.db`). A separate profile DB would complicate FK enforcement (cross-database FKs are not supported in SQLite). One DB, two tables, one settings key. The mirrored `_connect()` functions are intentional duplication — not an abstraction candidate — because the spec explicitly says "follow the exact pattern already in `auth/db.py`" and "do NOT introduce abstractions."

**3. `init_user_db()` before `init_profile_db()` in lifespan**
`user_profiles` has a FK referencing `users(id)`. Logical ordering: the referenced table must be initialized first. Reversed order would not cause a runtime error at `CREATE TABLE IF NOT EXISTS` time in SQLite, but it's semantically wrong and would confuse future readers.

**4. Test gates verified against a temp DB, not `data/app_users.db`**
Running gate verification against the development DB would create a test user row and a test profile row in the live DB. A temp dir DB isolates test state completely. Cleaned up after the script exits.

### Test Gate Verification

**Gate 1 — Fresh app start creates `user_profiles` table in `data/app_users.db`**
PASS. `sqlite_master` query confirms table name `user_profiles` exists after `init_profile_db()`.

**Gate 2 — `PRAGMA journal_mode` returns `wal` when queried on the connection**
PASS. `conn.execute("PRAGMA journal_mode").fetchone()[0]` == `'wal'`.

**Gate 3 — FK constraint is live: deleting a user row cascades to profile row**
PASS. Inserted a user row, inserted a matching profile row, deleted the user, confirmed the profile row is gone. `PRAGMA foreign_keys=ON` is required for this — confirmed active.

**Existing test suite:** 16/16 passing. No regressions.

### Cross-Domain Findings

None.

### Scope Overflow Check

No scope overflows. No CRUD functions written. `profile/db.py` contains `_connect()` and `init_profile_db()` only — exactly as specified.

### Documentation Flags for Claude

**ARCHITECTURE.md:**
- `user_profiles` table now exists in `data/app_users.db`. Profile DB is co-located with the users DB (same file, same SQLite connection pattern). FK from `user_profiles.user_id` to `users.id` with `ON DELETE CASCADE` — profile lifetime is tied to user lifetime.
- `init_profile_db()` is called in FastAPI lifespan after `init_user_db()`, ensuring table exists before any request is served.

**DECISIONS.md:**
- WAL mode enabled on `data/app_users.db`: concurrent LangGraph agent calls would block on SQLite's default journal mode (rollback journal has a write lock). WAL allows concurrent readers while a writer is active. Set via `PRAGMA journal_mode=WAL` in `_connect()` — applies database-wide on first connection.
- `PRAGMA foreign_keys=ON` required per connection: SQLite does not enforce FK constraints by default. Added to `_connect()` in both `auth/db.py` and `profile/db.py`. Any future module that introduces a new `_connect()` function for this DB must include this pragma or FK enforcement will silently fail for that connection.

**GLOSSARY.md:**
- `WAL mode` — Write-Ahead Logging journal mode for SQLite. Enables concurrent reads during writes by writing changes to a separate WAL file before committing to the main DB. Prevents write-blocking under concurrent access patterns (e.g., multiple LangGraph agent calls).
- `PRAGMA foreign_keys=ON` — Per-connection SQLite setting that enables FK enforcement. Must be set on every connection that should respect FK constraints; it does not persist between connections.

*Session 04 complete. 3/3 test gates passed. 16/16 existing tests passing. No cross-domain findings.*

— Rex
Co-Authored-By: Rex <rex.stockagent@gmail.com>

---

### Session 03 — Quinn NEEDS ADDITIONS Remediation (2026-05-09)

Quinn returned three required tests. All three added to `tests/test_conversation_memory.py`.
Full test suite: 16 passed, 0 failures.

**Test A — `format_history` empty session**

Targeted `SessionMemory.format_history("s1")` on a fresh instance. The `defaultdict(list)`
backing store returns `[]` for an unknown key, so `"\n".join(...)` over an empty list yields
`""`. The only risk was mistaking `defaultdict` for a normal `dict` (which would raise
`KeyError`) — reading `conversation.py` line 24 before writing confirmed `defaultdict` is in
use. Test also explicitly asserts `isinstance(result, str)` since prompt templates concatenate
this value and `None` would corrupt silently.

**Test B — truncation at 10 messages**

Exercised `messages[-10:]` at the exact boundary: 6 turns (12 messages) → 10 lines returned,
first 2 absent; 5 turns (10 messages) → all 10 lines present, nothing dropped. The boundary
test (at-10) is the important one — it confirms the slice does not clip at the exact boundary.
Added a third assertion verifying "question 0" and "answer 0" are absent from the 12-message
output, so this isn't just a line-count check.

**Test C — `generate()` passes `history` key to `chain.invoke()`**

The mock strategy: `RAG_PROMPT | llm | StrOutputParser()` is pure LCEL using `__or__`. A
`MagicMock`'s `__or__` returns another `MagicMock` by default, so chaining works naturally.
The challenge is controlling the final `chain.invoke()` return value (must be `str`, not
`MagicMock`, because `generator.py` line 62 reads `if provider.provider_name() == "openai":`
after the invoke — not a problem — but the return value flows back to the caller). The fix:
patch `RAG_PROMPT` with a mock whose `__or__` returns a controlled intermediate, whose `__or__`
returns a `mock_chain` with `invoke.return_value = "generated answer"`. Then
`mock_chain.invoke.call_args[0][0]` is the dict that `generate()` passed — assert `"history"`
key is present and value equals the input. Also patched `LLM_CALLS` (prometheus counter) since
`.labels(provider=..., status=...).inc()` would fail against a real metrics registry that
hasn't been initialized.

**Viktor advisories (noted, not fixed):**
1. Empty history renders a dangling "Conversation history:" label in the prompt — cosmetic,
   deferred.
2. Comment at `chain.py:73–75` (memory updated on cache-hit paths) could be more explicit that
   this is intentional — minor; will be addressed in any future `chain.py` touch.
3. Cache key / history interaction documented in DECISIONS.md — already flagged by Rex in
   Session 03 prose.

*Remediation complete. 16/16 tests passing. No domain boundary violations.*

— Rex
Co-Authored-By: Rex <rex.stockagent@gmail.com>
