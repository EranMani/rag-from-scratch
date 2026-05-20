# Commit 38.5 — `knowledge-profile-ui`
# Assignee: Aria (frontend)
# Phase: UI Redesign (depends on Commit 38)
# Status: pending

---

## Goal

Replace the existing `profile_panel()` contents in `src/app/ui.py` with the
two-tab sidebar design from the updated UI kit (`UI_Design/app/KnowledgeProfile.jsx`).

The new sidebar has:
- A **mastery chip** at the top (above the tabs)
- A **tab bar** with "Current" and "Overview" tabs
- A **tab panel** that switches content based on the active tab
- A **footer stats block** at the bottom (questions asked + last session)

The mastery chip and footer are outside the tab panel — they always show.

---

## Reference Files

Read all three before writing any code:

| File | Purpose |
|---|---|
| `UI_Design/app/KnowledgeProfile.jsx` | Full two-tab component structure to implement |
| `UI_Design/app/kit.css` | CSS classes and token values used by this component |
| `UI_Design/reference/design-spec.md` | Color token definitions and design rules |

**Note:** The correct files are in `UI_Design/app/` — not in `UI_Design/ui_kits/app/`.
The `ui_kits/` version of `KnowledgeProfile.jsx` is the old single-list design.

---

## Files to Modify

| File | Action | What |
|---|---|---|
| `src/app/ui.py` | **update** | `profile_panel()` only — no other function |

No new files. No backend changes. No API changes.

---

## Data Transformation

The `/api/profile/me` response shape is unchanged:

```json
{
  "mastery_level": "intermediate",
  "topic_scores": {
    "embeddings_and_similarity": 0.82,
    "rag_pipeline_architecture": 0.75,
    "chunking_strategies": 0.44
  },
  "interaction_count": 47,
  "last_activity_at": "2026-05-20T10:30:00"
}
```

The new UI needs a `modules` list. Build it from the existing `_PHASE_TOPICS`
and `_MODULE_LABELS` dicts already defined in `ui.py`, using this structure:

```python
# Full curriculum — all three modules
_ALL_MODULES = [
    {
        "num": "M1",
        "name": "Foundation",
        "topics": ["embeddings_and_similarity", "rag_pipeline_architecture"],
    },
    {
        "num": "M2",
        "name": "Core RAG",
        "topics": ["chunking_strategies", "vector_databases", "retrieval_methods", "context_and_prompting"],
    },
    {
        "num": "M3",
        "name": "Advanced",
        "topics": ["evaluation_and_metrics", "production_patterns"],
    },
]

# Active module index by mastery level
_ACTIVE_MODULE_IDX = {
    "novice":       0,
    "beginner":     0,
    "intermediate": 1,
    "advanced":     2,
    "expert":       2,  # expert: all unlocked; show M3 as context
}
```

Build the `modules` list from these inside `profile_panel()`:

```python
active_idx = _ACTIVE_MODULE_IDX.get(mastery, 0)
modules = []
for i, m in enumerate(_ALL_MODULES):
    is_locked = i > active_idx
    topic_items = []
    for slug in m["topics"]:
        score = topic_scores.get(slug)
        done = score is not None and score >= 0.70
        topic_items.append({
            "slug": slug,
            "name": _MODULE_LABELS.get(slug, slug.replace("_", " ").title()),
            "done": done,
        })
    done_count = sum(1 for t in topic_items if t["done"])
    modules.append({
        "num": m["num"],
        "name": m["name"],
        "topics": topic_items,
        "done_count": done_count,
        "locked": is_locked,
    })
active_module = modules[active_idx]
```

A topic is **done** when `topic_scores.get(slug, 0) >= 0.70`.
Locked modules show no progress bar and grey-out their text.
Expert level: all modules unlocked, active_module is M3 but all shown as complete.

---

## Tab State Management

Use a mutable list as a closure variable — the standard NiceGUI pattern for
refreshable state. Define it in the same scope as `profile_panel`:

```python
_tab_state = ["Current"]  # ["Current"] or ["Overview"]
```

Inside `profile_panel()`, read `_tab_state[0]` for the active tab.
Tab buttons call:

```python
def _switch_tab(name: str) -> None:
    _tab_state[0] = name
    profile_panel.refresh()
```

Do not use `ui.state` or a class — the mutable list is the lightest correct pattern.

---

## CheckIcon Gradient — One-Time SVG Defs

Define the gradient once via `ui.add_head_html()` in the **parent page function**
(where the chat page layout is assembled), not inside `profile_panel()`.

The refreshable will be called multiple times — placing the SVG defs inside it
would inject duplicate `<defs>` blocks on every refresh.

```python
ui.add_head_html("""
<svg width="0" height="0" style="position:absolute;overflow:hidden">
  <defs>
    <linearGradient id="tg" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="#f97316"/>
      <stop offset="0.5" stop-color="#ec4899"/>
      <stop offset="1" stop-color="#8b5cf6"/>
    </linearGradient>
  </defs>
</svg>
""")
```

The CheckIcon SVG circle then references `fill="url(#tg)"` — no inline `<defs>`.

---

## Current Tab Layout

