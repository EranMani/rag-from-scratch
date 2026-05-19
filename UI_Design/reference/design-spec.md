# RAG Tutor — Design Specification

> This document is the single source of truth for the RAG Tutor visual redesign.
> It is written for Claude (or any design agent) to consume directly.
> Follow every section in order. Do not deviate from the color tokens, copy, or structural outline without a noted reason.

---

## 1. Visual Identity

### 1.1 Color Palette

The existing palette is already strong and must be **preserved and extended**, not replaced.
Every value below is a design token. Use these names throughout all CSS and component code.

| Token | Hex | Role |
|---|---|---|
| `--c-canvas` | `#120e28` | Page background — deepest void |
| `--c-frame` | `#0c0a1e` | Header, drawer, surfaces darker than canvas |
| `--c-sidebar` | `#16103a` | Sidebar, secondary panels |
| `--c-card` | `#1e163c` | Cards, modals, elevated surfaces |
| `--c-border` | `#241d4a` | Default borders, dividers |
| `--c-warm` | `#f97316` | Orange — energy, CTA accents, brand primary |
| `--c-coral` | `#ec4899` | Pink — emotion, focus states, glow anchor |
| `--c-violet` | `#8b5cf6` | Purple — AI, depth, sidebar accents |
| `--c-blue` | `#38bdf8` | Sky — data, highlights, code |
| `--c-muted` | `#94a3b8` | Secondary text, labels |
| `--c-subtle` | `#64748b` | Tertiary text, disabled |
| `--c-surface-alt` | `#231848` | Input bar background, footer zone |

**Gradient tokens** (use these by name in code):

```css
--g-sunset:  linear-gradient(135deg, #f97316 0%, #ec4899 50%, #8b5cf6 100%);
--g-horizon: linear-gradient(90deg,  #f97316 0%, #ec4899 40%, #8b5cf6 70%, #38bdf8 100%);
--g-deep:    linear-gradient(160deg, rgba(22,16,44,0.98) 0%, rgba(28,20,52,0.98) 100%);
--g-glow-bg: radial-gradient(ellipse at 8% 92%, rgba(249,115,22,0.07), transparent 38%),
             radial-gradient(ellipse at 92% 8%, rgba(139,92,246,0.07), transparent 38%);
```

**Semantic glow rules:**
- Orange glow (`rgba(249,115,22,0.15–0.35)`) → active actions, send buttons, CTA hover
- Pink glow (`rgba(236,72,153,0.12–0.55)`) → focus rings, input borders, AI response cards
- Violet glow (`rgba(139,92,246,0.12–0.25)`) → sidebar, passive cards, retrieved context

**New colors to add** (extend the palette without breaking the existing system):

| Token | Hex | Role |
|---|---|---|
| `--c-success` | `#4ade80` | Health checks, success states |
| `--c-warning` | `#fbbf24` | Degraded services, soft warnings |
| `--c-error` | `#f87171` | Errors, delete actions |
| `--c-neural` | `#a78bfa` | Knowledge check cards, AI-specific accents |

---

### 1.2 Typography

**Primary font:** `Inter` (Google Fonts, weights 400 / 500 / 600 / 700)
**Monospace font:** `ui-monospace, 'Cascadia Code', monospace` (for code, scores, trace IDs)

**Type scale:**

| Role | Size | Weight | Color |
|---|---|---|---|
| Brand wordmark | `1.35rem` | 700 | `--g-sunset` (gradient clip) |
| Page section heading | `2.5rem–3.5rem` | 700 | `--g-sunset` (gradient clip) |
| Card heading | `1.1rem` | 700 | `--g-sunset` (gradient clip) |
| Body / chat text | `0.9–1rem` | 400 | `#e2e8f0` |
| Secondary label | `0.82rem` | 500 | `--c-muted` |
| Tertiary / caption | `0.7–0.78rem` | 400–500 | `--c-subtle` |
| Monospace data | `0.85rem` | 400 | `--c-blue` or `#e879f9` |

