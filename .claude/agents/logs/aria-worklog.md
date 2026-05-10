# Aria — Worklog
# Project: rag-from-scratch
# Stack: Python / NiceGUI / FastAPI

---

## Current State
*Last updated: Commit 19 · 2026-05-10*

**Last completed:** Commit 19 `profile-ui-panel` ✅
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- Commit 20 (Aria): `profile_panel` is `@ui.refreshable` — call `profile_panel.refresh()` after each chat response to update scores live. The function is defined inside `index()` and is in scope for the `send()` coroutine.

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
