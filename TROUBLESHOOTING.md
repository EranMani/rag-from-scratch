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

---

### TRB-006 — `/api/health/services` causes server loop and WebSocket disconnects

**Date:** 2026-05-15
**Component:** API / Health (`src/app/api/routes/health.py`, `src/app/main.py`)
**Symptom:** When the admin panel opened or refreshed, the server entered a loop — WebSocket connections opened and closed instantly in rapid succession, making the app unresponsive. Commenting out only the Chroma probe inside `services_health` restored normal behaviour.

**Root cause:** Three compounding issues:

1. **DNS, not sockets, was the bottleneck.** `chroma_host` is set to `"chroma"` (a Docker service name). Without Docker running, Windows cannot resolve this hostname. Python's `urllib.request.urlopen(url, timeout=2)` and `socket.create_connection` only apply their timeout to the *socket connect phase* — DNS resolution is a separate blocking call that ignores the timeout and can hang for 15–30 seconds on Windows.

2. **Python threads cannot be cancelled.** Wrapping the probe in `asyncio.to_thread` and guarding it with `asyncio.wait_for(..., timeout=2)` appeared to fix the problem but didn't: `wait_for` cancels the *coroutine wrapper*, not the underlying OS thread. The DNS-hung thread kept running for 15–30 seconds regardless, becoming a zombie.

3. **FastAPI and NiceGUI share one event loop.** When `admin_panel()` called `await http().get("/api/health/services")`, it was awaiting a response from an endpoint whose thread pool was slowly filling with zombie DNS threads. Once the pool (default 32 slots) was exhausted, new requests queued indefinitely. NiceGUI's WebSocket heartbeats couldn't be processed in time, so the browser's WebSocket timed out and reconnected — which re-triggered `admin_panel()`, which queued another stuck thread. This was the loop.

**Fix:** Replaced live per-request probing with a background-probe architecture:

- **`src/app/api/routes/health_probe.py`** (new) — `probe_redis()`, `probe_chroma(client)`, and `build_snapshot(client)`. The Chroma probe uses `httpx.AsyncClient`, which delegates DNS resolution to `anyio.getaddrinfo()` — a truly async call that honours the configured timeout end-to-end. No threads involved.

- **`src/app/main.py` lifespan** — creates a dedicated `app.state.probe_http_client` (`httpx.AsyncClient`, no `base_url`), runs one probe before the server starts serving, then launches a background `asyncio.Task` that refreshes `app.state.health_snapshot` every `settings.health_probe_interval_seconds` seconds (default 30). Task is cancelled and client closed cleanly on shutdown.

- **`/api/health/services`** — now returns the cached `app.state.health_snapshot` with zero network I/O on the request path. Adds `"stale": true` if the snapshot is older than `2 × interval`, so a dead background task is visible in the response.

- **`/api/health/ready`** — kept as a live per-request probe (its job is readiness gating, not dashboarding), but now delegates to the shared probe helpers and reuses `app.state.probe_http_client` instead of creating a new client per call.

**Settings added:** `health_probe_interval_seconds` (default `30`) and `health_probe_timeout_seconds` (default `2.0`) in `src/app/core/config.py`.

---

### TRB-007 — Off-topic messages produce a generic model response instead of a RAG redirect

**Date:** 2026-05-16
**Component:** AI / Prompts (`src/agents/prompts/rag.py`)
**Symptom:** Sending "hi there" or any other off-topic message causes the assistant to answer generically (e.g., "Hello! How can I help you?") rather than directing the user to ask about RAG.

**Root cause:** The system prompt templates contained no instruction for handling off-topic or ambiguous input. The model followed its default behaviour and produced a conversational reply regardless of whether the message had anything to do with RAG.

**Fix:** Added a level-calibrated redirect instruction to all six prompt templates (`_DEFAULT_SYSTEM`, `_NOVICE_SYSTEM`, `_BEGINNER_SYSTEM`, `_INTERMEDIATE_SYSTEM`, `_ADVANCED_SYSTEM`, `_EXPERT_SYSTEM`). When the user's message is unrelated to RAG systems and the retrieved context contains nothing relevant, the model responds with a brief redirect naming concrete RAG topics. Tone is tuned per mastery level — warm for novice, terse for expert.

---

### TRB-008 — Empty response card flashes visible during the loading animation

