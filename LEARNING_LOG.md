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
