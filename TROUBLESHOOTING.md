# Troubleshooting

A running log of bugs, errors, and misconfigurations encountered during development — each entry includes the symptom, root cause, and fix so the same issue is never debugged twice.

---

### TRB-001 — `rag-chroma` container is unhealthy on startup

**Date:** 2026-05-11
**Component:** Docker / ChromaDB
**Symptom:** `dependency failed to start: container rag-chroma is unhealthy` when running `docker compose up -d`. The `app` and other services that depend on `chroma` fail to start.

**Root cause:** The `chromadb/chroma:latest` image does not include `curl`, `wget`, or any HTTP client binary. The health check used `CMD-SHELL` with `curl`, so every probe failed immediately with `curl: not found` (exit 1) — even though the ChromaDB server itself was healthy and responding on port 8000.

**Fix:** Replaced the `curl`-based health check with a raw TCP probe using bash's built-in `/dev/tcp` pseudo-device, which is available in the image. Applied to both `docker-compose.yml` and `docker-compose.prod.yml`.

```yaml
# Before (broken)
test: ["CMD-SHELL", "curl -sf http://localhost:8000/api/v1/heartbeat || exit 1"]

# After (fixed)
test: ["CMD-SHELL", "bash -c 'exec 3<>/dev/tcp/localhost/8000 && echo -e \"GET /api/v2/heartbeat HTTP/1.0\\r\\nHost: localhost\\r\\n\\r\\n\" >&3 && grep -q 200 <&3'"]
```

**Note:** The API path was also updated from `/api/v1/heartbeat` to `/api/v2/heartbeat` while fixing — ChromaDB 1.x still serves both, but v2 is the canonical path going forward.

---

### TRB-002 — Site redirects endlessly between `/` and `/login`

**Date:** 2026-05-11
**Component:** UI / Auth (`src/app/ui.py`)
**Symptom:** Opening the app in a browser causes an infinite redirect loop between the index page (`/`) and the login page (`/login`). The browser eventually shows an "ERR_TOO_MANY_REDIRECTS" error.

**Root cause:** The guard at the top of `login_page()` had an inverted condition:

```python
# Buggy — redirects to "/" when auth IS required
if not settings.allow_anonymous_chat:
    ui.navigate.to("/")
    return
```

When `allow_anonymous_chat = False` (auth required) and the user is unauthenticated:
1. `/` checks auth → not authenticated → redirects to `/login`
2. `/login` sees `not allow_anonymous_chat` is `True` → redirects back to `/`
3. Infinite loop.

**Fix:** Changed the guard to redirect to `/` only when the user genuinely has no reason to be on the login page — either anonymous access is allowed, or they are already authenticated.

```python
# Fixed — src/app/ui.py
if settings.allow_anonymous_chat or await verify_stored_bearer():
    ui.navigate.to("/")
    return
```

---

### TRB-003 — `RuntimeError: Found top level layout element "Footer" inside element "Column"`

**Date:** 2026-05-11
**Component:** UI / NiceGUI layout (`src/app/ui.py`)
**Symptom:** `RuntimeError: Found top level layout element "Footer" inside element "Column". Top level layout elements can not be nested but must be direct children of the page content.` — raised as soon as an authenticated user navigates to the chat page (`/`).

**Root cause:** NiceGUI enforces that `ui.footer()`, `ui.header()`, `ui.left_drawer()`, and `ui.right_drawer()` are **direct children of the page** — they cannot be nested inside any container. The `ui.footer()` (the chat input bar) was placed inside a `ui.column()`, which was itself inside a `ui.row()`:

```
ui.row()            ← outer layout row
  └── ui.column()   ← chat area wrapper
        └── ui.footer()   ← ILLEGAL — must be at page level
```

**Fix:** Moved `ui.footer()` out of all containers to sit as a direct page-level sibling of the outer `ui.row()`. Two height values were also corrected as a result:
- Outer `ui.row()`: `height:calc(100vh - 120px)` → `height:calc(100vh - 144px)` (now accounts for both header ~64px and footer ~80px)
- Inner chat scroll column: `height:calc(100% - 80px)` → `height:100%` (the 80px deduction was compensating for the footer being inside the column — no longer needed)

**Also fixed in the same pass:** `register_page()` guard was `if not settings.allow_anonymous_chat and await verify_stored_bearer()` — this allowed already-authenticated users to reach `/register` when anonymous chat was enabled. Simplified to `if await verify_stored_bearer()` to always redirect authenticated users away from the register page, consistent with the `login_page` guard.

---

### TRB-004 — `thinking.delete()` crashes after async SSE stream resumes

**Date:** 2026-05-15
**Component:** UI / NiceGUI (`src/app/ui.py`)
**Symptom:** Sending a chat message raises an exception in the `finally` block after the SSE stream completes. The "thinking" stage label (`Retrieving context...` / `Preparing your answer...`) was supposed to disappear after the answer arrived, but the call crashed instead.

**Root cause:** `ui.element.delete()` mutates the NiceGUI slot tree and dispatches a DOM deletion message to the browser by resolving the ambient `Client` context. That context is only set inside NiceGUI route handlers and explicit `with client:` blocks. The `send()` coroutine suspends at `await` during the SSE stream; when it resumes in the `finally` block it is back on the event loop but outside any NiceGUI request context — so `delete()` fails trying to look up which client to notify.

**Fix:** Replaced `thinking.delete()` with `thinking.set_visibility(False)`.

`set_visibility` does not touch the slot tree and does not need the ambient context. It pushes a targeted attribute update (`display: none`) using the element's own client reference, which was captured when the label was created inside the route handler and remains valid throughout the coroutine's lifetime.

```python
# Before (broken)
thinking.delete()

# After (fixed)
thinking.set_visibility(False)
```

---

### TRB-005 — Knowledge-check questions never appear in the chat UI

**Date:** 2026-05-15
**Component:** Agent / UI (`src/agents/nodes/assess.py`, `src/rag/chain.py`, `src/app/ui.py`)
**Symptom:** The passive assessment ran and topic scores updated, but the agent never visibly asked the user a test question. The system appeared to operate in passive-only mode despite curriculum questions being defined.

**Root cause:** `assess_node` correctly selected a curriculum question, stored it in `pending_test_question` in LangGraph state, and appended it as an `AIMessage` to the conversation (so the checkpointer held it for the next evaluation turn). However, the SSE stream in `chat.py` filtered events to `langgraph_node == "generate"` only — tokens from `assess_node` were never emitted. The `done` event was built by `build_chat_response`, which did not read `pending_test_question` from state. The question was silently stored but invisible to the user.

**Fix:** Two changes:

1. `src/rag/chain.py` — Added `test_question: str | None = None` to `ChatResponse` and populated it from `state.get("pending_test_question")` in `build_chat_response`. The field travels through the existing `done` SSE event at no extra cost.

2. `src/app/ui.py` — After rendering the answer card and debug info, check `done_data.get("test_question")`. If set, render a styled "Knowledge Check" card with the question text so the user sees it and can type their answer.

The evaluation path (`_is_evaluation_mode` in `assess.py`) was already correct — once users can see the question, the scoring on the next turn works as intended.
