# Learning Log

> Written for the Team Lead. Plain language. No jargon without explanation.
> Every commit gets at minimum a one-liner. Significant commits get a full entry
> with code snippet, reasoning, and design pattern analysis.
>
> **Use this file to:** understand what was built, why it was built that way,
> which design patterns and architectural principles were applied, and how to
> explain all of it to a reviewer or recruiter.

---

## Entry Format Reference

### Full Entry
*Used for: architectural changes, non-obvious decisions, security-relevant changes,
design pattern applications (atomicity, single responsibility, dependency injection,
idempotency, separation of concerns, etc.) — anything that also touches ARCHITECTURE.md
or DECISIONS.md.*

---

**Commit [N] — [commit-name]** · [date] · [agent] · `[architectural | new feature | optimization | fix]`

> **In one sentence:** [One recruiter-ready line — what changed and why it matters.]

**Interview talking point:**
> **Q:** [The interview question this commit best answers]
>
> **A:** [1–2 sentences max. Demonstrates you understood the why, not just the what. Written so the Team Lead can say it verbatim.]

**What happened and why:**
- [One idea — what was built or changed]
- [One idea — what problem it solves]
- [One idea — why this approach over the alternatives]
- [One idea — any non-obvious constraint or consequence]
- [One idea — what this enables going forward (if relevant)]

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| [pattern name] | [what it does in this specific context] | [why this over the alternative] |
| [pattern name] | [what it does in this specific context] | [why this over the alternative] |

