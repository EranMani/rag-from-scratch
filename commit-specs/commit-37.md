# Commit 37 — `mcq-chat-ui`
# Assignee: Aria (frontend)
# Phase: Progression System (depends on Commit 35)
# Status: pending

---

## Goal

Update the chat UI to render MCQ questions as interactive option buttons (A/B/C/D)
instead of requiring free-text entry. When the backend signals an MCQ question is
pending (`is_mcq: true` in the SSE done event), the text input is replaced by four
option buttons. Clicking a button submits that letter as the user's answer.

---

## Context

**From Commit 35 (Nova):** The SSE `done` event now includes `"is_mcq": true|false`.
When `is_mcq: true`, the `test_question` field contains the full MCQ text:
```
Knowledge check: [Question text]

A. [Option A text]
B. [Option B text]
C. [Option C text]
D. [Option D text]
```

The user's answer must be submitted as a single letter: "A", "B", "C", or "D".

**NiceGUI constraint:** All user-visible text must use `ui.label()` or `ui.html()`
with static strings only — never f-strings with user-controlled data in `ui.html()`.
The option texts come from backend-served content; extract and display via `ui.label()`.

**Scope boundary:** This commit touches `src/app/ui.py` only — the chat section.
The progression phase panel and onboarding modal are Commit 38.

---

## Files to Modify

| File | Action | What |
|---|---|---|
| `src/app/ui.py` | **update** | MCQ state tracking, option button rendering, input toggle logic |

No backend changes. No new files.

---

## UI Behavior Specification

### State to track (per session, in `app.storage.user` or local variables)

```python
_mcq_pending: bool = False          # True when MCQ question is active
_mcq_options: list[str] = []        # ["Option A text", "Option B text", ...]
```

### When `done` event arrives with `is_mcq: true`

1. Set `_mcq_pending = True`
2. Parse the 4 option texts from `test_question`:
   - Split on newlines; find lines matching `^[A-D]\. `
   - Strip the letter prefix: `"A. foo"` → `"foo"`
   - Store in `_mcq_options` (order preserved: index 0=A, 1=B, 2=C, 3=D)
3. Hide the standard text input field
4. Show the MCQ option panel (see layout below)

### When `done` event arrives with `is_mcq: false`

1. Set `_mcq_pending = False`
2. Clear `_mcq_options`
3. Show the standard text input field
4. Hide the MCQ option panel

### MCQ option panel layout

Below the chat messages, replace the text input area with:

```
┌─────────────────────────────────────┐
│  A  [Option A text]                 │  ← button, full width
│  B  [Option B text]                 │  ← button, full width
│  C  [Option C text]                 │  ← button, full width
│  D  [Option D text]                 │  ← button, full width
└─────────────────────────────────────┘
```

Each button:
- Letter badge (pill, accent color) on the left
- Option text in `ui.label()` — never f-string interpolation
- Full-width, subtle border, hover highlight (match existing button style)
- On click: submit the letter ("A", "B", "C", or "D") as a chat message and hide the panel immediately

### Submission flow

```python
async def submit_mcq_option(letter: str):
    _mcq_pending = False
    # Hide MCQ panel, show text input
    await send_message(letter)   # reuse existing chat send function
```

The user sees their letter appear as a HumanMessage in the chat. The AI's next
response (evaluation result + next question or answer) streams back normally.

### Visual design notes

- Match the existing dark theme (background `#0c0a1e`, border `rgba(139,92,246,0.2)`)
- Letter badge: gradient pill matching the submit button (`#f97316 → #ec4899 → #8b5cf6`)
- Option text: `color: #e2e8f0`
- Hover state: border `rgba(236,72,153,0.4)` (matching the input hover style)
- No emoji. No icons beyond the letter badge.

---

## Quality Gate Triage

| Reviewer | Decision | Reason |
|---|---|---|
| Viktor | **skip** | UI-only commit — no logic paths, no backend routes changed |
| Sage | **run** | Option texts come from backend content rendered in the DOM — verify no XSS path |
| Quinn | **skip** | No test suite applicable to NiceGUI UI rendering |
| Mira | **run** | User-facing interaction model change — new input paradigm (buttons vs text) |
| Ryan | **run** | Always; one-liner entry (UI interaction enhancement, no architectural change) |

---

## Test Gate

No automated tests apply to NiceGUI UI rendering. Aria validates manually:

- MCQ option buttons appear when a knowledge check message arrives
- Standard text input is hidden while MCQ is pending
- Clicking "A" submits "A" as a chat message (verify in browser network tab)
- Standard text input reappears after submission
- Option texts are rendered with `ui.label()` — not injected via f-string into `ui.html()`
- All 4 buttons are visible without scrolling on a standard laptop viewport
- Dark theme and gradient letter badge match existing UI aesthetic

---

## Handoff Outputs

**→ Aria (Commit 38 `progression-ui`):**
- MCQ panel DOM structure established in this commit — Commit 38 may reference its
  surrounding layout context when positioning the progression sidebar
- `_mcq_pending` state pattern can be reused for onboarding modal visibility logic
