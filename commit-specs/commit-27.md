# Commit 27 Spec — `ui-header`
> **Project:** rag-from-scratch · **Assignee:** Aria · **Load only for the active commit.**

---

### Commit 27 — `ui-header`

**Commit message:** `feat: UI header redesign — brand mark, Inter typography, refined nav`

**Body:**
Redesigns the application header. Scope is strictly the `ui.header()` block in `index()`.

Changes:
- Replace plain "Educational RAG System" text with a flex row:
  - SVG brand mark (`</>` bracket icon in sky→indigo gradient, ~20px) via `ui.html()`
  - "RAG Tutor" in Inter 600 weight (`font-weight: 600; font-size: 1.25rem`) —
    shorter and more product-like than the full name
- Subtitle: tighten to `font-size: 0.75rem; color: #64748b`
- Replace `border-bottom: 1px solid #334155` with
  `box-shadow: 0 1px 0 rgba(51,65,85,0.8)` — reads thinner on dark backgrounds
- User email label: tighten to `font-size: 0.72rem`
- Log out button: add `:hover` color transition via `.q-btn:hover` rule in the
  existing `<style>` block (do not add a new `add_head_html` call)

**Scope rule (hard):** Only `src/app/ui.py` is modified. Only the `with ui.header()`
block (~lines 299–321) and one CSS rule added to the existing `<style>` block are
touched. Do not modify tab definitions, panels, the footer, or any logic below the header.

**Assignee:** Aria

**Files touched:**
- `src/app/ui.py` (ui.header block + one CSS rule in existing style block)

**Depends on:** 26

**Testing — done when:**
- [ ] Header shows SVG brand mark + "RAG Tutor" text side by side
- [ ] Inter font applied to header text
- [ ] Box-shadow visible (thin line) replacing the explicit border
- [ ] User email + logout button still display and function correctly for logged-in users
- [ ] Anonymous / logged-out state still shows "Sign in" and "Register" links
- [ ] Functional behavior unchanged: logout clears storage and navigates to "/"