**Letter-spacing rules:**
- All-caps labels: `letter-spacing: 0.06–0.08em`
- Brand name: `letter-spacing: -0.02em`
- Body: none

---

### 1.3 Overall Aesthetic / Vibe

**Keyword brief:** *AI-native observatory.* The UI should feel like a deep-space research terminal — authoritative, precise, and quietly alive. Every surface glows faintly. Data moves with purpose. Nothing is decorative without function.

**Key aesthetic principles:**

1. **Depth through layering.** Canvas → frame → card → content. Each layer is slightly lighter purple-black. Borders and glows define the edges rather than hard outlines.
2. **The gradient is the brand.** Orange → Pink → Violet is the identity. It appears on the logo, headings, progress bars, active states, and CTAs. Never use it as a background fill — only as a stroke, text clip, or accent.
3. **Glow is hierarchy.** Important interactive elements (send button, focused input, CTA) have a warm glow. Passive elements (cards, sidebar) have a cool violet glow. Never apply the same glow weight to everything.
4. **Motion is subtle.** Animations are slow, smooth, and meaningful — never flashy. The thinking dots cycle colors; gradients breathe; elements fade in. Nothing bounces or pops.
5. **Data is beautiful.** Progress bars, stat cards, and score displays should feel like mission control readouts. Monospace for numbers. Uppercase caps-lock for labels.

---

## 2. Brand & Audience Context

### 2.1 Core Mission

> RAG Tutor is an AI-powered learning system that teaches Retrieval-Augmented Generation — adapting in real time to each learner's current understanding, filling their gaps, and advancing their mastery from first principles to production patterns.

### 2.2 Product Positioning

**Category:** Adaptive AI education tool
**Differentiator:** Not a static course or a chatbot — a personalized tutor that tracks your knowledge graph and tailors every response to exactly where you are.
**Comparison frame:** "What if Perplexity was built specifically to teach you RAG, and it remembered everything you'd learned?"

**One-line pitch:**
> *The fastest way to go from "what is RAG?" to shipping RAG in production.*

### 2.3 Voice & Tone

| Dimension | Description |
|---|---|
| **Voice** | Expert peer, not instructor. Speaks like a senior engineer who genuinely enjoys explaining things. |
| **Tone** | Confident, warm, precise. Never condescending. Never over-caffeinated. |
| **Technical register** | High — assumes the reader can read code and knows what an embedding is. |
| **Personality** | A little ambitious. Believes deeply that understanding RAG properly matters. |

**Write like this:** "Here's why chunking strategy matters more than most people think — and what to do about it."
**Not like this:** "Great question! Let me explain what chunking is in simple terms!"

### 2.4 Target Audience Avatars

**Avatar 1 — The Hands-On Engineer**
- Senior software developer, 3–8 years exp, has used LLMs via API
- Frustrated by RAG pipelines that feel like black boxes
- Learns by doing — wants code examples, wants to understand the *why* behind each decision
- Goal: ship a production RAG system with confidence

**Avatar 2 — The ML Practitioner**
- Data scientist or ML engineer, comfortable with embeddings and vector math
- Already knows the theory, wants to close the gap between research and production
- Reads papers. Wants to know what actually works at scale
- Goal: understand retrieval methods deeply, evaluate and tune their own pipeline

**Avatar 3 — The Ambitious Non-Coder**
- Product manager, founder, or technical writer
- Building or overseeing an AI product and needs to understand RAG to make good decisions
- Intimidated by code but not by concepts
- Goal: understand RAG well enough to ask the right questions and evaluate vendor claims

---

## 3. Structure & Copy

This section outlines every screen and section the redesign should address.
Each subsection names the screen, lists all UI elements, and provides the exact copy to use.

---

### 3.1 Landing / Marketing Page (NEW — does not exist yet)

The app currently drops users directly into the chat or login. A landing page is needed to establish the brand before asking for sign-up.

**Layout:** Single scrolling page. Dark canvas. Sections stack vertically. Subtle parallax on scroll.

---

#### Section A — Hero

