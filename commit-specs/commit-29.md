# Commit 29 Spec — `ui-sidebar-admin`
> **Project:** rag-from-scratch · **Assignee:** Aria · **Load only for the active commit.**

---

### Commit 29 — `ui-sidebar-admin`

**Commit message:** `feat: UI sidebar and admin redesign — mastery badge, score pills, stat card accents`

**Body:**
Visual redesign of the profile sidebar and admin dashboard. The `@ui.refreshable`
decorator on both panels is preserved — only the style strings and component types
within the panel functions change. All new CSS rules go in the existing `<style>` block
in `index()`, not inside `@ui.refreshable` functions (they re-inject on every refresh).

**Profile sidebar changes:**
- **Mastery tier badge:** replace plain `Level: {mastery}` text label with a color-coded
  chip using `ui.html()` or a styled `ui.label()`:
  - `novice` → `background: rgba(100,116,139,0.2); color: #94a3b8; border: 1px solid #475569`
  - `intermediate` → `background: rgba(56,189,248,0.1); color: #38bdf8; border: 1px solid rgba(56,189,248,0.3)`
  - `advanced` → `background: rgba(129,140,248,0.1); color: #818cf8; border: 1px solid rgba(129,140,248,0.3)`
  - `expert` → `background: linear-gradient(135deg,rgba(56,189,248,0.15),rgba(129,140,248,0.15)); color: #c4b5fd; border: 1px solid rgba(129,140,248,0.4)`
  - All chips: `border-radius: 20px; padding: 0.2rem 0.75rem; font-size: 0.72rem; font-weight: 600; display: inline-block`
- **Score pills:** for each topic, replace the current `ui.label` + `ui.linear_progress` stack
  with a two-element row:
  - Left: topic label (`font-size: 0.72rem; color: #94a3b8`)
  - Right: score % text in monospace (`font-size: 0.72rem; color: #64748b; font-family: ui-monospace, monospace`)
  - Below: keep `ui.linear_progress` but add `.q-linear-progress` CSS rule in the
    `<style>` block to set height to 4px and border-radius to 2px
- **Gap badges:** change background from `#1e3a5f` to `rgba(239,68,68,0.1)`,
  border to `1px solid rgba(239,68,68,0.2)`, color to `#fca5a5` — reads as "needs attention"

**Admin dashboard changes:**
- **Stat cards:** add gradient background `linear-gradient(135deg, rgba(30,41,59,1), rgba(15,23,42,1))`
  + colored top-border per card (using the `stat_card` helper function):
  - USERS card: `border-top: 2px solid #38bdf8`
  - LATEST JOIN card: `border-top: 2px solid #a78bfa`
  - SYSTEM card: `border-top: 2px solid #4ade80` (healthy) or `#f87171` (degraded)
  - STACK card: `border-top: 2px solid #fb923c`
- **Health status chips:** replace the `●` dot + plain text pattern with a proper
  status chip per service:
  - healthy: `background: rgba(74,222,128,0.1); border: 1px solid rgba(74,222,128,0.2); color: #4ade80`
  - degraded: `background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.2); color: #fbbf24`
  - unknown: `background: rgba(100,116,139,0.1); border: 1px solid #475569; color: #64748b`
  - All chips: `border-radius: 20px; padding: 0.1rem 0.6rem; font-size: 0.7rem; display: inline-block`

**Scope rule (hard):** Only `src/app/ui.py` is modified. `@ui.refreshable` decorators,
all `async/await` structure, and all API call logic within panels are untouched.
Any new CSS rules go in the existing `<style>` block in `index()` only.

**Assignee:** Aria

**Files touched:**
- `src/app/ui.py` (profile_panel, admin_panel, existing style block for progress bar CSS)

**Depends on:** 28

**Testing — done when:**
- [ ] Mastery tier badge renders with correct color scheme per level (test with a user at each level)
- [ ] Topic score rows show % text alongside thin (4px) progress bar
- [ ] Gap badges render red-tinted (not blue)
- [ ] `profile_panel.refresh()` works without console errors (no style re-injection)
- [ ] Stat cards show gradient background + colored top-border per card
- [ ] Health chips render with correct color per service status
- [ ] Admin Refresh button still triggers `admin_panel.refresh()` correctly
- [ ] Admin delete operations still function
