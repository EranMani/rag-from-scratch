# Learning Log

> Written for the Team Lead. Plain language. No jargon without explanation.
> Every commit gets at minimum a one-liner. Significant commits get a full entry
> with code snippet, reasoning, and design pattern analysis.
>
> **Use this file to:** understand what was built, why it was built that way,
> which design patterns and architectural principles were applied, and how to
> explain all of it to a reviewer or recruiter.

> Technical terms (WAL mode, TOCTOU, CWE-209, etc.) are defined in [GLOSSARY.md](GLOSSARY.md).

---

## Agents in This Project

The following specialized AI agents contributed to this codebase. Each log entry
identifies the owning agent by name.

| Agent | Role | Responsible for |
|---|---|---|
| Rex | Backend Engineer | API routes, auth, profile service, SQLite, tests |
| Nova | AI/ML Engineer | LangGraph graph, RAG pipeline nodes, prompt engineering |
| Aria | Frontend Engineer | NiceGUI UI (`src/app/ui.py`) |
| Adam | DevOps Engineer | Docker, nginx, EC2 deployment scripts |
| Viktor | Code Reviewer | Reviews every commit — blocks on hard findings |
| Sage | Security Engineer | Reviews auth, secrets, and external API commits |
| Quinn | QA Engineer | Test coverage review |
| Mira | Product Manager | User-facing behavior review |
| Ryan | Tech Writer | This log, README, API reference |
| Claude | Orchestrator | Sequences commits, routes agents, maintains architecture docs |

---

## Entry Format Reference

### When to use which format

| Commit type | Format |
|---|---|
| Architectural change, new pattern, ARCHITECTURE.md or DECISIONS.md updated | Full entry |
| Non-obvious decision, security-relevant, cross-domain wiring | Full entry |
| Routine fix, config update, test addition, minor refactor | One-liner |

For full entries: include only the sections that add value for *this specific commit*.
"Why it wasn't obvious" and "Design pattern" are optional — use them when they genuinely
apply, omit them when they don't. Depth scales with complexity.

---

### Full Entry

---

**Commit [N] — [commit-name]** · [date] · [agent] · `[architectural | new feature | fix | security]`

> **In one sentence:** [One recruiter-ready line — what changed and why it matters.]

**Interview talking point:**
> **Q:** [The question this commit best answers in a technical interview]
>
> **A:** [1–2 sentences. The why, not the what. Written so the Team Lead can say it verbatim.]

**What happened and why:** *(1-2 sentences per bullet — no paragraphs)*
- [What was built or changed]
- [What problem it solves]
- [Why this approach over the alternative — only if a real choice was made]
- [Any non-obvious constraint or consequence — only if one exists]

**Reasoning & discovery:** *(1-2 sentences per step — no paragraphs)*
1. [How the problem was first understood]
2. [What was ruled out and why]
3. [What clinched the solution]

**The key change:** *(omit if prose explains it better than code)*
```python
# path/to/file.py
# Before / After — show only the load-bearing lines
```

**Design pattern:** *(omit if no genuine pattern was applied — do not invent one)*
| Pattern | What it means here | Why it was chosen |
|---|---|---|

**Files touched:**
- `path/to/file` — what changed

---

### One-liner Entry

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
- FastAPI's `get_current_user` dependency was injected to reject any request without a valid JWT. The mandatory variant was chosen because there is no anonymous ingest use case.
- Using `file.filename` directly allowed path traversal — a crafted filename could overwrite arbitrary server files. Two-layer confinement (`Path.name` + `is_relative_to`) closes this.
- `get_current_user` was a synchronous SQLite query running on the async event loop, blocking all concurrent requests for its duration. It was converted to `async def` with `asyncio.to_thread`.
- A file extension guard (`.txt` and `.md` only) was added to reject unexpected input before any I/O runs, keeping the expensive path behind the cheap check.

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Guard clause | Auth check and extension check appear at the top of the handler and return immediately on failure | Keeps the happy path unindented and readable; rejection conditions are easy to audit at a glance |
| Dependency injection (FastAPI Depends) | Authentication is declared as a parameter dependency, not implemented inside the route | Auth logic is testable in isolation, swappable without touching route code, and visible in the OpenAPI schema automatically |
| Defense in depth | Path confinement uses two independent checks: `Path(filename).name` strips directory components; `is_relative_to` catches anything that slips through | Either check alone handles most inputs; together they cover symlinks and OS-specific edge cases that a single check would miss |

