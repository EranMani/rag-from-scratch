# Sage — Worklog
# Project: RAG from Scratch
# Stack: Python / FastAPI / LangGraph / NiceGUI / SQLite / ChromaDB / AWS EC2

---

## Current State
Last reviewed: Commit 18 `adaptive-graph-integration` (gate re-run, second pass)
Open findings unresolved: MEDIUM: hardcoded NiceGUI storage secret : Rex (from Commit 10, still open)
CRITICAL findings this project: 0 — none
Attack surface map (current):
- POST /api/chat — public SSE endpoint; user input flows to LangGraph → LLM; session_id user-controlled memory key
- POST /api/ingest — authenticated (get_current_user); path traversal mitigations verified intact
- POST /api/auth/login, /api/auth/register — credential intake
- GET /api/auth/me — authenticated
- GET /metrics — unauthenticated Prometheus endpoint (pre-existing; not reviewed this session)
- NiceGUI UI layer — calls /api/chat via internal httpx client; stores JWT in app.storage.user
- MemorySaver — in-process, not persisted; keyed by user-supplied session_id with no ownership binding
- OpenAI API key — env-only via pydantic-settings; no hardcoding found
- JWT secret — env-only with 32-char minimum validator; no hardcoding found
- Redis query cache — keyed by SHA-256(question + null-byte + user_level); per-level isolation verified
- mastery_level DB value — coercion guard with warning log on unexpected values; allowlist validated

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 01 | 10 `langgraph-graph-assembly` | Done | No hard blocks; one MEDIUM finding on hardcoded NiceGUI storage secret |

---

## Session 01 — Commit 10: `langgraph-graph-assembly`

**Date:** 2026-05-10
**Status:** Done

### Task Brief

Ad-hoc security review of the SSE streaming refactor. Six areas flagged for
scrutiny: prompt injection / input sanitization, session_id as memory key,
MemorySaver isolation in multi-worker deployments, SSE headers, httpx error
handling in ui.py, and OpenAI API key provenance.

### Findings

**Finding 1 — MEDIUM — Hardcoded NiceGUI storage secret**
File: src/app/ui.py:370
`ui.run_with(fastapi_app, mount_path="/", storage_secret="rag-secret-key")`
Literal string used as the NiceGUI session-storage encryption key. Any attacker
who reads the source (public portfolio = public repo) can forge or decrypt
NiceGUI storage cookies, potentially stealing access tokens stored in
app.storage.user. Mitigation: move to settings.nicegui_storage_secret sourced
from env.

**Finding 2 — LOW — Unbounded session_id memory accumulation (session_id IDOR)**
File: src/app/api/routes/chat.py:138 / src/agents/graph.py:31
MemorySaver holds all thread checkpoints for the process lifetime. An attacker
(anonymous, if allow_anonymous_chat=True) can supply arbitrary session_id values,
either enumerating other users' conversation history (if session IDs are guessable)
or growing the in-process checkpoint store without bound. No max-sessions cap or
ownership binding exists. Mitigation: bind thread_id to authenticated user_id
(e.g., thread_id = f"{user_id}:{session_id}"), reject anonymous callers from
supplying a session_id, and add a per-process session cap.

**Finding 3 — INFO — Prompt injection surface acknowledged, no server-side mitigation**
req.question flows unsanitized into HumanMessage → LLM. For a portfolio RAG app
scoped to educational content, this is expected and acceptable. Noted for
completeness; no action required.

**Finding 4 — INFO — MemorySaver not isolated across workers**
Pre-existing architectural characteristic acknowledged in the commit brief.
Not a security defect in single-worker EC2 deployment.

**Verified clean:**
- /api/ingest auth gate intact (get_current_user, non-optional)
- OpenAI API key: env-only, empty-string default, no hardcoding
- JWT secret: env-only, 32-char minimum enforced at startup
- httpx internal client has 30s timeout, no redirect concerns (localhost only)
- SSE Content-Type set correctly via StreamingResponse media_type
- No shell=True, no eval/exec, no pickle, no raw SQL, no verify=False

### Decisions Made

**1. session_id IDOR rated LOW not HIGH**
The attack requires knowledge of another user's session_id, which is a UUID4
generated client-side and never disclosed in responses. Enumeration is
computationally infeasible. Rated LOW (defense-in-depth) rather than HIGH.
The memory growth concern is real but bounded by the EC2 instance's restart cycle.

**2. Prompt injection rated INFO**
This is a portfolio RAG system, not a privileged action system. The LLM has no
tool access that would amplify injection impact. No server-side mitigation required
at this stage.

