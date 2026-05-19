# RAG Tutor — Design System

> Single source of truth for the RAG Tutor visual language: an AI‑native, deep‑space "observatory meets mission control" aesthetic for an adaptive RAG learning product.

---

## What is RAG Tutor?

RAG Tutor is an AI‑powered adaptive learning system that teaches **Retrieval‑Augmented Generation**. Rather than a static course or a generic chatbot, it tracks a learner's knowledge graph and tailors every response to where they are — from "what is RAG?" all the way to shipping production‑grade retrieval pipelines.

**Category:** Adaptive AI education tool
**Differentiator:** Personalized tutor that updates a per‑user knowledge profile after every interaction
**Comparison frame:** "What if Perplexity was built specifically to teach you RAG, and it remembered everything you'd learned?"
**One‑line pitch:** *The fastest way to go from "what is RAG?" to shipping RAG in production.*

### Surfaces in scope

1. **Landing / marketing page** — net‑new. Hero + problem framing + features + curriculum marquee + CTA.
2. **Login / Register** — existing app cards, copy & glow refinements.
3. **Chat / Learn interface** — sidebar with live Knowledge Profile, chat area, input bar, knowledge‑check cards.

### Audiences

- **The Hands‑On Engineer** — senior dev, learns by doing, wants the *why* under each decision.
- **The ML Practitioner** — comfortable with embeddings, wants research‑to‑production patterns.
- **The Ambitious Non‑Coder** — PM/founder, intimidated by code but not concepts.

### Source materials

This system was built from a single internal source:

- `reference/design-spec.md` — the full design specification authored for this redesign (color tokens, type scale, copy strings, screen breakdowns, wow‑factor concepts). **Read this file for any ambiguity.**
- `assets/rag-tutor-logo-full.png` — the canonical product logo, supplied by the team.

No public Figma file, GitHub repo, or codebase was attached. The existing app is described in the spec as a **NiceGUI** (Python) implementation; the CSS tokens here mirror its `:root` variables so the system can drop in without breaking what ships.

---

## Index — what's in this folder

| Path | What |
|---|---|
| `README.md` | This file. Start here. |
| `SKILL.md` | Agent‑Skill entry point (drop into Claude Code as a skill). |
| `colors_and_type.css` | All CSS variables: surfaces, gradients, glow, radii, spacing, type scale, motion. Import this once. |
| `reference/design-spec.md` | Full source spec — copy strings, structure, wow‑factor concepts. |
| `assets/` | Logo, logomark, and any standalone visual assets. |
| `preview/` | Per‑token preview cards rendered to fill the Design System tab. |
| `ui_kits/app/` | High‑fidelity click‑thru UI kit for the RAG Tutor product (landing → login → chat). |

---

## Content fundamentals

Voice is **expert peer**, not instructor.

| Dimension | Notes |
|---|---|
| **Voice** | A senior engineer who genuinely enjoys explaining things. Confident, never condescending. |
| **Technical register** | High. Assumes the reader can read code and knows what an embedding is. |
| **Tone** | Confident, warm, precise. Not over‑caffeinated. No exclamation points in normal copy. |
| **Personality** | Slightly ambitious — believes understanding RAG *properly* matters. |
| **Pronouns** | Second person ("you"). First person singular ("I") is reserved for the tutor speaking — e.g. "I'll adapt to your level as we go." Never "we" for the tutor. |
| **Casing** | Sentence case for headings and buttons. UPPERCASE only for eyebrows, mono labels ("MODULE PROGRESS"), and tag pills. Letter‑spacing 0.06–0.12em on all caps. |
| **Length** | Short, declarative sentences. Em‑dashes for asides. Avoid hedging ("might", "perhaps"). |
| **Emoji** | **No.** The only glyph used decoratively is the four‑pointed sparkle `✦` on Knowledge Check labels. No emoji in body copy, buttons, or marketing. |
| **Numbers & code** | Always monospace. "0.85" not "85%". Trace IDs, scores, latencies, version numbers all live in `var(--f-mono)`. |

### Voice cheatsheet — write like this, not like that