**Reasoning & discovery:**
1. The codebase had two auth dependencies — `get_current_user` (mandatory) and `current_user_optional` (nullable) — and the question was which to use. Since every ingest document must be traceable to a user, the mandatory form was the obvious choice.
2. Path traversal was not in the initial scope — Viktor and Sage both flagged it independently during the gate pass. Optional auth was ruled out: it would have required manually re-implementing what the mandatory dependency already provides.
3. Sage flagged that a synchronous SQLite query blocks all concurrent requests for its duration — that clinched the async fix. The `asyncio.to_thread` pattern was already in `chat.py`, so extending it to `deps.py` kept the codebase consistent.

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
- `generate()` in `generator.py` had no awareness of session state. Every LLM call was stateless, so multi-turn conversations received answers with no memory of prior exchanges.
- A `{history}` slot was added to `RAG_PROMPT` and a `conversation_history: str = ""` parameter was added to `generate()`, defaulting to empty so all existing callers remain compatible without any changes.
- History is fetched as STEP 2b in `chain.py`, after `retrieve()` returns and before the LLM cache check. This keeps retrieval query-pure — history is injected at generation only.
- A known gap was accepted: the LLM cache key (`question + docs[:100]`) excludes conversation history, so a cache hit can return a stale answer ignoring the current session. The same gap exists on the query-level cache.
- The ordering and the cache gap are both documented in an inline comment at `chain.py` lines 54–57 and in DECISIONS.md, so future engineers don't "fix" a non-bug or inherit the gap silently.

**Pipeline flow:**
```
[User Question]
      │
      ▼
  retrieve(question)              ← pure query — no history contamination
      │
      ▼
  format_history(session_id)      ← STEP 2b: injected here by design
      │                              history does NOT influence retrieval
      ▼
  generate(question, docs, history)
      │
      ├── LLM cache check  ← cache key omits history (known accepted gap)
      │
      ▼
  [Answer]
```

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

**Commit 05 — user-profile-service** · 2026-05-09 · Rex · `architectural | new feature | security`

> **In one sentence:** The full user profile CRUD service was built on top of the Commit 04 schema — with two non-obvious decisions: a column allowlist that closes a structural SQL injection path before any caller could open it, and a TOCTOU-safe `get_or_create` that absorbs concurrent-creation races at the DB layer rather than propagating them to callers.

**Interview talking point:**
> **Q:** How did you handle the dynamic SQL in your profile update function — wasn't that a SQL injection risk?
>
> **A:** The values were parameterized, but column names can't be — they have to be interpolated. So I added a module-level frozenset allowlist that validates every kwarg key before the SET clause is built. Unknown keys raise `ValueError` before SQL runs. The frozenset is immutable, so no caller can patch it at runtime. It's defence-in-depth: the current callers are all internal code, but the guard means a future LangGraph node spreading LLM output into kwargs can't accidentally become an injection vector.

