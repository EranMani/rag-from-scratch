# Aria — Worklog
# Project: rag-from-scratch
# Stack: Python / NiceGUI / FastAPI

---

## Current State
*Last updated: Commit 20 · 2026-05-10*

**Last completed:** Commit 20 `dynamic-chat-ui` ✅
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- (none)

**Open Handoffs — Inbound:**
- (none)

**Key Interfaces I Own (for teammates):**
- `src/app/ui.py` — NiceGUI page definitions; main chat + profile sidebar layout

**Decisions Other Agents Must Know:**
- The profile panel is defined as a nested `@ui.refreshable` async function inside `index()`. This keeps it in scope of both `auth_headers()` and `http()` closures without threading those as parameters. Commit 20 must call `profile_panel.refresh()` (not re-invoke `await profile_panel()`) to trigger a re-render.
- The `not can_use_chat` branch now redirects to `/login` instead of rendering an inline form. This eliminates the duplicate `do_login()` closure that previously lived in `index()`.

---

## Session Index
| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 1 | 19 | ✅ Done | Profile panel as nested @ui.refreshable; redirect unauthenticated users to /login |
| 2 | 20 | ✅ Done | _STAGE_LABELS at module level; ui.timer(2.5) with mutable closure list for stage advancement |

---

## Session 02 — Commit 20: `dynamic-chat-ui`

**Date:** 2026-05-10
**Status:** ✅ Done

### Task Brief
Three additions to `send()` in `ui.py`: cycling stage labels with `ui.timer` (2.5s intervals, 3 stages), `profile_panel.refresh()` after each turn, adaptation badge from `done_data["user_level"]`.

### Approach
The cycling label needed a way to mutate state inside a closure defined inside an async function. Python closures can read enclosing variables but cannot reassign them without `nonlocal`. The mutable-list pattern (`stage_idx = [0]`) sidesteps this cleanly — the list object itself is captured by the closure and its contents are mutated in place, no `nonlocal` keyword required. This is a well-understood idiom for NiceGUI timer callbacks, which do not receive parameters. `_STAGE_LABELS` was placed at module level (alongside `_MODULE_LABELS`) because it is a pure constant with no per-request state — module level is the right home for it. The adaptation badge was inserted inside the existing `with ui.row()` context so it flows naturally with the other 4 badges and inherits the same `flex-wrap:wrap` layout. `profile_panel.refresh()` placement was confirmed: it must be called after the `with chat_area:` block closes so the refreshable panel re-renders the full sidebar, not nested inside the card being built.

### Decisions Made
1. **`stage_idx = [0]` mutable list for closure mutation** — avoids `nonlocal` keyword in a nested function inside an async coroutine; the pattern is idiomatic and readable.
2. **`_STAGE_LABELS` at module level** — consistent with `_MODULE_LABELS` placement; the constant has no per-request state so module scope is appropriate.
3. **Adaptation badge inside existing `with ui.row()`** — the badge row already uses `flex-wrap:wrap`, so the adaptation badge sits naturally alongside cache/latency/chunks/trace. No new container needed.
4. **`profile_panel.refresh()` before `send_btn.enable()`** — the sidebar updates while the button is still disabled, preventing a second submit racing the refresh.

### Issues Found Mid-Task
None. Import check passed on first run.

### Gate-Fix — Viktor Block (post-Commit 20)

**Concern 1 — `thinking.delete()` outside `finally`:** The standalone `thinking.delete()` call after the `try/finally` block was unreachable if any exception escaped the `finally`. Moved inside `finally`, after `stage_timer.cancel()`.

**Concern 2 — `_advance` may fire on deleted element:** `ui.timer` callbacks fire on the background event loop; `stage_timer.cancel()` does not drain an already-queued callback. Added `stage_active = [True]` (mutable-list pattern, consistent with `stage_idx = [0]`) at the same scope. Set `stage_active[0] = False` as the first statement in `finally` (before `cancel()`). Added early return guard `if not stage_active[0]: return` at the top of `_advance`.

**Lines changed in `src/app/ui.py`:**
- Line ~347: added `stage_active = [True]` after `stage_idx = [0]`
- Lines ~349–351: added `if not stage_active[0]: return` as first line of `_advance`
- `finally` block: added `stage_active[0] = False` before `stage_timer.cancel()`; added `thinking.delete()` after `cancel()`
- Removed standalone `thinking.delete()` that previously sat after the `try/finally`

### Self-Review Checklist
- [x] Stage labels cycle: Retrieving → Assessing → Generating
- [x] Timer cancelled before `thinking.delete()`
- [x] `profile_panel.refresh()` called after response render
- [x] Adaptation badge shown when `user_level` is non-None
- [x] UI does not break when `user_level` is None (badge simply absent — `if user_level:` guard)
- [x] Import check passes

### Product Fix — Post-gate label corrections

**Fix 1 — Stage label rename:** Changed `"Personalizing your answer..."` to `"Preparing your answer..."` in `_STAGE_LABELS` (module level, line 9). The old label implied user-profile personalization is always active, which is false for cold-start users with no established profile. The new label is accurate for all users.

**Fix 2 — Adaptation badge phrasing:** Replaced the inline `f"Adapted for: {user_level}"` string with a `_LEVEL_LABELS` dict lookup. The dict maps `beginner → "Simplified for clarity"`, `intermediate → "Standard depth"`, `advanced → "Full technical detail"`. The dict was defined at module level (alongside `_STAGE_LABELS` and `_MODULE_LABELS`) as `_LEVEL_LABELS: dict[str, str]`. The fallback `f"Adapted for: {user_level}"` is preserved for any unexpected level string so the badge always renders.

