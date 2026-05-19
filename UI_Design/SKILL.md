---
name: rag-tutor-design
description: Use this skill to generate well-branded interfaces and assets for RAG Tutor, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping the AI-native "observatory meets mission control" aesthetic of the RAG Tutor adaptive learning product.
user-invocable: true
---

# RAG Tutor design skill

Read the `README.md` file within this skill first — it holds the full visual + content fundamentals, the gradient rule, the glow hierarchy, and the iconography rules. Then explore the other files as needed.

## Layout of this folder

| Path | What it gives you |
|---|---|
| `README.md` | Voice, tone, content fundamentals, visual foundations, iconography. **Read first.** |
| `colors_and_type.css` | All CSS variables: surfaces, gradients, glow shadows, radii, spacing, type scale, motion. Import this once in any HTML you produce. |
| `reference/design-spec.md` | The original design specification with full copy strings, screen breakdowns, and wow-factor concepts. |
| `assets/` | Logo PNGs (full lockup, square icon, wordmark). |
| `preview/` | Per-token preview cards — useful as reference, not for prod. |
| `ui_kits/app/` | Pixel-faithful React recreation of the three priority screens (landing, auth, chat). Lift components from here. |

## When invoked

If the user invokes this skill without other guidance, ask what they want to build, then act as an expert RAG Tutor designer. Default outputs:

- **Visual artifact (slide / mock / throwaway prototype):** copy the assets out, write a static HTML file that imports `colors_and_type.css`, and use the components in `ui_kits/app/` as your starting point. Hand it back as a single self-contained HTML.
- **Production code:** copy the relevant components and CSS variables, and translate them into the user's framework. The variable names in `colors_and_type.css` mirror the existing NiceGUI app's `:root` block — they are stable.

## Non-negotiables

- **The gradient is the brand.** `linear-gradient(135deg, #f97316, #ec4899, #8b5cf6)` only appears as text clip, 1px border, progress fill, or CTA background. Never as a large fill.
- **Glow hierarchy is hierarchy.** Pink 0.55 on the CTA. Pink 0.18 on focused inputs. Violet 0.12 on passive cards. Text never glows.
- **Inter for everything**, except numbers / scores / trace IDs / code → JetBrains Mono.
- **No emoji.** The only decorative glyph is `✦` on Knowledge Check labels.
- **Voice is expert peer**, not instructor. Short, declarative, no hedging, no exclamation points.

## Asking questions

If the user asks for something on a surface that doesn't exist yet (settings, billing, mobile sheet, etc.), ask what they want it to do before designing — the system has tokens for everything, but unfamiliar surfaces need a quick spec round first.