**Date:** 2026-05-16
**Component:** UI (`src/app/ui.py`)
**Symptom:** After sending a message, an empty answer card appears immediately while the three-dot loading animation is still running. The card contains no text until the first streaming token arrives, creating a jarring layout jump.

**Root cause:** The response column (`response_col`) and its inner card were pre-created unconditionally before the SSE stream was opened, so they were mounted in the DOM — and therefore visible — from the moment the send button was clicked.

**Fix:** Call `response_col.set_visibility(False)` immediately after creation. Inside the token event handler, set a `first_token_received = [False]` guard; on the first `token` SSE event, call `response_col.set_visibility(True)` before updating the markdown content. The card now appears exactly when content is available and never before.

---

### TRB-009 — Knowledge check appears after off-topic redirect

**Date:** 2026-05-16
**Component:** AI / Agent node (`src/agents/nodes/assess.py`, `tests/test_assess_node.py`)
**Symptom:** After an off-topic message triggers the redirect response (TRB-007), the UI still renders a "Knowledge Check" card with a curriculum question — even though no real RAG question was asked.

**Root cause:** `_select_test_question` in `assess_node` always completed the full slug-selection and curriculum-file-load path regardless of what `_run_passive_assessment` returned. The passive assessment LLM already classifies off-topic queries as `relevant_slug = None`, but `_select_test_question` discarded that signal and proceeded to set `pending_test_question` unconditionally.

**Fix:** Changed `_run_passive_assessment` return type from `dict[str, float]` to `tuple[dict[str, float], bool]`, where the bool (`is_rag_related`) is `True` when `relevant_slug is not None`. `_select_test_question` now unpacks the tuple and exits early with `test_mode=False, pending_test_question=None` when `is_rag_related` is `False`. The exception fallback returns `({}, True)` — permissive, so a failed LLM classification does not silently suppress knowledge checks on valid queries. Tests updated: stale `assert_not_called` removed, six tests now mock `_run_passive_assessment` directly, and a new `TestOffTopicSuppression` class covers both paths.

---

### TRB-010 — "Where do we start?" incorrectly treated as off-topic

**Date:** 2026-05-16
**Component:** AI / Prompts (`src/agents/prompts/rag.py`)
**Symptom:** A user asking "where do we start?" or "help me learn" receives the off-topic redirect message instead of curriculum guidance — even though they are clearly expressing intent to learn RAG.

**Root cause:** The redirect instruction added in TRB-007 used a single binary condition: "if the context is empty or irrelevant, redirect." Learning-navigation queries (vague but RAG-adjacent) and truly off-topic queries (unrelated to RAG at all) both hit empty retrieved context, so both triggered the redirect. The model had no way to distinguish intent.

**Fix:** Replaced the single redirect block in all six prompt templates with a three-case `INTENT CLASSIFICATION` block, applied in order with a hard stop at the first match:

- **Case 1 — Truly off-topic** (weather, jokes, unrelated topics): redirect as before.
- **Case 2 — Learning navigation intent** ("where do we start?", "what should I learn?", "help me", "what's first?"): respond with the ordered 8-topic curriculum even when context is empty. The curriculum is embedded directly in the prompt so the model can answer without retrieved documents. An explicit permission line — *"You may generate this response even when context is empty"* — prevents fallthrough to Case 1.
- **Case 3 — Specific RAG question**: answer from context only, unchanged.

Curriculum order embedded in the prompt: Embeddings & Similarity → RAG Pipeline Architecture → Chunking Strategies → Vector Databases → Retrieval Methods → Context & Prompting → Evaluation & Metrics → Production Patterns.

---

### TRB-011 — Welcome message is static and impersonal regardless of user history

**Date:** 2026-05-17
**Component:** UI (`src/app/ui.py`)
**Symptom:** Every user — new or returning, regardless of their learning progress — sees the same generic greeting: "Welcome! I am a RAG system that answers questions about how RAG systems work." The system already maintains per-user profiles with mastery level, topic scores, gaps, and strengths, but none of that data surfaces on login.

**Root cause:** The welcome card was a hardcoded `ui.markdown()` call with a static string. No profile data was fetched or consulted at page-load time for the chat area.

**Fix:** Two changes in `src/app/ui.py`:

