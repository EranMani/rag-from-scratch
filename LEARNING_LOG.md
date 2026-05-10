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

**Commit 08 — langgraph-retrieve-node** · 2026-05-09 · Nova · `new feature | architectural`

> **In one sentence:** The first LangGraph node was implemented — `retrieve_node` wraps the retrieval pipeline and infers the retrieval source (Chroma or BM25) without modifying the retriever's signature, using a non-obvious state inspection pattern to detect which backend was available before and after the call.

**Interview talking point:**
> **Q:** How did you determine which retrieval backend was used without modifying the `retrieve()` function signature?
>
> **A:** The callback's `is_available()` method is the single source of truth for Chroma availability. I inspect it both before and after calling `retrieve()` — if it's available both times, Chroma was used; if it's unavailable before the call, BM25 ran. If it was available before but not after (unlikely in production but possible), BM25 was used. This pattern detects which backend handled the call without adding an out-parameter or return wrapper to the retriever itself.

**What happened and why:**
- `retrieve_node` is the first of six nodes in the adaptive-RAG LangGraph graph. It receives the user question from `AgentState`, calls the existing `retrieve()` function, and returns the retrieved documents plus a `retrieval_source` label.
- The `retrieve()` function in `src/rag/pipeline/retriever.py` takes care of routing to Chroma or BM25 based on `chroma_cb.is_available()` — it returns only `list[Document]`, with no signal about which backend ran.
- Rather than modify `retrieve()`'s signature or duplicate the routing logic inside the node, the node inspects the callback's availability before and after the call. If available both times, Chroma ran. Otherwise BM25 ran.
- Three state combinations are possible: both `True` (Chroma), both `False` (BM25), or `True→False` (rare but possible — Chroma became unavailable mid-call, BM25 fallback).
- Eleven tests validate all three CB state transitions, document that empty questions return an empty doc list without raising, and confirm the return dict has exactly `{"docs", "retrieval_source"}`.

