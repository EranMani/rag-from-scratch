# Commit 26 Spec — `ui-foundation`
> **Project:** rag-from-scratch · **Assignee:** Aria · **Load only for the active commit.**

---

### Commit 26 — `ui-foundation`

**Commit message:** `feat: UI design foundation — Inter font, palette tokens, auth page redesign`

**Body:**
Establishes the visual foundation for the portfolio UI redesign. This commit covers
only the authentication pages and global style injection — no structural changes,
no streaming handlers, no auth logic.

Changes:
- Inject Google Inter font (weights 400, 500, 600, 700) via `ui.add_head_html()` in
  all three page functions (`login_page`, `register_page`, `index`) — each `@ui.page`
  is its own document and requires separate injection
- Add `font-family: 'Inter', system-ui` to all body style declarations
- Add `font-feature-settings: "cv02","cv03","cv04","cv11"` for tabular numerals in stat areas
- Login page background: replace flat `#0f172a` with
  `radial-gradient(ellipse at 60% 0%, #0c2344 0%, #0f172a 60%)`
- Login/Register card: glass morphism — `backdrop-filter: blur(8px)`,
  `background: rgba(30,41,59,0.8)`, `border: 1px solid rgba(255,255,255,0.06)`
- Login/Register: add SVG logo mark (`</>` bracket icon in sky→indigo gradient, ~24px)
  via `ui.html()` above the "Sign in" / "Register" heading
- Login/Register CTA button: `background: linear-gradient(135deg,#0369a1,#4f46e5) !important`,
  `border-radius: 10px`
- Add CSS variable block to the global `<style>` injection in `index()` for palette tokens
  used in subsequent UI commits:
  ```css
  :root {
    --c-bg: #0f172a;
    --c-surface: #1e293b;
    --c-border: #334155;
    --c-accent: #38bdf8;
    --c-accent-2: #818cf8;
    --c-muted: #94a3b8;
    --c-warm: #fb923c;
  }
  ```

**Scope rule (hard):** Only `src/app/ui.py` is modified. Only `login_page()`,
`register_page()`, and the `add_head_html` / `<style>` block within `index()` are
touched. Do not modify any component inside `index()` beyond the style injection block.

**Assignee:** Aria

**Files touched:**
- `src/app/ui.py` (login_page, register_page, add_head_html / style block in index)

**Depends on:** 25

**Testing — done when:**
- [ ] Login page shows radial gradient background
- [ ] Card has visible glass morphism blur effect
- [ ] Logo mark SVG renders above "Sign in" / "Register" heading
- [ ] CTA button shows sky→indigo gradient (not flat blue)
- [ ] Inter font loads (check Network tab for fonts.googleapis.com request)
- [ ] Functional behavior unchanged: login succeeds, register succeeds, redirects work
- [ ] No errors in browser console