1. Added `_build_welcome_message(display_name, profile)` at module level. It selects one of five messages based on the user's profile state:

   | Condition | Message style |
   |---|---|
   | No profile (unauthenticated or fetch failed) | Generic fallback |
   | `interaction_count == 0` | First-time journey welcome |
   | `gaps` present | Names up to 2 gap topics, invites the user to work on them |
   | `strengths` present, no gaps, advanced/expert level | Acknowledges mastery, prompts for deeper topics |
   | `strengths` present, no gaps, other level | Acknowledges strengths, invites deeper or new exploration |
   | Returning, no strengths/gaps computed yet | Session count acknowledgement |

2. In `index()`, after `verify_stored_bearer()`, a single `GET /api/profile/me` call populates `_welcome_profile`. The welcome card renders `_build_welcome_message(display_name, _welcome_profile)` instead of the static string. The profile sidebar continues to fetch independently via its existing `@ui.refreshable` function.

---

### TRB-012 — Orchestrator process failures in Commit 27 caused ~350k extra tokens

**Date:** 2026-05-17
**Component:** Orchestration (Claude) — not application code
**Symptom:** A header styling commit that should cost ~60–80k tokens cost ~411k. Three separate orchestrator failures compounded.

---

**Failure 1 — Gate-fix passes run 4× in violation of an explicit written rule**

`team-preferences.md` states: *"Gate-fix passes — eliminated. There are no gate-fix passes. If a reviewer blocks on a system-breaking issue, the owning agent fixes it in a new dedicated commit — not within the current loop. The gate wave does not re-run."*

In C27, the orchestrator ran gate-fix passes anyway — twice on the first attempt (Viktor blocked → Aria fixed → Viktor re-reviewed) and twice on the retry (Viktor+Sage blocked → Aria fixed → Viktor+Sage re-reviewed). Four gate cycles instead of zero.

**Cost:** Each gate-fix + re-review cycle adds one full reviewer pass (~18–24k tokens on Sonnet). Four cycles × two reviewers = ~150–200k extra tokens from this failure alone.

**Fix:** Rule reinforced with a CRITICAL callout at the top of `team-preferences.md` and a lesson added to `.claude/agents/CLAUDE.md`. Memory file `feedback_no_gate_fix_passes.md` written to persist across sessions.

**Correct procedure:** When a reviewer blocks, surface the finding to the Team Lead. The fix becomes its own next commit. The gate does not re-run in the current loop.

---

**Failure 2 — Reviewer agents invoked without `model: "haiku"`, defaulting to Sonnet**

`team-preferences.md` Model Assignments section states Haiku for Viktor, Sage, Quinn, Mira, and Ryan. The orchestrator omitted `model: "haiku"` from every Agent invocation. Reviewers ran on Sonnet (~18–24k tokens each) instead of Haiku (~5–8k each).

**Cost:** 8 reviewer passes in C27 × ~15k extra tokens per pass = ~120k extra tokens from this failure alone.

**Fix:** Explicit `model: "haiku"` parameter added to all reviewer/writer Agent invocations going forward. Memory file `feedback_model_tiering_enforcement.md` written.

---

**Failure 3 — Spec not validated before agent invocation**

The first attempt spec for C27 described changes (box-shadow, font size tweaks, SVG `<text>` gradient) that produced an imperceptible visual change relative to the stated goal ("wow on first impression"). The orchestrator did not cross-check the spec against the goal before invoking Aria.

Additionally, the retry spec written by the orchestrator used `ui.html(f'<span>{label}</span>')` with an unescaped user email — introducing CWE-79 XSS. `ui.html()` renders raw HTML; `ui.label()` auto-escapes. This is a NiceGUI-specific rule the orchestrator should have applied when writing the spec.

**Cost:** Pass 1 rejection = ~186k tokens producing nothing committed. CWE-79 in the retry spec triggered Sage and an additional gate cycle = ~50k extra tokens.

**Fix:** Two pre-invocation checks now required before briefing any implementation agent:
1. Does the spec achieve the stated goal? (If goal is "visually striking" but spec only tweaks font sizes → rewrite the spec.)
2. Does any UI element render user data via `ui.html()`? (If yes → change to `ui.label()`.)

Memory file `feedback_spec_validation_before_invocation.md` written.

---

**SVG rendering lesson (technical, not process)**

The first attempt used an SVG `<text>` element with `fill="url(#gradient-id)"` for the brand mark gradient. SVG gradient fills on `<text>` elements are browser-dependent and failed silently. The reliable technique is SVG `<path>` strokes with `stroke="url(#gradient-id)"` — path strokes with gradient renders correctly across all browsers. This is documented in LEARNING_LOG.md (C27 full entry).