**Purpose:** Communicate the product's value proposition in under 5 seconds and drive sign-up.

**Elements:**

```
[NAVBAR]
  Logo (SVG icon + "RAG Tutor" gradient wordmark)         [left]
  Links: Features · How It Works · Docs                   [center, desktop only]
  CTA Button: "Start Learning Free →"                     [right]

[HERO CONTENT]
  Eyebrow label (small caps, muted):
    "AI-NATIVE LEARNING SYSTEM"

  H1 headline (large gradient text, ~3.2rem, two lines):
    "Master RAG.
     Ship with confidence."

  Subheadline (body, muted, max-width 480px):
    "RAG Tutor adapts to your level in real time — tracking your gaps,
     building on your strengths, and guiding you from fundamentals
     to production-grade systems."

  CTA Row:
    Primary button (sunset gradient): "Start for Free"
    Secondary link (ghost, muted): "See how it works ↓"

  Social proof line (tiny, muted, center):
    "No credit card required · Personalizes to your level instantly"

[HERO VISUAL]
  (see Section 4 for the animated background asset concept)
  Floating UI mockup card showing the chat interface — subtle glow, slight 3D tilt
```

---

#### Section B — The Problem

**Purpose:** Make the pain real before presenting the solution.

**Layout:** Two-column (left: headline + copy; right: stylized "before" vs "after" comparison)

```
Eyebrow: "THE PROBLEM"

H2: "RAG is everywhere.
     Understanding it deeply is rare."

Body copy (3 short paragraphs):
  "Most teams bolt together a LangChain tutorial and call it a RAG pipeline.
   Then they wonder why retrieval quality degrades, why hallucinations
   creep in at the edges, why their re-ranker makes things worse."

  "The real issues — chunking strategy, embedding model choice, index
   configuration, retrieval scoring, hybrid search, production caching —
   live in the space between the tutorial and the production system."

  "RAG Tutor closes that gap. Not with more documentation.
   With a tutor that knows exactly where you are and what you need next."
```

---

#### Section C — Features / How It Works

**Layout:** Three cards in a row (desktop), stacked (mobile). Each card has an icon, title, and 2-sentence description.

```
Section heading:
  "Built different."

Feature card 1 — Adaptive Learning Engine
  Icon: branching neural node (SVG, warm gradient)
  Title: "Knows what you know"
  Copy: "Every question you ask updates your knowledge profile.
         RAG Tutor adapts every response to your current mastery level —
         not a generic difficulty setting."

Feature card 2 — Production-Grade Curriculum
  Icon: stacked layers / pipeline (SVG, cool gradient)
  Title: "From zero to production"
  Copy: "Six modules cover every layer of the RAG stack — fundamentals,
         vector databases, retrieval methods, chunking, LangChain, and
         production patterns. In that order, for a reason."

Feature card 3 — Knowledge Checks Built In
  Icon: checkmark with circuit trace (SVG, violet)
  Title: "Learns from your answers"
  Copy: "After each response, RAG Tutor surfaces a knowledge check question.
         Your answers train its model of you — so the next response is
         sharper, more targeted, more useful."
```

---

#### Section D — Curriculum / Module Breakdown

**Layout:** Horizontal scrolling row of module cards (or vertical accordion on mobile)

```
Section heading:
  "Six modules. One coherent path."

Subheading (muted):
  "Designed to build on each other — not to be consumed in isolation."

Module cards (one per topic):
  01 · RAG Fundamentals       — "The architecture, the intuition, the why."
  02 · Vector Databases       — "FAISS, Pinecone, Weaviate — and when to use each."
  03 · Retrieval Methods      — "Semantic, keyword, hybrid, re-ranking."
  04 · Chunking Strategies    — "The decision that breaks more pipelines than any other."
  05 · LangChain              — "Chains, agents, and retrieval pipelines in code."
  06 · Production Patterns    — "Caching, eval, observability, latency tuning."
```

---

#### Section E — Social Proof / Testimonials (Placeholder)

