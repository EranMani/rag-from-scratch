# Commit 30 Spec — `ui-landing-page`
> **Project:** rag-from-scratch · **Assignee:** Aria · **Load only for the active commit.**

---

### Commit 30 — `ui-landing-page`

**Commit message:** `feat: add landing page as app entry point with particle network hero (EranMani)`

**Body:**
Adds `/landing` as a new NiceGUI page and redirects unauthenticated users from `/` to
`/landing` instead of `/login`. The landing page is the first thing new users see.

**Requested by EranMani.**

---

### Reference files (read all before writing any code)

- `UI_Design/ui_kits/app/Landing.jsx` — all sections and layout
- `UI_Design/ui_kits/app/ParticleNetwork.jsx` — canvas particle animation
- `UI_Design/ui_kits/app/Brand.jsx` — logo SVG, wordmark, icons
- `UI_Design/colors_and_type.css` — all design tokens
- `UI_Design/reference/design-spec.md` §3.1 — copy, section structure, visual rules
- `UI_Design/screenshots/01-screen.png` — visual target

---

### Sections to implement (in order)

**A — Navbar**
- Left: BrandMark SVG + "RAG Tutor" gradient wordmark
- Center: links "Features · How It Works · Docs" (desktop only, hidden mobile)
- Right: "Start Learning Free →" button (sunset gradient, coral glow)

**B — Hero**
- Background: `<canvas id="rag-particle-canvas">` positioned `inset: 0`, z-index 0, opacity 0.18
- Eyebrow: `"AI-NATIVE LEARNING SYSTEM"` — small caps, `--c-muted`, `letter-spacing: 0.12em`
- H1: `"Master RAG.\nShip with confidence."` — gradient text clip `--g-sunset`, ~3.2rem
- Subheadline: body copy, `--c-muted`, `max-width: 480px`
- CTA row: primary button "Start for Free" → `/register`; ghost link "See how it works ↓"
- Social proof: `"No credit card required · Personalizes to your level instantly"` — tiny, muted, centered
- Right column: HeroMock (fake chat UI preview — use INLINE styles on all mock bubble elements; do NOT use class names shared with the real chat page)

**C — Marquee**
- Full-width horizontal scrolling strip between hero and problem section
- Topics: `RAG Fundamentals · Vector Databases · Retrieval Methods · Chunking Strategies · LangChain · Production Patterns`
- Duplicate the row so the loop is seamless
- CSS: `@keyframes rag-landing-marquee` scrolling left, ~30s linear infinite
- Style: uppercase, 0.75rem, `--c-muted`; dot dividers in `--c-coral`

**D — Problem section**
- Eyebrow: `"THE PROBLEM"`
- H2 gradient: `"RAG is everywhere.\nUnderstanding it deeply is rare."`
- Three body paragraphs (exact copy from design-spec.md §3.1 Section B)
- Right column: before/after comparison cards (bad / good)

**E — Features section**
- Eyebrow: `"HOW IT WORKS"`
- H2: `"Built different."`
- Three feature cards in a row (brain icon / layers icon / check-circuit icon)
- Copy: exact text from design-spec.md §3.1 Section C
- Icons: inline SVG paths from Brand.jsx Icon component — warm/coral/violet colors

**F — Modules section**
- Eyebrow: `"CURRICULUM"`
- H2: `"Six modules. One coherent path."`
- Subhead: `"Designed to build on each other — not to be consumed in isolation."`
- 6 module cards: num · title · desc · progress bar (fill: `--g-sunset`)

**G — CTA footer**
- H2 gradient: `"Start learning today."`
- Body: `"Your first session is free. No setup. No configuration. Just ask your first question and watch the system adapt."`
- Large sunset-gradient button: `"Get Started →"` → `/register`
- Below button: `"Already have an account?"` + Sign in link → `/login`

**H — Site footer**
- BrandMark + wordmark (small)
- `"© 2026 RAG Tutor · retrieve · augment · generate · master"` — `--c-subtle`

---

### Particle network implementation

Emit a `<canvas>` element via `ui.html()` within the hero container. Emit the JS via
`ui.add_head_html()` as an inline `<script>` block.

**Critical constraints:**
1. Wrap initialization in `document.addEventListener('DOMContentLoaded', ...)` — NiceGUI's
   incremental DOM render means the canvas may not exist when `<head>` scripts run.
2. The hero container **must** have an explicit pixel height (e.g., `min-height: 560px`)
   before the canvas reads `getBoundingClientRect()`. If the parent is unsized, the canvas
   will silently init at 0×0 and the animation loop will run invisibly.
3. Canvas opacity: 0.15–0.18 — text must remain fully legible.

JS behavior: ~25–30 nodes drifting slowly; edges pulse orange→pink→violet; no sudden
movements. Match the behavior in `UI_Design/ui_kits/app/ParticleNetwork.jsx`.

---

### CSS rules

- **Namespace every class with `rag-landing-`** (e.g., `rag-landing-hero`, `rag-landing-marquee`,
  `rag-landing-feature`, `rag-landing-module`). NiceGUI does not isolate CSS per page —
  styles persist in the browser session. Collisions with `.q-*` classes or the chat page's
  `.nicegui-markdown` rules will cause visual corruption on navigation.
- Inject all CSS via `ui.add_head_html()` at the top of `landing_page()`.
- Do not touch the `:root` block or any existing CSS variables — only extend.
- The gradient `--g-sunset` is NEVER a large background fill. Text clip, button background,
  progress bar, or border only.

---

### Routing change

In `index()` (the `/` route), change the unauthenticated redirect from:
```python
ui.navigate.to("/login")
```
to:
```python
ui.navigate.to("/landing")
```

This is the only change to `index()`. All other logic (auth check, profile fetch, session,
streaming, admin panel) is untouched.

---

### Logic constraint

This is a static marketing page. There are no async handlers, no API calls, no storage reads.
The only Python logic is two `ui.navigate.to()` calls: "Start for Free" → `/register`,
"Sign in" → `/login`.

---

### Files touched

- `src/app/ui.py` — new `@ui.page("/landing")` function; one-line redirect change in `index()`

---

### Testing — done when

- [ ] `/landing` renders in browser with all 8 sections visible
- [ ] Particle canvas is visible and animating in the hero background (verify canvas bounds in DevTools — must not be 0×0)
- [ ] Scrolling marquee loops seamlessly
- [ ] "Start for Free" and "Get Started" buttons navigate to `/register`
- [ ] "Sign in" link navigates to `/login`
- [ ] Visiting `/` while unauthenticated redirects to `/landing` (not `/login`)
- [ ] No CSS class collisions with chat or auth pages (verify by visiting all three pages in one browser session)
- [ ] Gradient never used as large background fill
