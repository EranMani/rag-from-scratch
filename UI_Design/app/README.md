# RAG Tutor — App UI Kit

High‑fidelity, click‑through recreation of the three priority surfaces:

1. **Landing** — hero with particle network, curriculum marquee, three feature cards
2. **Auth** — login (orange top bar) and register (violet top bar) cards
3. **Chat** — header, Knowledge Profile sidebar, chat column, knowledge‑check card, input bar with high‑glow send

## Files

| File | Purpose |
|---|---|
| `index.html` | Entry point — boots React, mounts `<App />`, renders the three‑screen prototype. |
| `App.jsx` | Root prototype shell — routes between landing → auth → chat, fakes auth state. |
| `Brand.jsx` | `BrandMark`, `Wordmark`, `Sparkle`, `Icon` (Lucide-style line icons). |
| `Landing.jsx` | Hero, problem section, features, module marquee, CTA footer. |
| `ParticleNetwork.jsx` | Canvas-based particle graph for the hero background. |
| `Auth.jsx` | `LoginCard` + `RegisterCard`. Orange top border for login, violet for register. |
| `ChatShell.jsx` | The chat screen: header, sidebar, message stream, input bar. |
| `KnowledgeProfile.jsx` | Sidebar: mastery chip + tagline + module progress + stats. |
| `Composer.jsx` | The bottom input bar with send button (highest glow). |
| `KnowledgeCheck.jsx` | Violet ambient quiz card surfaced after replies. |
| `Bubbles.jsx` | `UserBubble`, `AssistantBubble`, `ThinkingBubble`. |

## Click-through flow

`Landing → Sign in (auth toggle) → Chat → ask a question → receive reply with knowledge check`.

All state is local React. No backend. No persistence — refresh resets the flow.

## Visual fidelity

All values pulled from `../../colors_and_type.css`. Surfaces, glow, gradient, and motion are kept on token. The chat shell mirrors the existing NiceGUI app described in `reference/design-spec.md` §3.4; the landing page (§3.1) is the new piece.