```
Section heading: "What engineers say."

[3 testimonial cards — placeholder copy for now, replace with real quotes]

Card 1:
  Quote: "I've read the LangChain docs a dozen times.
          RAG Tutor was the first thing that made retrieval scoring click."
  Attribution: "— Senior Engineer, Series B startup"

Card 2:
  Quote: "The knowledge profile feature is genuinely impressive.
          It noticed I kept asking surface-level chunking questions
          and pushed me toward the underlying tradeoffs."
  Attribution: "— ML Engineer, enterprise team"

Card 3:
  Quote: "I'm not a developer but I needed to understand RAG to make
          decisions about our AI product. This is the first resource
          that didn't lose me."
  Attribution: "— Technical Product Manager"
```

---

#### Section F — CTA Footer

```
Large centered block, canvas background, gradient headline:

H2: "Start learning today."

Body: "Your first session is free. No setup. No configuration.
       Just ask your first question and watch the system adapt."

Button (large, sunset gradient, full glow):
  "Get Started →"

Micro-copy below button (muted, tiny):
  "Already have an account? Sign in →"
```

---

### 3.2 Login Page (Existing — Refine)

The existing login page is well-structured. The following copy and layout adjustments apply:

**Keep:** Card layout, gradient top border (orange `#f97316`), logo, input styling, existing button gradient.

**Update copy:**

```
Tagline (below logo): "Your AI-powered RAG learning assistant"   ← keep as-is
Sub-label:            "Sign in to continue your learning path"   ← change from "Sign in to your account"

Email field label:    "Email address"                            ← change from "Username or Email"
Password field label: "Password"                                 ← keep

Button:               "Continue →"                              ← change from "Login"
Register link:        "Don't have an account? Create one →"     ← change from "Create a new account"
```

---

### 3.3 Register Page (Existing — Refine)

**Keep:** Card layout, gradient top border (violet `#8b5cf6`), logo, input styling.

**Update copy:**

```
Sub-label:           "Create your account to start learning"    ← change from "Create your account"
Button:              "Create account →"                         ← keep, add arrow
Login link:          "Already learning? Sign in →"              ← change from "Already have an account? Sign in"

Success state heading: "You're all set."                        ← change from "You're signed in"
Success state body:    "Your profile is ready. Start with your first question →"
```

---

### 3.4 Chat Interface (Existing — Upgrade)

**Keep:** The overall layout (sidebar + chat + input bar) is correct. Upgrade specific zones.

#### Header bar

```
Logo + wordmark:     keep as-is
Tab labels:          "Chat" → "Learn" · "Admin" → "System"     ← rename tabs for cleaner tone
User pill:           keep email display
Logout button:       "Sign out"                                  ← change from "Log out"
```

#### Knowledge Profile Sidebar

```
Section heading:     "Your Profile"                             ← change from "Knowledge Profile"

Mastery chip labels:
  novice       → "Novice"        (slate, existing)
  intermediate → "Intermediate"  (warm orange, existing)
  advanced     → "Advanced"      (pink, existing)
  expert       → "Expert"        (violet, existing)

Below mastery chip, add a one-liner:
  novice:       "Just getting started — great time to build foundations."
  intermediate: "You've got the core. Time to go deeper."
  advanced:     "Strong foundations. Let's tackle production complexity."
  expert:       "You're in the top tier. Ask me anything."

Topic scores label: "Module Progress"                           ← change from "Topic Scores"

Bottom stats:
  "Queries: N"   → "N questions asked"
  "Last active"  → "Last session: [date]"
```

#### Chat message area

```
Welcome message card (existing logic is good — update the fallback copy):

  First visit (no profile):
    "Welcome. I'm your RAG learning assistant.
     Ask me anything — from 'what is RAG?' to advanced retrieval tuning.
     I'll adapt to your level as we go."

  Generic returning user:
    "Welcome back. Your profile has [N] sessions so far.
     What would you like to explore today?"

User bubble label:       show display_name if set, else email prefix before @
Assistant bubble label:  "RAG Tutor"                            ← change from "RAG Assistant"
```

