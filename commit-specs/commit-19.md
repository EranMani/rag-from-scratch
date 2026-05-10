# Commit 19 Spec — `profile-ui-panel`
> **Project:** rag-from-scratch · **Assignee:** Aria · **Load only for the active commit.**

---

### Commit 19 — `profile-ui-panel`

**Commit message:** `feat: profile sidebar panel with refreshable knowledge profile display`

**Body:**
Adds a profile sidebar to the main chat page. Structural changes:

1. **Layout refactor**: replaces the single centered `ui.column` container with a
   `ui.row` containing a left sidebar (~280px) and right chat area (`flex:1`).

2. **Dead code removal**: the duplicate inline login form in `index()` (lines ~195–231
   in the current `ui.py`) is removed and replaced with `ui.navigate.to("/login")`.
   This also removes the duplicate `do_login()` closure.

3. **Profile panel**: built with `@ui.refreshable` decorator from day one so Commit 19
   can call `.refresh()` without layout surgery. Fetches `GET /api/profile/me` on
   page load. Displays:
   - Mastery level label
   - Topic scores as `ui.linear_progress` bars (one per module)
   - Identified gaps as a short tag list
   - Query count and "Last active" timestamp

Panel handles the case where `topic_scores` is empty (fresh user) gracefully —
shows "Start chatting to build your profile" message.

**Carry-forwards from Commit 18 (Mira → Aria):**
- `user_level: null` in the SSE `done` event means assessment did not run — display a neutral "—" or "N/A", not "novice"
- `assessed_topics` values are per-turn **deltas** (not absolute scores); do not display them as percentage mastery without combining with the full profile
- The `answer` field exists in `ChatResponse.model_dump()` — if the SSE done event is passed directly to the UI, filter `answer` to avoid a duplicate render
- Cache TTL seam: profile may lag by up to the cache TTL after score changes mid-session; accepted tradeoff, no UI workaround needed

**Assignee:** Aria (`aria.stockagent@gmail.com`)

**Files touched:**
- `src/app/ui.py`

**Depends on:** 06 (profile API), 17 (ChatResponse extended)

**Testing — done when:**
- [ ] Logged-in user sees profile panel on the left side of the chat page
- [ ] Fresh user (no interactions yet) sees the empty-state message, not an error
- [ ] Profile panel loads without blocking the chat area
- [ ] Logging out clears the profile panel
- [ ] Duplicate inline login form is gone from `index()`