---

### TRB-013 — Admin tab and admin API endpoints accessible to all authenticated users

**Date:** 2026-05-17
**Component:** Auth / API / UI (`src/app/auth/db.py`, `src/app/auth/schemas.py`, `src/app/api/routes/admin.py`, `src/app/api/routes/auth.py`, `src/app/main.py`, `src/app/ui.py`)
**Symptom:** Any logged-in user could see the Admin tab in the UI and call `/api/admin/users` (list all users) and `/api/admin/users/{user_id}` (delete any user). There was no role distinction between regular users and administrators.

**Root cause:** The users table had no role column. The admin API routes only checked `get_current_user` (valid JWT = access granted) with no further privilege check. The Admin tab in the UI was rendered unconditionally for all authenticated sessions.

**Fix:** Four layers updated together so that role enforcement is consistent at the database, API, token, and UI levels:

1. **Database** (`auth/db.py`) — Added `is_admin INTEGER NOT NULL DEFAULT 0` to the `users` table. A safe `ALTER TABLE … ADD COLUMN` migration runs on every startup so existing databases gain the column without data loss. All `SELECT` queries were updated to include `is_admin`. `create_user()` gained an `is_admin: bool = False` parameter. A `seed_admin_user()` function inserts the built-in admin account (`email="admin"`, `password="admin"`, `is_admin=1`) on first startup and is a no-op thereafter.

2. **API routes** (`api/routes/admin.py`) — Both admin endpoints now call `_require_admin(current_user)` before any logic. If `current_user["is_admin"]` is falsy, a **403 Forbidden** is returned immediately. Previously only a 401 (unauthenticated) was possible.

3. **Auth contract** (`auth/schemas.py`, `api/routes/auth.py`) — `UserPublic` gains `is_admin: bool`. The `/api/auth/me` endpoint now returns this field so the UI can read the flag without an extra round-trip. `LoginBody.email` was relaxed from `EmailStr` to `str` so the built-in `admin` username (no `@` sign) passes server-side validation.

4. **UI** (`ui.py`) — `verify_stored_bearer()` stores `is_admin` in `app.storage.user` after each successful `/api/auth/me` call. The Admin tab is created but immediately hidden with `admin_tab.set_visibility(False)` for any session where `is_admin` is not `True`. The login input label was changed from "Email" to "Username or Email" to reflect that the admin account uses a plain username.

**Why only one admin account:** The system is a single-tenant learning tool. Administrative actions (listing and deleting users) carry irreversible consequences — a deleted user loses all mastery history permanently due to `ON DELETE CASCADE`. Granting admin rights to all authenticated users would allow any registered learner to erase other learners' data. A single seeded admin account with a known credential provides operator-level access without exposing a role-promotion endpoint that could be abused.

---

### TRB-014 — "Already have an account?" on the register page flashes the main page before redirecting to login

**Date:** 2026-05-18
**Component:** UI (`src/app/ui.py`)
**Symptom:** Clicking "Already have an account? Sign in" on the register page briefly renders the main chat page (`/`) before the browser lands on `/login`. The flash is visible and feels like a broken navigation.

**Root cause:** The link target was `/` instead of `/login`. The main page's `index()` handler calls `verify_stored_bearer()` — if the user is unauthenticated it redirects to `/login`, but only after the page has already begun rendering. That partial render causes the visible flash.

**Fix:** Changed the link target from `"/"` to `"/login"` so navigation goes directly to the login page with no intermediate stop.

```python
# Before (broken)
ui.link("Already have an account? Sign in", "/").classes("text-sky-400 text-sm")

# After (fixed)
ui.link("Already have an account? Sign in", "/login").classes("text-sky-400 text-sm")
```

---

### TRB-015 — Custom button background overridden by Quasar `.bg-primary !important`

**Date:** 2026-05-19
**Component:** UI / NiceGUI + Quasar (`src/app/ui.py`)
**Symptom:** A button styled with a CSS class (`.rag-signout-btn`) kept rendering with the default Quasar primary blue background despite `background: linear-gradient(...) !important` in the stylesheet. Multiple CSS selector approaches all failed.

