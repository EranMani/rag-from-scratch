# Commit 28 Spec — `ui-chat`
> **Project:** rag-from-scratch · **Assignee:** Aria · **Load only for the active commit.**

---

### Commit 28 — `ui-chat`

**Commit message:** `feat: UI chat area redesign — gradient bubbles, AI accent, knowledge check prominence`

**Design baseline:** The auth pages (Commit 26) set the visual tone — radial gradient, glass morphism, sky→indigo gradient accents, Inter font. The chat area must match that aesthetic register. A reviewer who has seen the login page should feel visual continuity when they arrive in the chat. Do not fall below the auth page's quality signal.

**Body:**
Visual redesign of the chat message area only. No changes to streaming logic,
SSE event handlers, `@ui.refreshable` functions, or auth. Strictly style string
changes on existing components.

Changes:
- **Welcome card:** add `border-left: 3px solid #38bdf8` to the initial message card
- **User message bubble:** change background from flat `#0369a1` to
  `linear-gradient(135deg, #0369a1, #1d4ed8)`; keep `border-radius: 12px`
- **AI message card:** add `border-left: 3px solid #38bdf8` — disambiguates AI from
  user at a glance without any layout changes
- **Knowledge Check card:** currently visually buried — make it prominent:
  - Background: `rgba(129,140,248,0.08)`
  - Border: `border: 1px solid rgba(129,140,248,0.4)`
  - Box shadow: `box-shadow: 0 0 12px rgba(129,140,248,0.15)`
  - "Knowledge Check" label: `font-weight: 600; color: #a78bfa`
  - Prepend `✦ ` to the label text string
- **Thinking indicator label:** change color from `#94a3b8` to `#818cf8`

**Scope rule (hard):** Only `src/app/ui.py` is modified. Only the `.style()` string
arguments on the welcome card, user bubble card, AI response card, Knowledge Check
card, and thinking label are changed. Do not touch any `async` / `await` logic,
`ui.update()` calls, `first_token_received`, `stage_timer`, `response_col.set_visibility()`,
or SSE parsing code.

**Assignee:** Aria

**Files touched:**
- `src/app/ui.py` (welcome card, user bubble, AI card, knowledge check card, thinking label — style strings only)

**Depends on:** 27

**Testing — done when:**
- [ ] User message bubbles show gradient (not flat blue)
- [ ] AI message card has visible left blue border
- [ ] Knowledge Check card is visually prominent — indigo border + glow
- [ ] Streaming still works: tokens appear progressively, response card reveals on first token
- [ ] Thinking dots still animate and disappear correctly on response completion
- [ ] Welcome message renders for anonymous and logged-in users without errors