| ✅ Write like this | ❌ Not like this |
|---|---|
| "Here's why chunking strategy matters more than most people think." | "Great question! Let me explain chunking in simple terms!" |
| "Master RAG. Ship with confidence." | "Learn RAG today and become an AI expert!" |
| "You've got the core. Time to go deeper." | "Awesome job leveling up!" |
| "Six modules. One coherent path." | "Six amazing modules you'll love!" |
| "Ask anything about RAG, embeddings, retrieval, LangChain…" | "How can I help you today?" |
| "Sign in to continue your learning path." | "Welcome back, please log in to your account." |

### Microcopy patterns

- **Section eyebrows**: `THE PROBLEM`, `HOW IT WORKS`, `AI‑NATIVE LEARNING SYSTEM` (uppercase, muted, sparse).
- **CTA shapes**: `Verb [object] →` — "Start for Free", "Continue →", "Create account →". Always trailing arrow on primary CTAs.
- **Mastery copy** is calibrated to register, never sycophantic:
  - novice → "Just getting started — great time to build foundations."
  - intermediate → "You've got the core. Time to go deeper."
  - advanced → "Strong foundations. Let's tackle production complexity."
  - expert → "You're in the top tier. Ask me anything."

---

## Visual foundations

### The single most important rule

**The gradient is the brand.** `linear-gradient(135deg, #f97316 0%, #ec4899 50%, #8b5cf6 100%)` appears on the wordmark, headings, progress bars, active borders, and CTAs — **never** as a large background fill. Only as: text clip, 1px border, progress fill, button background, or thin decorative stroke.

### Surface system

A four‑step ladder from deepest to most elevated. Layering — not hard borders — is what defines structure.

```
canvas  #120e28   page bg                  deepest void
frame   #0c0a1e   headers, drawers         darker than canvas
sidebar #16103a   sidebar, panels
card    #1e163c   cards, modals
alt     #231848   input bar, footer zone
```

Each step is ~5–10% lighter purple‑black than the one below it. Borders are `--c-border (#241d4a)` — present but quiet; they should read as *edges*, not lines.

### Color usage

| Surface | Glow color | Why |
|---|---|---|
| CTA buttons, send buttons | **Pink** `rgba(236,72,153,0.55)` warm bias | Highest hierarchy — "act here" |
| Focused inputs, active tabs | **Pink** `rgba(236,72,153,0.18)` ring | Medium hierarchy — "I am attending to this" |
| Passive cards, sidebar | **Violet** `rgba(139,92,246,0.12)` ambient | Low hierarchy — passive presence |
| Body text, icons at rest | **None** | Text never glows |

Orange `#f97316` is the energy stop, not a focus color — it appears at the start of the gradient and as an accent for the **login** card's top border. Violet `#8b5cf6` is the AI/depth stop and is used for the **register** card's top border.

### Typography

- **Sans:** Inter (400/500/600/700/800). Used for everything except numbers/code.
- **Mono:** JetBrains Mono fallback (`ui-monospace, 'Cascadia Code'`). Used for **all** data: scores, latencies, trace IDs, code snippets, version numbers.
- **Display headings**: gradient‑clipped, `-0.02em` tracking. *Never* gradient on body — only headings/wordmark.
- **Eyebrows / all‑caps labels**: `0.06–0.12em` tracking, muted color, used like signposts.

### Backgrounds

- **No imagery in the chrome.** Surfaces are flat dark with two faint radial glows (orange at 8/92, violet at 92/8). See `--g-glow-bg`.
- **No hand‑drawn illustrations.** Brand visuals are limited to the supplied logo, the brand gradient, and procedural canvas/SVG (particle network, scanning lines).
- **No repeating patterns or textures.** Surfaces are flat; depth comes from layering and glow.
- **Full‑bleed imagery** does not exist on this product. The closest analogue is the procedural **particle network** in the hero, sitting at ~15% opacity behind H1.

### Motion

- **Easing:** `cubic-bezier(0.16, 1, 0.3, 1)` (slow‑out) is the default. `cubic-bezier(0.4,0,0.2,1)` for shorter UI transitions.
- **Durations:** 120ms (hover), 220ms (UI state), 420ms (layout), 6s (breathing glows).
- **Vocabulary:** fades and gentle opacity breathing. **No bounces, no pops, no spring overshoots.** Loading dots cycle hues; the hero background drifts; radial glows breathe.
- **Hover:** lift glow opacity by ~30%, never scale.
- **Press:** drop glow opacity by ~30%, no shrink.