```
┌─────────────────────────────────┐
│  [Advanced]  ← mastery chip     │  ← always shown, above tabs
│  Strong foundations. Let's...   │
├─────────────────────────────────┤
│  Current  │  Overview           │  ← tab bar (underline indicator)
├─────────────────────────────────┤
│  Active module · M3             │  ← cur-eyebrow
│  Advanced                       │  ← cur-title
│                                 │
│  ████████░░░░░  1 / 2           │  ← progress bar + fraction
│                                 │
│  ✓  Evaluation & Metrics        │  ← done topic (gradient check)
│  ·  Production Patterns         │  ← pending topic (outline dot)
└─────────────────────────────────┘
```

- Progress bar shows `done_count / total` for the active module
- CheckIcon: inline SVG circle `fill="url(#tg)"` with white checkmark path
- PendingIcon: outline circle with center dot, uses `color: var(--c-subtle)`

---

## Overview Tab Layout

```
┌─────────────────────────────────┐
│  [Advanced]  ← mastery chip     │
│  Strong foundations. Let's...   │
├─────────────────────────────────┤
│  Current  │  Overview           │
├─────────────────────────────────┤
│  Overall progress               │
│  ████████████░░░  1 / 3 modules │
│                                 │
│  M1  Foundation         2/2     │  ← completed, full track
│  ████████████████████████       │
│                                 │
│  M2  Core RAG           3/4     │  ← in progress, partial track
│  █████████████░░░░░░░░░░        │
│                                 │
│  M3  Advanced           —       │  ← locked: dimmed, no track
└─────────────────────────────────┘
```

- Overall progress: `completed_modules / total_modules` where completed means
  all topics done and not locked
- Each row: num · name (left), fraction (right), track (below)
- Locked rows: dim all text (`opacity: 0.6`), no progress bar rendered
- Expert level: no rows locked; all rows show full tracks

---

## CSS Translation Rules

Translate all JSX class names to inline style strings using existing token values
from the `:root` block in `ui.py`. Do not add new CSS class names. Do not add new
custom properties. Use the token values already defined.

Key token mappings (from `UI_Design/app/kit.css`):

| CSS var | Value |
|---|---|
| `--c-fg` | `#f8fafc` |
| `--c-muted` | `#94a3b8` |
| `--c-subtle` | `#475569` |
| `--c-hairline` | `rgba(255,255,255,0.07)` |
| `--c-card` | `#1e1b4b` (approx) |
| `--f-sans` | `'Inter', system-ui, sans-serif` |
| `--f-mono` | `ui-monospace, 'Fira Code', monospace` |
| `--r-pill` | `999px` |
| `--t-base` | `160ms` |
| `--g-horizon` | `linear-gradient(90deg, #f97316, #ec4899, #8b5cf6)` |

Read `UI_Design/app/kit.css` for all `.sb-*`, `.cur-*`, `.ov-*`, and `.topic-*`
rule blocks to get exact dimensions, font sizes, and spacing values.

---

## Rules

1. **Only touch `profile_panel()`.** Do not modify any other function in `ui.py`.
2. **Do not change any API calls or data fetching logic.** The fetch from `/api/profile/me` and its error handling stay exactly as they are.
3. **Do not change the profile data structure.** Work with `topic_scores` and `mastery_level` as returned.
4. **Do not introduce new CSS custom property names.** Use existing token names only.
5. **Do not use `ui.html()` with any user-controlled string interpolation.** All user data (names, scores, counts) must go through typed NiceGUI components (`ui.label()`, etc.).
6. **Do not duplicate the SVG gradient defs.** Add once to page head; reference `url(#tg)` in each CheckIcon.
7. **The `_ALL_MODULES` and `_ACTIVE_MODULE_IDX` dicts may be added at module level** (same location as the existing `_PHASE_LABELS`, `_PHASE_TOPICS`, `_MODULE_LABELS` dicts) since they are static display config, not application state.

---

## Quality Gate Triage

| Reviewer | Decision | Reason |
|---|---|---|
| Viktor | **run** | New Python logic — data transformation (topic_scores → modules), tab state management, module index dicts. Viktor checks for type discipline and data correctness. |
| Sage | **run** | Renders user profile data (mastery level, topic names, scores). Verify no user data flows into `ui.html()` or raw HTML. Same check as C38. |
| Quinn | **skip** | UI-only commit — no test suite applicable to NiceGUI rendering |
| Mira | **run** | Explicitly requested by Team Lead. Core user-facing product behavior change. |
| Ryan | **run** | Full entry — new tab interaction pattern and data-to-display transformation introduced |

---

## Test Gate

No automated tests apply to NiceGUI UI rendering. Aria validates manually:

**Current tab:**
- Mastery chip shows correct level and tagline
- Active module name and number shown correctly
- Progress bar fills correct fraction
- Done topics show gradient checkmark icon
- Pending topics show outline dot icon

**Overview tab:**
- Overall progress bar reflects completed modules / total modules
- Each module row shows correct num, name, fraction
- Locked modules are visually dimmed and have no progress bar
- Expert level: all modules shown as unlocked

**Tab switching:**
- Clicking "Overview" shows Overview content, "Current" indicator moves
- Clicking back to "Current" restores Current content
- Profile refresh after chat turn preserves tab selection

**Regression check:**
- Mastery chip still appears above tabs
- Footer stats (questions asked, last session) still appear below tab panel
- No other function in ui.py is changed