**Reasoning & discovery:**
1. The initial design consulted `chroma_cb.is_available()` only after the call — this left the `True→False` transition undetected. Viktor's review caught the gap: if the callback becomes unavailable mid-call, BM25 handles the retrieval, but the node would incorrectly report `"chroma"`.
2. Adding a post-call inspection was ruled out — it doesn't solve the problem for the race case. Inspecting both before and after covers all three paths unambiguously.
3. Modifying `retrieve()`'s return type to include source metadata was rejected: it couples the node to the retriever's implementation and breaks the clean domain separation between `src/agents/` (LangGraph) and `src/rag/pipeline/` (retrieval logic).

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| State query over signature modification | The node inspects `chroma_cb.is_available()` instead of asking `retrieve()` to return source metadata | Avoids coupling the retriever to LangGraph; the node reads the canonical source of truth (the callback's state) rather than trusting a return value |
| Defensive boundary inspection | Both pre- and post-call checks detect all possible CB state transitions | Handles the rare case where Chroma becomes unavailable during retrieval (triggers fallback to BM25) without relying on `retrieve()` to signal it |
| Node-level state enrichment | The retrieval source label is added at the node boundary, not inside `retrieve()` | Retrieval remains a pure query problem; the LangGraph-specific metadata is added at the point where the retriever's output enters the graph |

**The key change:**

```python
# src/agents/nodes/retrieve.py — new file

def retrieve_node(state: AgentState) -> dict:
    """Retrieve documents for the user question and label the retrieval source.
    
    The retrieval source (Chroma or BM25) is inferred by inspecting
    chroma_cb.is_available() before and after the retrieve() call.
    """
    question: str = state["question"]
    
    chroma_available_before: bool = chroma_cb.is_available()
    docs: list[Document] = retrieve(question)
    chroma_available_after: bool = chroma_cb.is_available()
    
    if chroma_available_before and chroma_available_after:
        retrieval_source: str = "chroma"
    else:
        retrieval_source: str = "bm25"
    
    return {"docs": docs, "retrieval_source": retrieval_source}
```

**Files touched:**
- `src/agents/nodes/retrieve.py` — new: `retrieve_node` with pre/post CB availability inspection
- `tests/test_retrieve_node.py` — new: 11 tests covering both CB available, both unavailable, available-then-unavailable transitions; empty question handling; return dict shape validation

---

**Commit 09 — langgraph-generate-node** · 2026-05-09 · Nova · `new feature | architectural`

> **In one sentence:** The second LangGraph node was implemented — `generate_node` applies adaptive prompt engineering by building a context-aware system message at runtime and calling the LLM async, with two non-obvious decisions: per-invocation `get_provider()` to detect callback state changes and async-by-design for streaming readiness without future refactoring.

**Interview talking point:**
> **Q:** Why do you call `get_provider()` inside the node instead of using a module-level LLM singleton?
>
> **A:** The callback opens after startup. A module-level singleton would freeze before that CB state changes. Per-invocation lets every generation turn see the current callback state — if OpenAI is open, Ollama is used as fallback. The cost is one function call per turn. The benefit is the node automatically adapts to infrastructure state changes without requiring a restart or manual refresh.

**What happened and why:**
- `generate_node` is the second of six LangGraph nodes. It reads `state["docs"]`, `state["messages"]`, and `state["user_level"]`, builds a system message with retrieved context, and calls the LLM with full conversation history.
- The system message is constructed dynamically at invocation time, incorporating both the retrieved documents and the user's proficiency level. This allows the prompt to adapt per turn without modifying `RAG_PROMPT` or `generate()`.
- `get_provider().get_llm()` is called inside the node body so the LLM instance reflects the current callback state. If the callback freezes after startup, subsequent turns still see the update and use Ollama fallback.
- The node uses `await llm.ainvoke()` (async) instead of wrapping `llm.invoke()` in `asyncio.to_thread()`. This is intentional: when `graph.astream_events()` is wired in a later commit, token-level streaming events fire automatically with no changes needed to this node.
- `add_messages` reducer in the state schema appends new AIMessages rather than replacing the list, so prior conversation history is automatically available to the LLM without manual fetch-and-format.

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Per-invocation provider lookup | `get_provider()` is called inside the node, not at module level | Detects callback state changes post-startup so the node automatically uses Ollama fallback if OpenAI becomes unavailable |
| Runtime prompt assembly | System message is built at invocation time with current `user_level` and retrieved docs | Allows prompt adaptation per turn without modifying the underlying generator function or duplicating RAG_PROMPT |
| Streaming-ready async design | Uses `await llm.ainvoke()` rather than `asyncio.to_thread(llm.invoke())` | When Commit 10 adds `graph.astream_events()`, token-level callbacks fire automatically; no refactoring needed |
| State reducer for history | `messages` is appended to via `add_messages`, not replaced | Prior conversation is automatically accumulated; the node receives full history without manual joins or fetches |

**Reasoning & discovery:**
1. The initial design used a module-level LLM singleton. Viktor's review flagged the gap: a module-level instance freezes before the CB can open, so the Ollama fallback would never activate at runtime — per-invocation lookup is the only correct approach.
2. Async design was chosen because `on_chat_model_stream` token events in LangChain only fire from a true async context. Wrapping `llm.invoke()` in `asyncio.to_thread()` would miss those events entirely, making the node streaming-incompatible without a future rewrite.
3. The `add_messages` reducer behavior was verified during design: LangGraph appends to the messages list rather than replacing it, so the node receives `state["messages"]` pre-populated with the full conversation. No manual concatenation needed.

**The key change:**

```python
# src/agents/nodes/generate.py — new file

async def generate_node(state: AgentState) -> dict:
    """Generate an answer using the LLM with adaptive prompt and full conversation history.
    
    The system prompt is built at invocation time to adapt the explanation depth
    to the user's current proficiency level. History is appended via add_messages
    reducer and automatically available in state["messages"].
    """
    context: str = "\n\n".join(doc.page_content for doc in state["docs"])
    user_level: str = state.get("user_level", "novice")

    system_msg = SystemMessage(content=(
        "You are an expert on RAG systems. Answer using ONLY the provided context.\n"
        f"Adapt your explanation depth to the user's level: {user_level}.\n\n"
        f"Context:\n{context}"
    ))

    # Per-invocation provider lookup detects callback state changes.
    # If OpenAI became unavailable post-startup, ainvoke() gets Ollama fallback.
    llm = get_provider().get_llm()
    
    messages: list[BaseMessage] = [system_msg] + list(state["messages"])
    response: AIMessage = await llm.ainvoke(messages)

    return {
        "messages": [response],   # add_messages appends — does not replace
        "answer": response.content,
    }
```

**Files touched:**
- `src/agents/nodes/generate.py` — new: `generate_node` with runtime system message construction and async LLM invocation
- `tests/test_generate_node.py` — new: 18 tests covering return shape (answer str, AIMessage in messages, exactly 2 keys), add_messages contract (exactly 1 AIMessage returned), first turn single HumanMessage, second turn full prior conversation forwarded, get_provider() called once per invocation and ainvoke() called not invoke()

---

**Commit 10 — `langgraph-graph-assembly`** · 2026-05-10 · Nova · `architectural | security`

> **In one sentence:** The retrieve and generate nodes were assembled into a LangGraph graph with `MemorySaver` checkpointer for cross-turn persistence, `SessionMemory` was deleted entirely, and `graph.astream_events()` replaced `run_rag_pipeline()` to stream tokens to clients in real time — with two non-obvious decisions: `build_graph(checkpointer)` as a factory function to keep checkpointers isolated between test and production instances, and hoisting the blocking `get_user_level()` call outside the async generator to prevent event loop stalls.

**Interview talking point:**
> **Q:** Why does `build_graph()` take the checkpointer as a parameter instead of using a module-level singleton?
>
> **A:** Each test needs an isolated in-memory `MemorySaver` so thread histories don't bleed across test cases. A module-level graph would share the same checkpointer, causing tests to inherit prior turns from earlier test runs. By injecting the checkpointer, tests instantiate their own `MemorySaver`, and production passes a single instance bound to the server lifespan. When we need to upgrade to `SqliteSaver` or `PostgresSaver` for persistence, we change one line in `main.py` — the graph doesn't care which checkpointer backs it.

**What happened and why:**
- `src/agents/graph.py` exposes `build_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph` — a factory function, not a module-level singleton. This allows tests to pass isolated `MemorySaver` instances and production to manage the checkpointer lifecycle in the FastAPI lifespan.
- The LangGraph graph nodes (retrieve, generate) are wired with `graph.add_node()` and connected with edges. The compiled graph is bound to the checkpointer at build time so multi-turn conversations can retrieve message history via `thread_id` without manual session lookups.
- `chat.py` no longer calls `run_rag_pipeline()` — it creates a `StreamingResponse` wrapping an async generator that iterates `rag_graph.astream_events(version="v2")`. Token events (`on_chat_model_stream`) fire as the LLM generates each word, yielding SSE messages to the client immediately.
- Blocking DB call `get_user_level(user_id)` is hoisted **outside** the async generator body and awaited with `asyncio.to_thread()` before `astream_events()` starts. Any blocking call inside the generator body stalls the event loop and prevents token streaming.
- `src/rag/memory/conversation.py` (the `SessionMemory` class) is deleted. LangGraph's `MemorySaver` checkpointer reconstructs conversation history automatically when `thread_id` is passed in the graph config — no manual session fetching needed.
- The public-repo secret exposure (hardcoded `storage_secret="rag-secret-key"` in `ui.py`) was moved to `NICEGUI_STORAGE_SECRET` environment variable with a 32-character minimum validator matching the `jwt_secret` pattern.

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Factory function over module singleton | `build_graph(checkpointer)` takes the checkpointer as a parameter | Tests pass isolated instances; production passes a lifespan-managed instance; swapping to `SqliteSaver` or `PostgresSaver` requires one-line change in `main.py`, not graph rebuild |
| Blocking call hoisting | `get_user_level()` runs with `asyncio.to_thread()` before the generator starts, not inside it | Blocking calls in async generators block the entire event loop, preventing token streaming. Hoisting keeps I/O off the critical path. |
| Checkpointer-based session identity | `thread_id` in graph config (derived from `session_id`) tells the checkpointer which turn history to load | No session table queries needed; checkpointer is the single source of truth for conversation state. |
| SSE streaming via event iteration | The async generator yields SSE `data:` lines for each `on_chat_model_stream` event | Client receives tokens as they arrive, not buffered until the full response is ready. |
| Environment variable for secrets | `NICEGUI_STORAGE_SECRET` is loaded from env, not hardcoded | No secrets in source code; 32-char minimum validator prevents weak keys. |

**Reasoning & discovery:**
1. The factory pattern was not obvious initially — the design began with a module-level compiled graph. Tests discovered the problem: the singleton's checkpointer was shared across test cases, causing message history to leak between independent tests. Injecting the checkpointer solved this and enabled multi-backend support.
2. Token streaming was breaking because the initial design ran `get_user_level()` inside the async generator. This blocks the event loop for 10–100ms per call, causing the LLM's token events to queue up and arrive in large batches instead of streaming. Moving the call outside the generator freed the event loop for the duration of token iteration.
3. The `version="v2"` parameter on `astream_events()` was necessary because v1 events had a different structure. This was discovered during integration testing when token events arrived in an unexpected format.

**Security note:** Hardcoded `storage_secret` in `ui.py` was moved to `NICEGUI_STORAGE_SECRET` environment variable. A Pydantic validator ensures the secret is at least 32 characters — matching the strength requirement for `jwt_secret`. Any missing or weak `NICEGUI_STORAGE_SECRET` causes the application to fail at startup with a clear error message.

**Watch for:** Any blocking I/O added inside `generate_stream()` (the async generator) will stall the event loop and cause token events to batch instead of streaming. Similarly, if test setup forgets to pass a fresh `MemorySaver` instance to `build_graph()`, message history will bleed across test cases. The checkpointer parameter is non-negotiable for test isolation.

**The key change:**

```python
# src/agents/graph.py — factory function, not module-level singleton

def build_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    """Assemble retrieve and generate nodes, compile with the provided checkpointer."""
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile(checkpointer=checkpointer)
```

```python
# src/app/main.py — checkpointer instantiated in lifespan, bound to app.state

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... init_user_db, init_profile_db, set_bm25_fallback ...
    
    checkpointer = MemorySaver()  # Swap to SqliteSaver or PostgresSaver here for persistence
    app.state.rag_graph = build_graph(checkpointer)
    
    yield
```

```python
# src/app/api/routes/chat.py — blocking I/O hoisted outside the generator

async def chat(req: ChatRequest, request: Request, current_user = Depends(current_user_optional)):
    rag_graph = request.app.state.rag_graph
    session_id = req.session_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None
    
    # Hoist the blocking call — run it with asyncio.to_thread BEFORE the generator starts.
    # Any blocking call inside the async generator stalls the event loop.
    user_level = await asyncio.to_thread(get_user_level, user_id)
    
    initial_state = {
        "messages": [HumanMessage(content=req.question)],
        "question": req.question,
        "user_id": user_id,
        "user_level": user_level,
        # ... rest of state ...
    }
    
    config = {"configurable": {"thread_id": session_id}}
    
    async def generate_stream():
        """No blocking I/O here — only async iteration."""
        async for event in rag_graph.astream_events(initial_state, config=config, version="v2"):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
            elif event["event"] == "on_chain_end" and event.get("name") == "LangGraph":
                final_state = event["data"].get("output", {})
        yield f"data: {json.dumps({'type': 'done', 'assessed_topics': final_state.get('topic_scores_delta', {})})}\n\n"
    
    return StreamingResponse(generate_stream(), media_type="text/event-stream")
```

**Files touched:**
- `src/agents/graph.py` — new: `build_graph(checkpointer)` factory function with retrieve/generate wiring
- `src/app/main.py` — lifespan: `MemorySaver` instantiated, passed to `build_graph()`, result bound to `app.state.rag_graph`
- `src/app/api/routes/chat.py` — replace `run_rag_pipeline()` with `StreamingResponse` wrapping `astream_events()` generator; hoist `get_user_level()` outside generator
- `src/rag/chain.py` — `run_rag_pipeline()` removed; `SessionMemory` import removed
- `src/rag/memory/conversation.py` — deleted entirely
- `src/app/core/config.py` — `NICEGUI_STORAGE_SECRET` added with 32-char minimum validator
- `src/app/ui.py` — `storage_secret` parameter now reads from env: `NICEGUI_STORAGE_SECRET`
- `tests/test_chat_streaming.py` — new: 12 tests covering end-to-end SSE streaming, token-by-token arrival, done event structure, multi-turn session persistence via `thread_id`, fallback to BM25 on ChromaDB unavailability

---

**Commit 11 — langgraph-graph-smoke-test** · 2026-05-10 · Nova · `test`

> **In one sentence:** Fourteen smoke tests validate the fully assembled LangGraph graph end-to-end without external services, covering state dict return, non-empty answers, docs lists, retrieval source types, and MemorySaver cross-turn conversation threading — establishing the hard gate before Phase 4 adaptive intelligence commits.

---

**Commit 12 — langgraph-assessment-scaffold** · 2026-05-10 · Nova · `architectural`

> **In one sentence:** Wired the assessment node into the graph as a fully-contracted stub with deterministic fallback, proving the adaptive reasoning pathway compiles and testing infrastructure works before the real LLM call lands in Commit 13.

**Interview talking point:**
> **Q:** How do you structure a commit when a component isn't finished yet but needs to be integrated?
>
> **A:** Build the full skeleton first — input/output contracts, error handling, routing logic — with a stub implementation. This proves the wiring compiles, tests pass, and the fallback mechanism works before the complex part (the real LLM call) arrives. It also makes the real logic *replace* the stub without any structural changes, and makes the fallback path visible and testable from day one.

**What happened and why:**
- Added `assess_node` to `src/agents/nodes/assess.py` with the full input/output contract (`AgentState` → `AssessmentOutput`) and a try/except wrapper around the entire output construction block.
- The LLM call is a stub returning an empty `AssessmentOutput` — the point is proving the signature works, the error handling activates on exception, and the graph compiles.
- Wired `assess_node` into the graph with a conditional edge (`_route_after_assess`) that examines the assessment result and routes to the next node. Both paths currently go to the same destination — that's intentional, making the routing function visible without overcomplicating the decision logic yet.
- Added `update_profile_node` as a one-line passthrough stub in `graph.py` — temporary placement signals this will be extracted and fully implemented in Commit 15.
- The try/except wraps construction, not just an LLM call, so when the real LLM chain replaces the stub in Commit 13, the fallback mechanism works unchanged.

**Reasoning & discovery:**
1. The problem: Commits 13–15 will add assessment logic, profile updates, and adaptive routing, but the graph structure was complete. We needed to prove the assessment node could slot in cleanly without later structural changes.
2. Alternatives considered: (a) Skip the stub and jump straight to the real LLM call — rejected because it couples assessment logic to graph wiring, makes testing fallback harder, and hides integration risk. (b) Use `add_edge` instead of `add_conditional_edges` — rejected because it hides the fallback path in the graph inspector and requires structural changes if Commit 15 diverges the two paths. (c) Wrap only the LLM call, not the entire construction — rejected because real parse errors will happen during `AssessmentOutput` creation, and we want the fallback to catch those too.
3. What clinched it: Viktor's review flagged a dead `if` statement in the first version of `_route_after_assess` (both branches did the same thing). Removing the conditional logic entirely and just returning `"update_profile"` unconditionally was the fix — the point of the function is the named routing hook, not the decision logic (which will come in Commit 15).

**Design pattern:**
| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Stub implementation | assess_node returns an empty `AssessmentOutput` until the real LLM call lands in Commit 13 | Proves the signature and error handling work before the expensive part is written; fallback is testable from day one |
| Explicit error boundary | try/except wraps the entire `AssessmentOutput` construction, not just a hypothetical LLM call | Real parse failures happen during construction, not the call itself; fallback mechanism must be robust to the real failure modes |
| Named routing hook | `_route_after_assess` exists even though both branches route the same way today | Makes the routing decision visible and testable; supports divergence in Commit 15 without graph rewiring; keeps the conditional edge explicit in graph inspection tools |
| Temporary placement | `update_profile_node` stub lives in `graph.py` rather than its own file | Signals one-commit status; Commit 15 creates the real file and moves it, keeping graph.py clean |

**Files touched:**
- `src/agents/nodes/assess.py` — new (84 lines): `assess_node` with full RAGState → AssessmentOutput contract, try/except fallback, stub LLM call returning empty output
- `src/agents/graph.py` — update (+38 lines): assess_node imported and added to graph; `update_profile_node` stub added; `_route_after_assess` conditional router added; edges wired
- `tests/test_assess_node.py` — new (258 lines, 19 tests): Gate 1 validates stub output shape; Gate 2 validates boundary condition (score presence); Gate 3 patches AssessmentOutput to raise and validates fallback triggers; Gate 4 validates conditional edge routing logic; Gate 5 validates the assembled graph compiles

---

**Commit 13 — langgraph-assessment-llm** · 2026-05-10 · Nova · `new feature`

> **In one sentence:** Replaced the stub assessment output with a real LangChain chain piping a structured prompt into `AssessmentOutput`, completing the full assessment loop and unblocking Commit 14–15 profile updates and adaptive routing.

**Interview talking point:**
> **Q:** How do you move from a testable stub to a real LLM integration without breaking the fallback mechanism?
>
> **A:** Keep the error boundary (try/except wrapper) and conditional routing unchanged — they exist at the graph level. Replace only the implementation inside the error boundary (the chain construction). The fallback sees the same interface, so tests and routing logic stay green with zero graph rewiring.

**What happened and why:**
- Replaced the stub `AssessmentOutput()` block in `assess_node` with a real LangChain chain: `assessment_prompt | llm.with_structured_output(AssessmentOutput)`. The try/except and conditional routing from Commit 12 pass through unchanged.
- Created `src/agents/prompts/assessment.py` — a `ChatPromptTemplate` with system (role + task + constraints) and human (context injection) messages. Prompts are code; they need version control, independent review, and test isolation as a module.
- `get_provider()` called per-invocation inside `assess_node`, not at module level. Same pattern as `generate_node` — circuit breaker failover (OpenAI → Ollama) must be observable on every individual call, not frozen at import time.
- `AssessmentOutput.user_level` intentionally NOT written back to `AgentState` yet — avoids state ownership conflict (reading and writing the same field creates circular update risk). Deferred to Commit 15 design review.

**Reasoning & discovery:**
1. The problem: Commit 12 proved the skeleton compiles and routes. Commit 13 fills in the LLM call without breaking the already-tested fallback mechanism or graph wiring.
2. Alternatives considered: (a) Inline the prompt template in `assess.py` — rejected because prompts evolve separately, need prompt-specific tests, and version control is cleaner with independent files. (b) Instantiate LLM at module level with a singleton pattern — rejected because it hides circuit breaker behavior (we can't switch providers without restarting the app) and makes testing harder (can't inject different providers per test).
3. What clinched it: The stub already had the try/except wrapper in the right place. Swapping `AssessmentOutput()` for `assessment_prompt | llm | ...` required zero changes to the error boundary. The fallback mechanism was already testable and complete — this commit is purely the real LLM call replacing the stub.

**The key change:**
```python
# src/agents/nodes/assess.py
# Before (stub):
try:
    output = AssessmentOutput()  # Empty stub
    return {"assessment": output}
except Exception:
    logger.warning("Assessment failed; routing to fallback")
    return {"assessment": None}

# After (real chain):
try:
    assessment_prompt = load_assessment_prompt()  # Imported from prompts/
    provider = get_provider()  # Per-call circuit breaker
    chain = assessment_prompt | provider.llm.with_structured_output(AssessmentOutput)
    output = chain.invoke({"state": state, ...})
    return {"assessment": output}
except Exception:
    logger.warning("Assessment failed; routing to fallback")
    return {"assessment": None}
```

**Design pattern:**
| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Stub→real swap | LLM call replaces one-liner, error boundary and routing unchanged | Decouples integration risk from graph structure; fallback proof carries from Commit 12 to Commit 13 unchanged |
| Prompt as module | `ChatPromptTemplate` lives in `src/agents/prompts/assessment.py` | Prompts are configuration code; independent versioning, testing, and review surface; easier to A/B test variants |
| Per-call provider | `get_provider()` inside `assess_node`, not at module init | Circuit breaker is dynamic; failover (OpenAI → Ollama) is observable on every invocation; test injection is straightforward |
| Explicit state gap | `AssessmentOutput.user_level` computed but not written to `AgentState` | Avoids circular write dependency; defers to Commit 15 design review where profile update logic will clarify ownership |

**Files touched:**
- `src/agents/nodes/assess.py` — replace stub block with real LangChain chain; add prompt loader
- `src/agents/prompts/__init__.py` — new: package marker
- `src/agents/prompts/assessment.py` — new: `ChatPromptTemplate` with system + human messages, topic scoring task, structured output format
- `tests/test_assess_node.py` — add 15 tests: 8 validate real chain output shape and score ranges; 4 test circuit breaker provider switching; 3 validate fallback triggers on parse errors
- `src/agents/nodes/assess.py` — documentation: add docstring explaining user_level deferral and fallback mechanism

---

**Commit 14 — topic-scoring-service** · 2026-05-10 · Rex · `new feature`

> **In one sentence:** A pure-function scoring service establishes the typed contract between the profile domain and the LangGraph agent layer, keeping curriculum awareness out of score computation and domain logic out of the agent graph.

**Interview talking point:**
> **Q:** How do you enforce a clean domain boundary between a persistence layer and an orchestration layer when they need to share computed state?
>
> **A:** We introduced a pure-function service with a TypedDict return type — no DB imports, no FastAPI imports, no side effects — so the agent layer can call it freely without acquiring infrastructure dependencies, and the profile domain owns the scoring formula exclusively.

**What happened and why:**
- `compute_topic_scores()` merges a sparse `assessed_topics` delta into the existing profile, then derives mastery level, strengths (score >= 0.7), and gaps (score <= 0.3) in one pass.
- Without this service, Nova's `update_profile_node` (Commit 15) would have had to implement its own scoring logic — duplicating domain decisions across a domain boundary.
- Unknown-but-numeric slugs are stored; non-numeric values are silently dropped — the service filters on value type rather than an allowlist, so it stays decoupled from the curriculum definition. An allowlist would silently drop valid scores whenever Nova added a topic before the list was updated.
- Score clamping to [0.0, 1.0] is applied silently at the last writeable boundary before profile persistence, guarding against out-of-range LLM output that would corrupt mastery thresholds without raising an immediate error.

**Reasoning & discovery:**
1. The problem was framed as: what is the minimal interface Nova needs from Rex's domain in order to write profile updates without knowing how scores are computed?
2. An allowlist of known module slugs was ruled out — it would couple the scoring service to the curriculum definition and cause silent data loss whenever a new topic was added before the list was updated; curriculum enforcement belongs at Nova's `assess_node` boundary.
3. Value-type filtering (`isinstance(score, (int, float))`) settled the contract: the invariant is "numeric value for any slug," not "only slugs we already know about," which keeps the service stable as the curriculum grows.

**The key change:**
```python
# src/app/profile/scoring.py
# Before: no service existed; scoring logic would have lived in Nova's update_profile_node

# After:
def compute_topic_scores(
    current_profile: dict[str, float],
    assessed_topics: dict[str, float],
    interaction_count: int,  # accepted but unused — part of orchestration contract for Commit 15
) -> TopicScoreUpdate:
    merged = {**current_profile}
    for slug, score in assessed_topics.items():
        if isinstance(score, (int, float)):
            merged[slug] = max(0.0, min(1.0, float(score)))  # silent clamp
    mastery = get_mastery_level(merged)
    return TopicScoreUpdate(
        topic_scores=merged,
        strengths=[s for s, v in merged.items() if v >= 0.7],
        gaps=[s for s, v in merged.items() if v <= 0.3],
        mastery_level=mastery,
    )
```

**Design pattern:**
| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Pure function service | `scoring.py` has no DB access, no FastAPI imports, no side effects | Nova can call it from the agent layer without acquiring infrastructure dependencies; trivially unit-testable |
| Typed contract (TypedDict) | `TopicScoreUpdate` is the shared return type between domains | Gives Nova a stable, inspectable interface; prevents implicit dict conventions from drifting across the domain boundary |
| Boundary enforcement over allowlist | Non-numeric slugs dropped; unknown-but-numeric slugs stored | Decouples scoring from curriculum definition; curriculum enforcement delegated to the correct boundary (Nova's assess_node) |
| Defensive clamping | `max(0.0, min(1.0, score))` at last writeable point | LLM output may be out-of-range; clamping prevents silent corruption of threshold-based mastery logic downstream |

**Files touched:**
- `src/app/profile/scoring.py` — new: `TopicScoreUpdate` TypedDict, `compute_topic_scores()`, `get_mastery_level()`
- `tests/test_scoring.py` — new: 17 unit tests across 4 classes; 172/172 full suite pass

---

**Commit 15 — `profile-update-node`** · 2026-05-10 · Nova · `new feature`

> **In one sentence:** Profile Update Node synchronously merges topic scores from assessment into user profiles and persists them to SQLite, unblocking Commit 18's UI rendering.

**Interview talking point:**
> **Q:** When does the user's profile reflect their learning progress — before or after they see the feedback?
>
> **A:** It reflects it immediately after assessment scoring completes. The profile-update-node merges the newly computed scores into the stored profile and persists the merged result in a single write. By the time the agent graph reaches the final response, the user's profile already contains the latest mastery deltas and interaction count — the UI can show current state, not stale state.

**What happened and why:**
- New `update_profile_node` in `agents/nodes/update_profile.py` reads `topic_scores_delta` and `assessment_error` from `AgentState`, calls `compute_topic_scores()` from Commit 14, then persists merged scores and metadata to SQLite via `update_profile()`.
- Fulfills Commit 12's routing stub and unblocks Commit 18's profile panel, which needs current `last_activity_at` and merged `topic_scores` to render correctly.
- Fast-exit ordering (None user_id check before assessment_error) ensures we never hit the DB for anonymous sessions, even if scoring failed.
- Scoring-derived gaps (from the `TopicScoreUpdate` contract) replace the per-turn LLM `identified_gaps` — this reflects cumulative mastery across sessions, not noise from a single assessment.
- `last_activity_at` timestamp written on every successful profile update; absence breaks the UI's "last active" panel (Commit 18 requirement).

**Reasoning & discovery:**
1. After Commit 14 was complete, the agent graph had scores but no place to persist them. Reading Commit 12's graph code showed a routing stub: `update_profile_node` was sketched but not implemented. Commit 15 had to fill that gap before the UI could render anything meaningful.
2. First draft used `AgentState.identified_gaps` directly as the DB `gaps` column — but reading `profile/db.py` revealed the column name mismatch and the `_ALLOWED_PROFILE_COLUMNS` frozenset. `identified_gaps` was not in the allowlist; `gaps` was. Only the computed gaps from Commit 14 passed validation, so that became the source of truth.
3. The interaction count increment was discovered in the existing profile row during test setup: `interaction_count + 1` had to read the current count from the DB, not assume state carried it. This meant the node must always do a DB read before the write — no shortcut paths.

**The key change:**
```python
# src/agents/nodes/update_profile.py
# Before (Commit 12 stub):
def update_profile_node(state: AgentState) -> dict:
    return {"profile": state.get("profile")}  # no-op pass-through

# After (Commit 15):
def update_profile_node(state: AgentState) -> dict:
    user_id = state.get("user_id")
    if user_id is None:
        return {"profile": None}
    
    assessment_error = state.get("assessment_error", False)
    if assessment_error:
        return {"profile": state.get("profile")}
    
    topic_scores_delta = state.get("topic_scores_delta", {})
    current_profile = db.get_profile(user_id)
    score_update = compute_topic_scores(
        topic_scores_delta=topic_scores_delta,
        current_profile=current_profile,
        interaction_count=current_profile.get("interaction_count", 0)
    )
    merged = db.update_profile(
        user_id=user_id,
        topic_scores=score_update["topic_scores"],
        gaps=score_update["gaps"],
        mastery_level=score_update["mastery_level"],
        last_activity_at=datetime.now(timezone.utc).isoformat()
    )
    return {"profile": merged}
```

**Design pattern:**
| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Guard-clause exits | Null user_id, assessment_error checks run first | Ensures DB is never queried for no-op paths; minimal I/O footprint for error or anonymous cases |
| Domain-boundary contract enforcement | Receives `TopicScoreUpdate` from scoring layer, writes only validated columns | Prevents LLM `identified_gaps` from corrupting the DB; contract makes the contract explicit |
| Timestamp-on-write rule | `last_activity_at` set on every successful persist | UI relies on this for "last active" display; absence produces blank state that confuses users |

**Files touched:**
- `src/agents/nodes/update_profile.py` — new: `update_profile_node()` with guard clauses, scoring integration, and profile persistence
- `src/agents/graph.py` — modified: imported real node, removed inline stub
- `tests/test_update_profile_node.py` — new: 22 tests across 6 classes; all 5 spec gates covered; 194/194 full suite pass

**Commit 16 — `fix-score-delta-semantics`** · 2026-05-10 · Rex · `fix`
> `compute_topic_scores` was treating LLM deltas as absolute scores, silently clamping negatives to 0.0 and losing user weakness signal; fixed to additive merge with clamping to [0.0, 1.0], added 14 isolation tests, 208/208 tests pass.