### Documentation Flags for Claude
**DECISIONS.md:**
- Stage label cycling uses `stage_idx = [0]` (mutable list in closure) rather than `nonlocal`. This is the standard pattern for NiceGUI timer callbacks, which cannot receive parameters.

**ARCHITECTURE.md:**
- `send()` now calls `profile_panel.refresh()` after each completed turn — sidebar live-updates topic scores without a page reload.
- Cycling stage labels (`ui.timer`, 2.5s interval) replace the static "Thinking..." label during SSE streaming.

---

## Session 01 — Commit 19: `profile-ui-panel`

**Date:** 2026-05-10
**Status:** ✅ Done

### Task Brief
Refactor the main chat page layout to a two-column row (profile sidebar left, chat right). Remove the duplicate inline login form from `index()`. Build a `@ui.refreshable` profile panel that fetches `GET /api/profile/me` on load and displays mastery level, per-module progress bars, gap tags, query count, and last active date. Handle empty state (fresh user with no topic_scores), error state (API unreachable), null mastery level, and anonymous users gracefully.

### Approach
The original `index()` page was a flat structure: a header, a conditional login block, then a single `ui.column` for chat. The duplicate login block at lines 195–231 was structurally identical to `login_page()` — same `do_login()` closure, same form widgets, same redirect — making it pure dead code once `/login` existed as a dedicated page. The simplest removal was a single `ui.navigate.to("/login"); return` replacing the entire block.

The layout refactor introduced a `ui.row` wrapping a fixed-width sidebar and a `flex:1` chat column. The key structural question was where to define the `@ui.refreshable` panel: as a module-level function (requiring `http` and `auth_headers` as parameters) or as a nested function inside `setup_ui` (closed over them naturally). The nested definition was clearly superior — it avoids parameter threading and matches the pattern already used by `login_page`, `register_page`, and `index` themselves. The panel is `async` because it awaits the HTTP call; NiceGUI supports async refreshable functions natively.

For the `not can_use_chat` branch, the redirect happens before the `ui.row` is constructed, so the profile panel is never instantiated for unauthenticated users — no cleanup needed. Anonymous users who reach the profile panel (via `allow_anonymous_chat=True` but no token) see a "Sign in to track your progress." message rather than a failed API call.

The DB schema confirmed `mastery_level` defaults to `'novice'` (not null) at the DB layer, but the spec requires null-safe display for cases where the schema layer may return None. The guard `profile.get("mastery_level") or "—"` covers both None and empty string without special-casing.

### Decisions Made
1. **Redirect vs. inline form for unauthenticated users**: Replaced the duplicate inline login block with `ui.navigate.to("/login"); return`. The duplicate was 37 lines of code with its own `do_login()` closure — removing it eliminates a maintenance surface where the two forms could drift apart.

2. **`@ui.refreshable` as nested async def**: Defined inside `index()` so it closes over `http()` and `auth_headers()` without parameter threading. The `await profile_panel()` call renders it on page load; Commit 20 calls `profile_panel.refresh()` to re-render after chat responses.

3. **Footer placement**: Moved the footer inside the chat column (not the outer row) so the sidebar scrolls independently of the input area. The footer is a `ui.footer()` scoped to the chat column.

4. **Anonymous user path in profile panel**: A user on an `allow_anonymous_chat=True` instance has no token. Rather than hitting the API and receiving a 401, the panel checks `auth_headers()` first and shows a soft "Sign in to track your progress." message. This avoids a noisy error state for a known-valid condition.

5. **Topic score display for partial profiles**: All 6 module slugs are always rendered when `topic_scores` is non-empty, using `.get(slug, 0.0)` to default missing modules to 0.0. This prevents the panel from showing only the modules a user has encountered so far, which would be a confusing incomplete view.

### Issues Found Mid-Task
- Import check required `PYTHONPATH=src` — the project does not run from the repo root without it. This is pre-existing behavior, not introduced by this commit.

### Self-Review Checklist
- [x] Profile panel renders for logged-in user
- [x] Empty state shown for fresh user (no topic_scores) — "Start chatting to build your profile."
- [x] Error state shown if API fails (no crash) — "Profile unavailable."
- [x] user_level null → displays "—" not "novice" (guarded by `or "—"`)
- [x] @ui.refreshable on profile panel from day one
- [x] Duplicate inline login form removed from index()
- [x] Import check passes — `from app.ui import setup_ui` prints OK

### Documentation Flags for Claude

**DECISIONS.md:**
- Profile sidebar uses a nested `@ui.refreshable` async function rather than a module-level component, so it can close over `http()` and `auth_headers()` without parameter threading. This is the intended pattern for NiceGUI refreshable panels that need request-scoped state.
- Unauthenticated users on the main page are redirected to `/login` (not shown an inline form), eliminating the duplicate `do_login()` closure that previously existed in `index()`.

**ARCHITECTURE.md:**
- Profile sidebar panel — new UI component in `src/app/ui.py`; left sidebar (~280px) in a two-column layout on the main chat page. Fetches `GET /api/profile/me` on load. Decorated `@ui.refreshable` — Commit 20 calls `profile_panel.refresh()` to update after each chat turn.
- Layout change: main chat page now uses `ui.row` (sidebar + chat column) instead of a single centered `ui.column`.