**Root cause:** NiceGUI's `ui.button()` defaults `color="primary"`, which causes Quasar to add the class `.bg-primary` to the rendered button element. Quasar's own stylesheet defines `.bg-primary { background: var(--q-primary) !important }`. When two `!important` declarations compete, specificity determines the winner. Our single-class selector `.rag-signout-btn` had specificity `[0,1,0]`, same as `.bg-primary`. A compound selector `.rag-signout-btn.q-btn` raised specificity to `[0,2,0]`, but Quasar's component styles are injected dynamically at component mount time — *after* the `<style>` block in `<head>` — and in modern browsers, when specificity is equal, the later-loaded rule wins. So `.bg-primary` continued to win regardless.

**Fix:** Apply the gradient background as an inline style with `!important` directly on the NiceGUI element via `.style("background:... !important")`. CSS cascade rules place inline `!important` at specificity `[1,0,0,0]`, which beats any stylesheet `!important` rule regardless of load order.

```python
# Failed — CSS class loses to Quasar's runtime-injected .bg-primary
ui.button("Sign out", on_click=logout).classes("rag-signout-btn").props("flat dense")

# Fixed — inline !important has absolute cascade priority
ui.button("Sign out", on_click=logout).classes("rag-signout-btn").props("unelevated dense no-caps").style(
    "background:linear-gradient(135deg,#f97316,#ec4899) !important; "
    "box-shadow:0 4px 18px rgba(236,72,153,0.55) !important; ..."
)
```

**Rule:** For any NiceGUI button where a CSS gradient must override Quasar's color system, set the background via `.style("... !important")` on the element. CSS classes alone cannot reliably win against Quasar's dynamically injected `.bg-{color}` rules.

---

### TRB-016 — Enter key and Shift+Enter conflict in NiceGUI `auto-grow` textarea

**Date:** 2026-05-19
**Component:** UI / NiceGUI (`src/app/ui.py`)
**Symptom:** Attempts to implement "Enter sends, Shift+Enter inserts newline" in the chat input either (a) sent on Enter but also inserted a newline character, (b) broke Enter entirely, or (c) sent on Enter but Shift+Enter also sent instead of inserting a newline.

**Root cause:** Three separate failure modes encountered:

1. `question_input.on("keydown.enter.exact", send)` — Vue's `.exact` modifier fires the Python handler correctly on plain Enter, but does not call `event.preventDefault()`. The textarea (created by `auto-grow`) still inserts a newline *after* dispatching the event to Python, so the input contains a trailing `\n` at send time.

2. JS-only approach (`addEventListener` with `e.preventDefault()` + `btn.click()`) — `btn.click()` on the `.rag-send-btn` DOM element does not trigger NiceGUI's server-side `on_click` event handler. NiceGUI/Quasar buttons wire their server callbacks through Vue's event system, not the native DOM click event. The button visually activates but the Python `send()` coroutine never runs.

3. Combined JS `preventDefault` + Vue `keydown.enter` handler — correctly prevents the newline and fires `send()`, but implementing Shift+Enter reliably in a way that does not accidentally trigger send required additional complexity for minimal user benefit.

**Fix:** Cancelled Shift+Enter support entirely. Used `question_input.on("keydown.enter", send)` with no JS involvement. Single-line send-on-Enter is the standard chat UX pattern and removes all edge cases. The `auto-grow` prop is kept for visual comfort as the user types long single-line queries.

**Rule:** To call a Python NiceGUI event handler from JavaScript, use Vue event bindings (`element.on("event", handler)`) — never simulate DOM clicks on Quasar button elements. Native `element.click()` bypasses Vue's event system and will not reach the server.

---

### TRB-017 — Quasar `.q-tab-panel` default 16 px padding bleeds into full-bleed layout

**Date:** 2026-05-19
**Component:** UI / NiceGUI + Quasar (`src/app/ui.py`)
**Symptom:** The chat page content area showed an unwanted gap around all four edges despite the outer layout row being styled with `padding:0`. Removing padding from `ui.row()` and `ui.column()` elements had no effect.

**Root cause:** Quasar's `.q-tab-panel` component applies `padding: 16px` by default. NiceGUI's `ui.tab_panel()` wraps content in this component. Even with all custom containers at `padding:0`, Quasar's class introduces the gap before any user-authored element is reached.

**Fix:** Added `padding: 0 !important` to the `.q-tab-panel` rule in the page's CSS block. Also added `padding: 0 !important` to `.nicegui-content` for the same reason — NiceGUI's default content wrapper also contributes padding that must be zeroed for full-bleed layouts.

```css
.q-tab-panel { padding: 0 !important; }
.nicegui-content { padding: 0 !important; }
```