### Borders & shadows

- **Default border:** 1px `--c-border` (#241d4a).
- **Gradient border:** the brand 1px stroke. Built with a masked pseudo‑element (`::before { padding: 1px; background: var(--g-horizon); mask-composite: exclude }`). Used on login/register cards (top edge), CTA outlines, and the expert‑mastery halo.
- **Inner shadows:** sidebar gets `inset 0 0 60px rgba(139,92,246,0.04)` — a subtle violet inner glow. Inputs get a `inset 0 1px 0 rgba(255,255,255,0.02)` to feel pressed.
- **Outer shadows:** see glow hierarchy above. No "neutral" drop shadow exists — every shadow is colored.

### Cards

```
border-radius: 16px
background:    linear-gradient(160deg, rgba(30,22,60,0.92) 0%, rgba(22,16,58,0.92) 100%)
border:        1px solid #241d4a
box-shadow:    0 4px 28px rgba(139, 92, 246, 0.12)     (violet ambient)
padding:       24px
```

On hover, lift the violet glow to `0.22`. No transform.

### Corner radii

| Token | Value | Used for |
|---|---|---|
| `--r-xs` | 4px | Tag chips, inline mono pills |
| `--r-sm` | 8px | Inputs, small buttons |
| `--r-md` | 12px | Tabs, mid buttons, knowledge‑check chips |
| `--r-lg` | 16px | Cards, modals |
| `--r-xl` | 24px | Hero feature panels, full‑bleed sections |
| `--r-pill` | 999px | Mastery chips, primary CTAs, progress bars |

### Transparency & blur

- **Use blur sparingly.** Two places only: the curriculum **marquee** (`backdrop-filter: blur(4px)`), and any **modal scrim** (`backdrop-filter: blur(8px)`).
- **Translucent surfaces** are reserved for elements that float over the procedural hero background — everything inside the app shell is opaque.

### Layout rules

- **Sidebar:** 280–320px fixed on desktop, off‑canvas drawer below 768px.
- **Chat column:** max‑width 760px, centered within remaining space.
- **Landing sections:** 1240px max‑width container, 80–120px vertical rhythm between sections.
- **Header:** fixed, 64px tall, frame surface, 1px bottom border.
- **Input bar:** fixed bottom of chat column, alt surface, 12px radius, pink focus ring.

### Imagery color vibe

The product has **no photography**. Visuals are: gradient, glow, line‑art SVG, and the procedural network animation. Tone is cool indigo with warm sunset accents — never grain, never warm filters, never b&w.

---

## Iconography

The supplied design source did not include a bespoke icon set, so the system uses **Lucide** (`https://unpkg.com/lucide@latest`) as its working icon library. Lucide's 1.6px stroke weight and 24×24 grid match the product's quiet, mission‑control feel. **Flagged substitution** — if RAG Tutor has an internal icon set, swap Lucide for it; nothing else in the system depends on a specific library.

### Rules

- **One stroke weight: 1.6px.** Never mix weights on the same screen.
- **Default color: `--c-muted`** (`#94a3b8`). Icons read as text, not as features.
- **Tinted variants** are reserved and meaningful:
  - **Warm `#f97316`** — the **send** button only.
  - **Pink `#ec4899`** — primary actions and search affordances.
  - **Violet `#a78bfa`** — AI / knowledge / retrieval (the "neural" lane).
  - **Sky `#38bdf8`** — code, data, traces.
- **Sizing: 16 / 20 / 24 / 32 / 44px.** 44px is the send button (largest single‑icon hit target).
- **No fills.** All icons are stroke‑only. The robot logomark is the single exception.
- **No emoji** anywhere. The four‑pointed sparkle `✦` appears as a text glyph on the **Knowledge Check** label and nowhere else.
- **No unicode chars as UI icons** beyond `→`, `↓`, `·`, `✦`.

### The logo

The robot logomark + wordmark live in `assets/` as PNGs supplied by the team:

- `assets/rag-tutor-logo-full.png` — full marketing lockup (1659×948).
- `assets/rag-tutor-icon.png` — square robot mark, suitable for favicons and app icons.
- `assets/rag-tutor-wordmark.png` — gradient wordmark with tagline.

A simplified gradient `R` mark is acceptable as a fallback in tight UI (header chrome at <32px) — see the `<BrandMark>` JSX in the app UI kit.

### Asset caveats

- Provided logo is **raster only** (1659×948 PNG). For crisp scaling above 256px, request an SVG or 2x retina export from the team.
- No favicon was provided. The app UI kit ships a placeholder generated from `rag-tutor-icon.png`.

---

## SKILL & agent use

Drop `SKILL.md` into a Claude Code project under `.claude/skills/rag-tutor-design/` (or wherever you keep skills). The skill instructs the agent to consult this README first, then explore `colors_and_type.css`, the preview cards, and the UI kit before producing artifacts.

---

## File index

Root of this design system:

```
README.md                  ← you are here
SKILL.md                   ← Agent-Skill front-matter; drop into Claude Code
colors_and_type.css        ← Single source of truth for tokens. Import this.

reference/
  design-spec.md           ← Original product spec (copy, screens, wow concepts)

assets/
  rag-tutor-logo-full.png  ← Full marketing lockup (1659×948)
  rag-tutor-icon.png       ← Square robot mark
  rag-tutor-wordmark.png   ← Gradient wordmark + tagline

preview/
  brand-logo.html              Brand · canonical lockup card
  brand-icons.html             Brand · Lucide-style icon set
  colors-brand-gradient.html   Colors · 4-stop sunset / horizon
  colors-surfaces.html         Colors · 5-step surface ladder
  colors-text.html             Colors · text scale
  colors-semantic.html         Colors · success / warning / error / neural
  colors-glow.html             Colors · glow hierarchy (CTA / focus / passive)
  type-display.html            Type · hero H1 specimen
  type-scale.html              Type · h1 → label scale
  type-mono.html               Type · mono data, inline tokens, code
  type-eyebrows.html           Type · eyebrows & all-caps labels
  spacing-scale.html           Spacing · 4-pt ladder
  spacing-radii.html           Spacing · corner radii
  spacing-shadows.html         Spacing · colored shadow / elevation
  components-buttons.html      Components · primary / secondary / ghost / send
  components-inputs.html       Components · rest / focus / error
  components-mastery-chips.html Components · 4 mastery tiers (Expert halo)
  components-progress.html     Components · gradient progress bars
  components-chat-bubbles.html Components · user + assistant bubbles
  components-knowledge-check.html Components · violet ambient quiz card
  components-cards.html        Components · card variants
  components-marquee.html      Components · scrolling curriculum strip
  components-thinking.html     Components · 3-dot loading + scan line
  components-tabs.html         Components · pill tabs + underline nav
  components-module-cards.html Components · numbered curriculum cards

ui_kits/
  app/                     RAG Tutor product UI kit (landing → auth → chat)
    README.md
    index.html             Boot file with prototype nav strip
    kit.css                Component-level CSS
    App.jsx                Root prototype shell (hash routing)
    Brand.jsx              Logo + icon set
    Landing.jsx            Marketing page
    ParticleNetwork.jsx    Hero particle canvas
    Auth.jsx               Login + register cards
    ChatShell.jsx          Header + sidebar + chat column
    KnowledgeProfile.jsx   Sidebar mastery + progress
    KnowledgeCheck.jsx     Violet quiz card
    Composer.jsx           Input bar + high-glow send
    Bubbles.jsx            User / assistant / thinking
```

---

## Caveats

- **Logo is raster only.** Vector exports were not supplied. The square mark scales acceptably to 256px; below 32px the system uses a procedural gradient `R` (see `<BrandMark>` in `ui_kits/app/Brand.jsx`).
- **No codebase or Figma access** was provided alongside this spec. Token names mirror the existing NiceGUI app's `:root` block as described in the spec; if the actual code uses different names, swap at the variable definition.
- **Icon library is Lucide** (CDN reference). If the product has an internal icon set, replace the `<Icon>` paths in `Brand.jsx`.
- **JetBrains Mono substitution** — the spec asks for `ui-monospace, 'Cascadia Code'`. JetBrains Mono is the closest open-source pairing on Google Fonts and what loads from `colors_and_type.css`; system mono is the fallback chain. Flag for the team if a specific monospace is preferred.
- **Inter is loaded from Google Fonts** at weights 400/500/600/700/800. No bundled `.woff2` files yet — if offline use is a concern, request self-hosted exports.