**Reasoning & discovery:**
1. [How the problem was initially understood — what was the bug or gap as first seen]
2. [What was tried or ruled out — alternatives considered and why they didn't fit]
3. [What clinched the solution — the observation or constraint that locked in the answer]

**The key change:**
```[language]
// path/to/file.py — line N
// Before:
[old code]

// After:
[new code]
```

**Files touched:**
- `path/to/file.py` — [what changed here]
- `path/to/other.py` — [what changed here]

---

### One-liner Entry
*Used for: routine fixes, config updates, test additions, minor refactors —
anything that doesn't introduce a new pattern or decision.*

---

**Commit [N] — [commit-name]** · [date] · [agent] · `[fix | config | test | refactor | docs]`

> **In one sentence:** [One recruiter-ready line.]

---

## Entries

---

**Commit 01 — auth-gate-on-ingest** · 2026-05-08 · Rex · `security | new feature`

> **In one sentence:** The document ingest endpoint was locked behind mandatory authentication and hardened against path traversal attacks, establishing the project's pattern for protecting write operations and running blocking I/O safely inside async routes.

**Interview talking point:**
> **Q:** How did you approach securing file upload endpoints in this project?
>
> **A:** I applied three layers in order — auth to verify identity, path confinement to prevent overwriting arbitrary server files via a crafted filename, and `asyncio.to_thread` to keep the upload off the event loop. Each layer is cheap-first: the cheapest check (auth) runs before any I/O touches the filesystem.

**What happened and why:**
- The `/ingest` endpoint accepted unauthenticated uploads, meaning anyone could push documents into the vector database and corrupt the knowledge base the RAG pipeline draws from.
- FastAPI's `get_current_user` dependency was injected to reject any request without a valid JWT; the mandatory variant was chosen because there is no anonymous ingest use case.
- `file.filename` was being used directly to build the upload path — an authenticated user could send `filename = "../../src/app/core/config.py"` and overwrite arbitrary server files; two-layer path confinement (`Path.name` + `is_relative_to`) closes this.
- `get_current_user` was a synchronous SQLite query running on the async event loop, blocking all concurrent requests for its duration; it was converted to `async def` with `asyncio.to_thread`.
- A file extension guard (`.txt` and `.md` only) was added to reject unexpected input before any I/O runs, keeping the expensive path behind the cheap check.

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Guard clause | Auth check and extension check appear at the top of the handler and return immediately on failure | Keeps the happy path unindented and readable; rejection conditions are easy to audit at a glance |
| Dependency injection (FastAPI Depends) | Authentication is declared as a parameter dependency, not implemented inside the route | Auth logic is testable in isolation, swappable without touching route code, and visible in the OpenAPI schema automatically |
| Defense in depth | Path confinement uses two independent checks: `Path(filename).name` strips directory components; `is_relative_to` catches anything that slips through | Either check alone handles most inputs; together they cover symlinks and OS-specific edge cases that a single check would miss |

**Reasoning & discovery:**
1. The initial framing was simply "add auth to ingest" — the codebase already had two auth dependencies (`get_current_user` mandatory, `current_user_optional` nullable) and the question was which to use; because every document entering the system should be traceable to a user, the mandatory form was the obvious choice.
2. The path traversal vulnerability was not in the initial implementation — it was caught independently by both Viktor and Sage during the quality gate pass; optional auth was ruled out because it would have required a manual `if current_user is None: raise` check inside the handler, re-implementing what the mandatory dependency already provides.
3. Sage's observation that a synchronous SQLite query on the event loop blocks all concurrent requests for its duration clinched the async fix; the `async def` + `asyncio.to_thread` pattern was already established in `chat.py`, so extending it to the auth layer made `documents.py` consistent with the rest of the codebase.

**The key change:**

```python
# src/app/api/routes/documents.py

# Before — no auth, no path sanitization, blocking I/O on event loop:
@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    dest = UPLOAD_DIR / file.filename          # path traversal risk
    with open(dest, "wb") as f:
        f.write(await file.read())
    ingest_documents(str(dest))               # blocks the event loop
    return {"status": "ok"}

# After — mandatory auth, two-layer path confinement, non-blocking I/O:
@router.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),   # 401 if no token
):
    if Path(file.filename).suffix.lower() not in {".txt", ".md"}:
        raise HTTPException(status_code=422, detail="Only .txt and .md files accepted")

    safe_name = Path(file.filename).name              # strip directory components
    dest = (UPLOAD_DIR / safe_name).resolve()
    if not dest.is_relative_to(UPLOAD_DIR.resolve()): # belt-and-suspenders confinement
        raise HTTPException(status_code=422, detail="Invalid filename")

    with open(dest, "wb") as f:
        f.write(await file.read())
    await asyncio.to_thread(ingest_documents, str(dest))  # off the event loop
    return {"status": "ok"}
```

**Files touched:**

- `src/app/api/routes/documents.py` — auth dependency injected, path sanitization added, extension check added, `ingest_documents` wrapped in `asyncio.to_thread`
- `src/app/auth/deps.py` — `get_current_user` converted from `def` to `async def` with `asyncio.to_thread` for the SQLite query
- `src/app/api/routes/chat.py` — `current_user_optional` made `async def` to match the same pattern
- `tests/test_ingest_auth.py` — 9 tests covering: unauthenticated rejection (401), valid upload, path traversal attempt, disallowed extension, empty file; uses a minimal isolated FastAPI app to bypass lifespan
- `pyproject.toml` — pytest configuration updated

---

**Commit 02 — config-and-naming-cleanup** · 2026-05-08 · Rex · `chore`

> **In one sentence:** Two misspelled identifiers (`allow_annonymous_chat`, `load_knoweldge_base`) were corrected across all call sites in a single atomic commit, preventing silent `AttributeError` bugs from propagating as the codebase grows.

---

**Commit 03 — wire-conversation-history** · 2026-05-09 · Rex · `architectural | new feature`

> **In one sentence:** Conversation history was wired into the RAG generation step — after retrieval, not before — so the LLM answers in context of the current session without letting prior turns contaminate document selection.

**Interview talking point:**
> **Q:** How did you decide where in the RAG pipeline to inject conversation history?
>
> **A:** Retrieval needs to stay query-pure — injecting history there would blur the semantic search and fetch documents that match earlier turns rather than the current question. History belongs at generation, where it gives the LLM session context without corrupting what gets retrieved.

**What happened and why:**
- `generate()` in `generator.py` had no awareness of session state; every LLM call was stateless, so multi-turn conversations received answers with no memory of prior exchanges.
- A `{history}` slot was added to `RAG_PROMPT` and a `conversation_history: str = ""` parameter was added to `generate()`, defaulting to empty so all existing callers remain compatible without any changes.
- History is fetched as STEP 2b in `chain.py`, after `retrieve()` returns and before the LLM cache check — this is the load-bearing ordering decision: retrieval stays query-pure, history is visible only to the generation step.
- A known gap was surfaced and accepted: the LLM response cache key is `question + docs[:100]` and does not include conversation history, so a cache hit can return a stale answer that ignores the current session's context; the same issue exists on the query-level cache.
- The ordering and the cache gap are both documented in an inline comment at `chain.py` lines 54–57 and in DECISIONS.md, so future engineers don't "fix" a non-bug or inherit the gap silently.

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Separation of concerns | Retrieval operates on the raw question only; generation operates on question + documents + history | Keeps each stage's responsibility distinct — retrieval is a semantic search problem, generation is a language problem; mixing them would make both worse |
| Default-parameter backward compatibility | `conversation_history: str = ""` defaults to empty string | Every existing caller of `generate()` continues to work without modification; the new capability is opt-in by passing a session ID through the chain |
| Defensive inline documentation | The STEP 2b comment in `chain.py` names the ordering constraint and explains why it is intentional | Prevents a future engineer from "simplifying" the code by moving the history fetch before retrieval, which would silently break semantic search quality |

**Reasoning & discovery:**
1. The initial framing was straightforward — surface `session_memory.format_history()` inside the LLM call. The question was where in `chain.py` the fetch should live: before retrieval, between retrieval and generation, or inside `generate()` itself.
2. Injecting history before retrieval was ruled out immediately: the retrieval vector search uses the question embedding, and prepending prior turns would shift that embedding toward earlier topics, causing the retriever to surface documents relevant to the conversation history rather than the current question.
3. The cache gap was discovered during the STEP 2b insertion: the LLM response cache key is constructed from `question + docs[:100]` at the point the history fetch was inserted, making it obvious that history is never part of the cache key. The decision to accept this gap rather than invalidate the cache or add history to the key was made explicit in DECISIONS.md.

**The key change:**

```python
# src/rag/chain.py — STEP 2b (new), inserted between retrieve() and the LLM cache check

# Before — chain went straight from retrieval to cache check with no history:
    docs = retrieve(question, retriever)
    # ... LLM cache check follows immediately

# After — history is fetched between retrieval and generation:
    docs = retrieve(question, retriever)

    # STEP 2b — fetch conversation history AFTER retrieval, not before.
    # Retrieval must use the raw question only so the vector search
    # reflects the current turn, not the accumulated session context.
    # NOTE: the LLM response cache key (question + docs[:100]) does NOT
    # include history — a cache hit will return an answer without current
    # session context. Accepted gap; see DECISIONS.md.
    conversation_history = session_memory.format_history(session_id)

    response = generate(question, docs, conversation_history=conversation_history)
```

**Files touched:**

- `src/rag/pipeline/generator.py` — `RAG_PROMPT` gained a `{history}` slot; `generate()` gained `conversation_history: str = ""` parameter; `chain.invoke()` now passes `"history": conversation_history`
- `src/rag/chain.py` — STEP 2b added: `conversation_history = session_memory.format_history(session_id)` called after `retrieve()`, result passed to `generate()`
- `tests/test_conversation_memory.py` — 7 new tests: empty session returns `""`, truncation boundary at 10 messages (3 tests), `generate()` passes history key to `chain.invoke()` (2 tests)

---

**Commit 04 — user-profile-db-schema** · 2026-05-09 · Rex · `architectural | new feature`

> **In one sentence:** A new `profile` Python package was created to own all user-profile logic, with a `user_profiles` table added to the existing SQLite database — connected to `users` via foreign key — and WAL journal mode enabled to prevent write-blocking under concurrent LangGraph agent calls.

**Interview talking point:**
> **Q:** How did you structure the user profile data model, and why did you keep it in the same database as the auth tables?
>
> **A:** The `user_profiles` table lives in the same SQLite file as `users` but is owned by a separate Python module. That lets us enforce referential integrity with a foreign key (`user_id → users.id ON DELETE CASCADE`) without managing a second database connection, while keeping the profile domain's code completely separate from the auth domain. WAL mode was added at this point because LangGraph's graph nodes run sequentially per turn and would otherwise serialize on the default SQLite write lock.

**What happened and why:**
- A new Python package `src/app/profile/` was created (`__init__.py` + `db.py`) to own all profile-related DB logic — this separates the domain from `src/app/auth/` even though both tables live in the same file.
- The `user_profiles` table is in `data/app_users.db` — the same file as `users` — so a single `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE` enforces referential integrity: deleting a user automatically removes their profile row.
- `PRAGMA journal_mode=WAL` was added to `_connect()` in `auth/db.py`; WAL allows readers and writers to operate concurrently — without it, a profile write from one LangGraph node would block a read happening in another node of the same turn.
- `init_profile_db()` is registered in the FastAPI lifespan alongside `init_user_db()` so the table is guaranteed to exist before the first request arrives.
- All JSON fields (`topic_scores`, `strengths`, `gaps`) are stored as raw strings in SQLite; the service layer (Commit 05) owns deserialization — the DB layer never returns Python dicts directly.

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Separation of concerns | `profile/` is its own module even though it shares a DB file with `auth/` | Profile logic (scoring, mastery, gaps) is unrelated to auth logic (tokens, passwords); keeping them separate prevents the auth module from growing into a catch-all |
| Single database, multiple tables | `user_profiles` lives in `app_users.db` alongside `users` | Avoids managing two SQLite connections and two lifespan init calls; FK enforcement only works within the same database file |
| Schema-layer / service-layer split | `profile/db.py` creates the table and stores raw JSON strings; deserialization is deferred to the service layer | The DB layer stays dumb — it stores and retrieves bytes; the service layer owns meaning. This makes the schema stable even when the Python shape of the data changes |

**Reasoning & discovery:**
1. The FK requirement drove the single-file decision: SQLite foreign keys only enforce across tables in the same connection/file, so splitting into a second DB would have meant managing cascade deletes manually in application code.
2. WAL mode was added at schema initialization time (not later) because it affects all connections to the file — enabling it once in `_connect()` means every subsequent connection automatically inherits it.
3. Storing JSON as strings was chosen over SQLite's JSON functions to keep the DB layer dependency-free; the service layer in Commit 05 gets full Python typing on deserialized fields without any SQL-level JSON path queries.

**The key change:**

```python
# src/app/profile/db.py — new file

def init_profile_db() -> None:
    conn = _connect()
    conn.execute("""
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
    """)
    conn.commit()

# src/app/auth/db.py — WAL mode added to existing _connect()
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")   # allows concurrent reads during writes
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

**Files touched:**
- `src/app/auth/db.py` — `PRAGMA journal_mode=WAL` added to `_connect()`
- `src/app/profile/__init__.py` — new, empty (makes `profile` a Python package)
- `src/app/profile/db.py` — new, contains `init_profile_db()` only
- `src/app/main.py` — `init_profile_db()` called in FastAPI lifespan alongside `init_user_db()`

---