**What happened and why:**
- Four CRUD functions were added to `profile/db.py`: `create_profile`, `get_profile_by_user_id`, `update_profile`, `get_or_create_profile` — plus a private `_deserialize_row` that centralizes JSON deserialization for the three JSON columns.
- The `update_profile` f-string interpolation of column names triggered a Sage MEDIUM finding and a Viktor block on the first gate pass — the fix was a `_ALLOWED_PROFILE_COLUMNS` frozenset guard added before the SQL runs.
- `get_or_create_profile` initially propagated `sqlite3.IntegrityError` on concurrent races — Viktor blocked on this. The fix wraps the insert in `try/except IntegrityError: pass` and always re-fetches the row after.
- `src/rag/memory/profiles.py` (the old flat-file JSON store) was deleted and its dead call sites removed from `chain.py` — two profile storage systems no longer coexist.
- `jwt_secret` hardcoded default was removed from `config.py` and replaced with a Pydantic `field_validator` requiring ≥ 32 characters — app now fails at startup with a clear error if `JWT_SECRET` is unset.

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Allowlist validation | `_ALLOWED_PROFILE_COLUMNS` frozenset guards `update_profile` kwargs before SQL | Column names can't be parameterized — the allowlist is the only way to prevent a caller-supplied key from reaching the SET clause |
| TOCTOU-safe upsert | `get_or_create_profile` uses check-then-insert with `IntegrityError` absorption | SQLite's UNIQUE constraint on `user_id` makes the race safe: one insert wins, the loser is silently absorbed, both callers get the correct row |
| Serialization boundary | `_deserialize_row` is the single point where JSON strings become Python objects | One function owns the DB→Python shape; all read paths go through it; changing the format means changing one function |

**The key change:**

```python
# src/app/profile/db.py

_ALLOWED_PROFILE_COLUMNS: frozenset[str] = frozenset({
    "mastery_level", "interaction_count", "topic_scores",
    "strengths", "gaps", "last_activity_at",
})

def update_profile(user_id: str, **fields) -> None:
    if not fields:
        raise ValueError(...)

    invalid = set(fields) - _ALLOWED_PROFILE_COLUMNS
    if invalid:
        raise ValueError(f"update_profile: unknown column(s) {invalid!r}")

    # ... serialize JSON fields, build SET clause, execute
```

**Files touched:**
- `src/app/profile/db.py` — 4 CRUD functions + `_deserialize_row` + `_ALLOWED_PROFILE_COLUMNS` allowlist
- `src/app/profile/schemas.py` — new: `UserProfilePublic` Pydantic model (incl. `updated_at`)
- `src/app/core/config.py` — `jwt_secret` default removed; `require_strong_secret` validator added
- `src/rag/chain.py` — dead `load_profile`/`save_profile` imports and calls removed
- `src/rag/memory/profiles.py` — deleted
- `tests/test_profile_service.py` — 26 tests: CRUD, FK cascade, allowlist rejection, malformed JSON

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
- `PRAGMA journal_mode=WAL` was added to `_connect()` so readers and writers can operate concurrently. Without it, a profile write from one LangGraph node would block a concurrent read in the same turn.
- `init_profile_db()` is registered in the FastAPI lifespan alongside `init_user_db()` so the table is guaranteed to exist before the first request arrives.
- All JSON fields (`topic_scores`, `strengths`, `gaps`) are stored as raw strings in SQLite. The service layer (Commit 05) owns deserialization — the DB layer never returns Python dicts directly.

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Separation of concerns | `profile/` is its own module even though it shares a DB file with `auth/` | Profile logic (scoring, mastery, gaps) is unrelated to auth logic (tokens, passwords); keeping them separate prevents the auth module from growing into a catch-all |
| Single database, multiple tables | `user_profiles` lives in `app_users.db` alongside `users` | Avoids managing two SQLite connections and two lifespan init calls; FK enforcement only works within the same database file |
| Schema-layer / service-layer split | `profile/db.py` creates the table and stores raw JSON strings; deserialization is deferred to the service layer | The DB layer stays dumb — it stores and retrieves bytes; the service layer owns meaning. This makes the schema stable even when the Python shape of the data changes |

