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

**What happened and why:**
[2–3 paragraphs in plain English. What the agent built, what problem it solves,
why this approach was chosen over the alternatives. Written so you can explain it
to someone who didn't read the code.]

**Design pattern / architectural principle:**
[Name the pattern(s) applied — e.g. atomicity, single responsibility, dependency injection,
idempotency, separation of concerns, guard clause, middleware chain, etc.
Then explain in one or two plain sentences what that pattern means in this specific context
and why it matters here. If no named pattern applies, write "N/A".]

**Reasoning & discovery:**
[How did the agent find this solution? What was the bug or problem as initially understood?
What guiding questions or observations pointed toward the answer? What was tried and ruled
out along the way? Synthesized from the agent's Approach note in their worklog — written
so you can follow the thought process, not just read the conclusion.]

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

**What happened and why:**

Before this commit, the `/ingest` endpoint accepted file uploads from anyone — no login required. That meant an unauthenticated user could push documents into the vector database, which would corrupt the knowledge base the RAG pipeline draws from. The fix was to inject FastAPI's `get_current_user` dependency, which rejects any request that doesn't carry a valid JWT. Because there is no legitimate reason to ingest documents anonymously, the mandatory form of the dependency was chosen over the optional variant — the endpoint either has an authenticated user or it refuses.

Two security issues were caught by the quality gate that weren't visible in the initial implementation. First: `file.filename` was being used directly to build the upload path. An authenticated user could send `filename = "../../src/app/core/config.py"` and overwrite arbitrary files on the server — a classic path traversal attack. The fix applies two layers: `Path(file.filename).name` strips any directory components the filename contains, and `.resolve()` + `is_relative_to()` confirms the resulting path still sits inside the intended upload directory. Second: the `get_current_user` dependency was a synchronous function querying SQLite, which means it was running blocking database I/O directly on the async event loop — a throughput bottleneck that worsens under load. It was made `async def` with `asyncio.to_thread` to push that blocking work off the loop.

The ingest operation itself calls ChromaDB's HTTP client and LangChain's `vectorstore.add_documents` — both synchronous. Wrapping the entire operation in `asyncio.to_thread(fn, *args)` keeps the event loop free during those calls. This is the same pattern already established in `chat.py` for the RAG pipeline, so `documents.py` is now consistent with it. A file type guard (`.txt` and `.md` only) was added as a final layer to reject unexpected input before any I/O happens.

**Design pattern / architectural principle:**

*Guard clause* — the authentication check and file extension check both appear at the top of the handler and return immediately on failure. This keeps the happy path unindented and readable, and makes the rejection conditions easy to audit at a glance.

*Dependency injection (FastAPI Depends)* — authentication is not implemented inside the route. It is declared as a parameter dependency. FastAPI resolves it before the handler runs. This means the auth logic is testable in isolation, swappable without touching route code, and visible in the OpenAPI schema automatically.

*Defense in depth* — path confinement uses two independent checks rather than one. `Path(file.filename).name` handles the common case (strip directory components). `is_relative_to(upload_dir)` catches anything that slips through (symlinks, OS-specific edge cases). Either check alone would be adequate for most inputs; together they make the attack surface meaningfully smaller.

**Reasoning & discovery:**

The starting question was which auth dependency to use. The codebase exposes two: `get_current_user` (mandatory — raises 401 if no token) and `current_user_optional` (returns `None` for unauthenticated requests). Because there is no anonymous ingest use case — every document entering the system should be traceable to a user — the mandatory form was the obvious choice. Optional auth would have required an explicit `if current_user is None: raise` check inside the handler, which is just manual re-implementation of what the mandatory dependency already provides.

The path traversal vulnerability was not in the initial implementation — it was caught independently by both Viktor (code review) and Sage (security review) during the quality gate pass. The attack vector is straightforward: multipart form uploads allow arbitrary filenames, and using that filename directly to build a filesystem path hands control of the write destination to the caller. `Path(filename).name` is the standard Python idiom for stripping directory traversal sequences; `is_relative_to` was added as belt-and-suspenders after Sage noted that `.name` alone doesn't catch all OS-specific edge cases.

The async fix for `get_current_user` followed from Sage's observation that a synchronous SQLite query running on the event loop blocks all concurrent requests for its duration. The fix — `async def` + `asyncio.to_thread` — is the same pattern used throughout the codebase for blocking I/O; this commit just extended it to the auth layer.

Testing required a workaround: `app.main` has a lifespan context that initializes ChromaDB on startup, which is unavailable in a unit-test environment. The solution was a minimal test FastAPI app that mounts only the documents router, bypassing the lifespan entirely. This keeps the 9 tests fast, hermetic, and free of infrastructure dependencies.

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