#### Input bar

```
Placeholder text:    "Ask anything about RAG, embeddings, retrieval, LangChain..."
                      ← expand from current shorter placeholder

Send button:         keep icon, keep gradient — consider adding tooltip "Send (Enter)"
```

#### Knowledge Check card

```
Label:   "✦ Knowledge Check"  ← keep as-is
Style:   keep violet glow card — consider adding a subtle shimmer animation on appear
```

---

## 4. New Visual Assets & Wow-Factor Ideas

This section describes visual assets that do not exist yet and need to be created separately (via image/video AI tools or custom SVG/CSS) before they can be wired into the build.

---

### 4.1 Hero Background — Looping Particle Network Animation

**Concept:** An infinitely looping, slow-moving particle graph in the hero section. Nodes float gently. Edges pulse with color (orange → pink → violet) as if data is flowing through them. The overall effect is a living neural network / knowledge graph. It sits behind the hero text at low opacity (15–20%) to preserve text legibility.

**Implementation path:** CSS + Canvas API (no external library needed). ~80 lines of JavaScript.

**Video generation prompt** (for tools like Sora, Runway, or Pika — use as a looping background):
```
A slowly drifting network of glowing nodes and edges on a very dark indigo-black background (#120e28).
Nodes are small soft-glow spheres in deep orange (#f97316), warm pink (#ec4899), and violet (#8b5cf6).
Edges between nodes pulse with light, cycling orange to pink to violet in a slow wave.
The overall motion is calm and meditative — no sudden movements.
The density is moderate — 20 to 30 nodes visible at once.
Style: cinematic, dark sci-fi, clean, no text.
Aspect ratio: 16:9. Duration: 8 seconds, perfectly loopable.
```

**Image generation prompt** (for a static fallback or Open Graph thumbnail):
```
A dark deep-space neural network visualization. Nodes connected by glowing fiber-optic-style edges.
Color palette: dark indigo-black background, nodes glowing in orange, pink, and purple.
Photorealistic render style, cinematic lighting, high detail.
The composition feels like a knowledge graph or data architecture diagram made beautiful.
No text, no UI chrome. Just the network.
```

---

### 4.2 Feature Section Icons — Gradient SVG Set

Three icons for the Features section (Section C above). Each is a 48×48 SVG with the sunset gradient applied as a stroke.

**Icon 1 — Adaptive Learning / "Knows what you know"**
Concept: A brain outline with a branching circuit path growing from it.
```
SVG prompt: Minimal line-art brain icon with a small decision tree / branch diagram
growing from the right hemisphere. Stroke style, no fill. Viewbox 48x48.
Apply gradient stroke: orange (#f97316) at top-left to violet (#8b5cf6) at bottom-right.
```

**Icon 2 — Curriculum / "From zero to production"**
Concept: A vertical stack of three horizontal layers (like a pipeline diagram).
```
SVG prompt: Three stacked horizontal rounded-rectangle layers with small connecting
arrows between them. Minimal, geometric, clean. Stroke style.
Apply gradient stroke: orange at top, pink in middle, violet at bottom.
```

**Icon 3 — Knowledge Checks / "Learns from your answers"**
Concept: A checkmark formed from a circuit trace line.
```
SVG prompt: A large checkmark (✓) where the line is drawn as a PCB circuit trace —
with small right-angle bends, small dots at joints. Stroke style, no fill.
Apply gradient stroke: orange to violet, left to right.
```

---

### 4.3 Scrolling Marquee — Curriculum Topics

**Concept:** An endlessly looping horizontal marquee between the hero and problem sections. It scrolls slowly left, displaying the six module names separated by a glowing dot divider. Pure CSS, no JavaScript.

**Text content:**
```
RAG Fundamentals  ·  Vector Databases  ·  Retrieval Methods  ·  Chunking Strategies  ·  LangChain  ·  Production Patterns  ·  RAG Fundamentals  ·  (repeat)
```