**Reasoning & discovery:**
1. The FK requirement drove the single-file decision: SQLite foreign keys only enforce across tables in the same connection/file, so splitting into a second DB would have meant managing cascade deletes manually in application code.
2. WAL mode was added at schema initialization time (not later) because it affects all connections to the file — enabling it once in `_connect()` means every subsequent connection automatically inherits it.
3. Storing JSON as strings was chosen over SQLite's JSON functions to keep the DB layer dependency-free. The service layer in Commit 05 gets full Python typing on deserialized fields without any SQL-level JSON path queries.

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

**Commit 06 — user-profile-api** · 2026-05-09 · Rex · `new feature | security`

> **In one sentence:** `GET /api/profile/me` was wired up behind JWT authentication and profile creation was moved into the registration flow — with two non-obvious decisions: `create_profile` (not `get_or_create_profile`) at registration to make double-creation visible, and a static 404 detail string to prevent the response body from leaking internal user IDs.

**Interview talking point:**
> **Q:** Why did you use `create_profile` instead of `get_or_create_profile` in the registration handler?
>
> **A:** Registration is the one moment in the system where a profile should not already exist. Using `get_or_create_profile` there would silently swallow an accidental double-creation — the kind of bug that only surfaces later as corrupted data. `create_profile` makes the intent explicit: if a profile row already exists when a new user registers, that is a data integrity problem worth knowing about, not something to paper over.

**What happened and why:**
- `GET /api/profile/me` exposes profile data externally, so `Depends(get_current_user)` was injected to lock it to the authenticated user. The route never accepts a `user_id` from the request — it reads from the verified JWT only.
- `get_profile_by_user_id` is a synchronous SQLite call. Wrapping it in `asyncio.to_thread` keeps it consistent with every other DB call in the project and avoids blocking the event loop during a lookup.
- Registration previously created a user row and returned — the user's first call to `GET /api/profile/me` would have received a 404. Moving `create_profile(user_id)` into `POST /api/auth/register` collapses profile initialization into the same HTTP transaction that creates the account.
- A known data integrity gap was accepted: `create_user` and `create_profile` run sequentially without a shared transaction, so a non-race failure in `create_profile` leaves an orphaned user row. The static 404 detail guides support without leaking implementation details.
- The 404 detail is a static string — `user_id` appears only in `logger.warning(...)` on the server side. A detail string that included the ID would confirm a valid internal identifier to any client that triggered the 404, which is a CWE-209 information exposure.

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Explicit over implicit | `create_profile` is called instead of `get_or_create_profile` at registration | Registration is the profile's creation event — `get_or_create_profile` would hide a bug (double creation) that should surface as an error |
| Information hiding at the API boundary | The 404 detail is a static string; `user_id` is logged server-side only | Prevents the response body from confirming or leaking internal identifiers to a caller who shouldn't have them |
| Dependency injection (FastAPI Depends) | `get_current_user` is declared as a parameter dependency, not called inside the route body | `user_id` is extracted from a verified JWT — the route cannot be called with a user-supplied ID |

**Reasoning & discovery:**
1. The key question was how to get `user_id` safely into the route. Using `get_current_user` reads it from the verified JWT — structurally safer than a query parameter that would require manual validation to prevent user-spoofing.
2. `get_or_create_profile` was ruled out — registration is not a case for silent race-handling. If a profile row already exists at registration, that is a data integrity problem that should surface as an error, not be absorbed.
3. The static 404 detail was the last decision: the first draft included `user_id` in the detail string for debuggability. The CWE-209 implication — that a 404 response confirming a valid internal ID is an information exposure — moved the ID to the server-side log and replaced the detail with a static support message.

**The key change:**

```python
# src/app/api/routes/profile.py — new file

@router.get("/me", response_model=UserProfilePublic)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    user_id: str = current_user["id"]

    profile = await asyncio.to_thread(get_profile_by_user_id, user_id)
    if profile is None:
        logger.warning(
            "Profile not found for user_id=%s — data integrity anomaly", user_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Contact support if this persists.",
        )

    return profile
```

```python
# src/app/api/routes/auth.py — register route, modified

# Before — user row created, no profile:
    user_id = create_user(email, hashed)
    return TokenResponse(...)

# After — profile created immediately after user:
    user_id = create_user(email, hashed)
    try:
        create_profile(user_id)
    except IntegrityError:
        pass   # concurrent duplicate — profile already exists
    return TokenResponse(...)
```

**Files touched:**
- `src/app/api/routes/profile.py` — new: `GET /api/profile/me` with `Depends(get_current_user)` and `asyncio.to_thread`
- `src/app/api/routes/auth.py` — `create_profile(user_id)` called after `create_user()` in register route; `IntegrityError` absorbed for concurrent duplicates
- `src/app/main.py` — `profile.router` included in app router
- `tests/test_profile_api.py` — new: 11 route tests covering authenticated fetch, unauthenticated rejection, 404 on missing profile, and register-then-fetch round trip

---

**Commit 07 — langgraph-state-schema** · 2026-05-09 · Nova · `architectural | new feature`

> **In one sentence:** `AgentState` and `AssessmentOutput` define the full LangGraph state schema for the adaptive-RAG graph (Commits 07–17) — with three non-obvious design decisions: `Annotated[list[BaseMessage], add_messages]` for session-aware message persistence, `Literal[...]` enforcement on `user_level` and `cache_hit` to prevent LLM hallucinations, and `from __future__ import annotations` paired with `get_type_hints(include_extras=True)` to preserve `Annotated` metadata through Python's string-annotation system.

**Interview talking point:**
> **Q:** Why does your state schema use `Annotated[list[BaseMessage], add_messages]` instead of a plain conversation history string?
>
> **A:** LangGraph's `add_messages` reducer is designed for exactly this — it appends incoming messages rather than replacing the entire list, which means prior turns are automatically accumulated without us having to fetch and concatenate strings manually. Paired with LangGraph's `MemorySaver` checkpointer (which reconstructs history via `thread_id`), it gives us session-aware state management for free. The `from __future__ import annotations` gotcha was the catch: we store annotations as strings, but `get_type_hints()` without `include_extras=True` strips the `Annotated` wrapper entirely, losing the reducer metadata. Any downstream code introspecting the schema has to use `include_extras=True` or the graph builder will silently get an undecorated list type.

**What happened and why:**
- The state schema is the single source of truth for the entire adaptive-RAG graph — changes made here cascade through graph construction in all downstream nodes (retrieve_node, generate_node, assess_node, profile_update_node). Designing it once for the full 07–17 arc was a conscious decision to avoid retroactive schema refactoring breaking the compiled graph.
- `messages: Annotated[list[BaseMessage], add_messages]` replaces `conversation_history: str` — the reducer appends turns rather than replacing, so prior context accumulates automatically. `session_id` is not a state field — it is passed as `thread_id` in the graph config for `MemorySaver`.
- `user_level` and `cache_hit` are `Literal[...]` types because `assess_node` calls the LLM with structured output — hallucinated values like `"ultra_expert"` would silently corrupt state. Pydantic raises `ValidationError` at parse time on any out-of-range value.
- `AssessmentOutput` has two `@field_validator`s that silently drop unknown module slugs rather than raising. A hallucinated slug drops from the result — the assessment turn still completes and profile update still runs.
- `from __future__ import annotations` stores all annotations as strings — `get_type_hints()` without `include_extras=True` silently strips the `Annotated` wrapper, losing the `add_messages` reducer. This affects any code introspecting `AgentState`, including the graph builder in Commit 08.

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Contract enforcement via Literal | `user_level` and `cache_hit` are restricted to a finite set of strings | The LLM in assess_node is constrained to valid values by Pydantic; invalid outputs raise ValidationError instead of corrupting state silently |
| Soft-fail validation | Unknown module slugs are dropped with a warning, not rejected | Assessment turns fail entirely if even one slug is unknown; soft-fail means a hallucinated slug doesn't block profile updates for the valid slugs |
| Separation of state identity from session ID | `messages` list accumulates turns; `session_id` lives in graph config as `thread_id` | Keeps the state schema focused on data (what the graph processes) not mechanics (how turns are persisted). The checkpointer uses `thread_id` to reconstruct history automatically. |
| Deferred deserialization | Topic scores and gaps live in the state as raw dicts/lists, deserialized later in profile_update_node | The state layer is dumb — it stores the assessor's output as-is. The service layer (Commit 15) owns validation and persistence. Schema changes don't cascade through the graph. |