**Styling:**
- Text: `0.75rem`, `font-weight: 600`, `letter-spacing: 0.1em`, `text-transform: uppercase`
- Color: `--c-muted` (`#94a3b8`)
- Dots: gradient color (`#ec4899`)
- Background: `rgba(12,10,30,0.6)`, `backdrop-filter: blur(4px)`
- Animation: CSS `@keyframes marquee` scrolling left, duration ~30s, linear, infinite

---

### 4.4 Chat Background — Subtle Radial Glow Atmospheres

**Current state:** The chat background already has radial gradient glows (orange bottom-left, violet top-right). This works well.

**Enhancement:** Add a third, very slow breathing animation to the radial gradients — expanding and contracting at ~0.03 opacity difference over 6 seconds. This makes the background feel alive without being distracting.

```css
@keyframes rag-breathe {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.7; }
}
.chat-glow-layer {
  animation: rag-breathe 6s ease-in-out infinite;
}
```

---

### 4.5 Mastery Level Badge — Animated Gradient Border (Expert tier only)

**Concept:** When a user reaches "Expert" mastery, their badge gets a slow rotating conic-gradient border — like a halo effect. Regular mastery levels keep the static badge.

```css
@keyframes rag-expert-halo {
  from { --angle: 0deg; }
  to   { --angle: 360deg; }
}
.rag-mastery-expert {
  background: conic-gradient(from var(--angle), #f97316, #ec4899, #8b5cf6, #f97316);
  animation: rag-expert-halo 4s linear infinite;
  /* mask inner content with nested element */
}
```

---

### 4.6 Loading / Thinking Indicator — Enhanced

**Current state:** Three dots cycling through orange/pink/violet. This is good.

**Enhancement:** Add a faint horizontal "scanning line" that sweeps left-to-right across the thinking area every 2s — like a radar sweep. SVG or CSS-only.

```
Prompt for image generator (if creating a Lottie-style asset):
A minimal dark-mode loading animation.
Three soft glowing dots in a row, cycling colors from orange to pink to purple.
Below them, a single horizontal line of light scans slowly from left to right, fading at both ends.
Background: transparent. Style: clean, tech, dark.
Loop: perfect. Duration: 2.5 seconds.
```

---

## 5. Implementation Notes for the Design Agent

1. **Do not change the NiceGUI Python code** unless a specific UI element cannot be achieved any other way. All visual changes should be CSS-first.

2. **Preserve all CSS custom property names** already in the codebase (e.g., `--c-canvas`, `--c-warm`). Extend the `:root` block — do not replace it.

3. **The gradient is sacred.** `linear-gradient(135deg, #f97316, #ec4899, #8b5cf6)` is the core brand expression. Never apply it as a large background fill. Only use it as: text clip, border image, progress bar fill, button background, or thin decorative stroke.

4. **Glow intensity hierarchy:**
   - Highest: send button, primary CTA (`box-shadow: 0 4px 28px rgba(236,72,153,0.55)`)
   - Medium: focused inputs, active tabs (`box-shadow: 0 0 0 3px rgba(236,72,153,0.18)`)
   - Low: passive cards, sidebar (`box-shadow: 0 4px 28px rgba(139,92,246,0.12)`)
   - None: body text, labels, icons in rest state

5. **The landing page** (Section 3.1) is a new HTML file or route — it does not touch the existing NiceGUI chat UI. Build it as a standalone `index.html` or a new NiceGUI `@ui.page("/landing")` route.

6. **Mobile:** The sidebar collapses to a bottom sheet or off-canvas drawer on screens < 768px. The hero section stacks vertically. The marquee always scrolls regardless of viewport.

7. **Fonts:** The `Inter` import is already in the codebase. Do not duplicate the font link. Ensure it is loaded before any styled content renders (`display=swap`).

8. **Accessibility:** All gradient text must have a plain-color fallback in the `color` property before the clip. Buttons must have visible focus rings. Input glow counts as a focus indicator only if `outline: none` is explicitly set.

---

*End of design specification. All sections are final unless noted as placeholder.*