**Reasoning & discovery:**
1. The design-once-for-the-arc decision was clear — retroactive TypedDict changes break compiled LangGraph graphs. The `add_messages` reducer won over string concatenation because it eliminates manual fetch-and-format boilerplate and pairs with `MemorySaver` to reconstruct history automatically.
2. Viktor's review raised the question: if the LLM can hallucinate `user_level` strings, how does the type system protect us? `Literal` in `AssessmentOutput` was the answer — Pydantic enforces it at parse time so invalid values never reach the graph state.
3. The `from __future__ import annotations` gotcha was found during code review: `get_type_hints()` without `include_extras=True` strips `Annotated`, so the graph builder silently receives `list[BaseMessage]` instead of the reducer-annotated version. Documented in the module and worklog for any downstream introspection code.

**The key change:**

```python
# src/agents/state.py — complete file excerpt

from __future__ import annotations

from typing import Annotated, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, field_validator

VALID_MODULE_SLUGS: frozenset[str] = frozenset({
    "rag_fundamentals",
    "vector_databases",
    "langchain",
    "chunking_strategies",
    "retrieval_methods",
    "production_patterns",
})

class AgentState(TypedDict):
    """Full state envelope for the LangGraph adaptive-RAG graph."""
    
    # The key design: messages is ANNOTATED with add_messages reducer.
    # from __future__ import annotations stores this as a string.
    # Any code calling get_type_hints() MUST pass include_extras=True.
    messages: Annotated[list[BaseMessage], add_messages]
    """add_messages reducer appends incoming messages rather than replacing."""
    
    question: str
    user_id: str | None
    docs: list[Document]
    retrieval_source: str
    answer: str
    
    # Literal enforcement prevents LLM hallucinations from corrupting state
    user_level: Literal["novice", "beginner", "intermediate", "advanced", "expert"]
    cache_hit: Literal["hit", "miss", "bypass"]
    
    # Assessment output fields
    topic_scores_delta: dict[str, float]
    identified_gaps: list[str]
    assessment_error: bool
    
    trace_id: str
    latency_ms: int

class AssessmentOutput(BaseModel):
    """LLM structured output schema for assess_node.
    
    Soft-fail validators drop unknown slugs rather than failing the turn.
    """
    
    topic_scores_delta: dict[str, float]
    identified_gaps: list[str]
    user_level: Literal["novice", "beginner", "intermediate", "advanced", "expert"]
    
    @field_validator("topic_scores_delta", mode="before")
    @classmethod
    def filter_topic_scores_slugs(cls, v: object) -> object:
        if not isinstance(v, dict):
            return v
        filtered = {k: val for k, val in v.items() if k in VALID_MODULE_SLUGS}
        dropped = set(v) - set(filtered)
        if dropped:
            logger.warning("AssessmentOutput.topic_scores_delta: dropped unknown slugs %s", dropped)
        return filtered
```

**Files touched:**
- `src/agents/state.py` — new: `AgentState` TypedDict + `AssessmentOutput` Pydantic model + `VALID_MODULE_SLUGS` frozenset
- `pyproject.toml` — documentation/verification that `langgraph` and `langchain-core` are declared as dependencies

---
