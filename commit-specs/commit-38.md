# Commit 38 — `progression-ui`
# Assignee: Aria (frontend)
# Phase: Progression System (depends on Commits 35 + 36 + 37)
# Status: pending

---

## Goal

Two UI additions in one commit:

1. **Onboarding wizard** — a modal overlay shown to first-time users on their first
   visit to the chat page. Walks through self-report → diagnostic MCQ → placement
   confirmation. Skippable.

2. **Phase progress panel** — a sidebar section showing the user's current phase,
   the topics in that phase, their scores, and what they need to advance.
   Replaces (or enhances) the existing profile topic_scores display.

---

## Context

**From Commit 36 (Nova) onboarding API:**
- `GET /api/onboarding/status` → `{"needed": bool}`
- `POST /api/onboarding/diagnostic` → `{"questions": [...], "slug": str}`
- `POST /api/onboarding/complete` → `{"confirmed_level": str, "correct_count": int, "message": str}`
- `skipped: true` in `/complete` sets level to novice

**From Commit 35 (Nova):** `is_mcq: bool` in SSE done event (used by Commit 37).
The onboarding diagnostic questions use the same MCQ button rendering from Commit 37.

**From Commit 34 (Nova):** Phase gate is based on `user_level`:
- novice/beginner → Phase 1 (embeddings, RAG pipeline architecture)
- intermediate → Phase 2 (chunking, vector DBs, retrieval methods, context & prompting)
- advanced → Phase 3 (evaluation & metrics, production patterns)
- expert → all phases complete

**Phase labels and topic labels** (Aria defines these for display):
```python
_PHASE_LABELS = {
    "novice":       ("Phase 1", "Foundation"),
    "beginner":     ("Phase 1", "Foundation"),
    "intermediate": ("Phase 2", "Core RAG"),
    "advanced":     ("Phase 3", "Advanced"),
    "expert":       ("Complete", "All phases"),
}

_PHASE_TOPICS = {
    "novice":       ["embeddings_and_similarity", "rag_pipeline_architecture"],
    "beginner":     ["embeddings_and_similarity", "rag_pipeline_architecture"],
    "intermediate": ["chunking_strategies", "vector_databases", "retrieval_methods", "context_and_prompting"],
    "advanced":     ["evaluation_and_metrics", "production_patterns"],
    "expert":       [],  # show full curriculum summary
}
```

**Mira's Flag 2 (resolved):** Users need to see why they're receiving phase-specific
questions. The progression panel is the answer — it shows the current phase and
explains the advancement gate.

---

## Files to Modify

| File | Action | What |
|---|---|---|
| `src/app/ui.py` | **update** | Onboarding modal logic; phase progress panel in sidebar |

No backend changes. No new files.

---

## Part 1: Onboarding Wizard

### Trigger

On page load of `/` (the main chat page), after auth check:

```python
if user_id:
    status = await http().get("/api/onboarding/status", headers=auth_headers())
    if status.json().get("needed"):
        show_onboarding_modal()
```

### Modal layout (3 steps)

**Step 1 — Self-report**
```
┌─────────────────────────────────────────────────┐
│  Welcome to RAG Tutor!                          │
│                                                 │
│  How familiar are you with RAG systems?         │
│                                                 │
│  [  Beginner — just starting out  ]             │
│  [  Intermediate — some experience ]            │
│  [  Expert — I've built RAG systems]            │
│                                                 │
│                              [ Skip for now ]   │
└─────────────────────────────────────────────────┘
```

**Step 2 — Diagnostic questions (3 MCQ)**
- Fetch questions from `/api/onboarding/diagnostic` with selected level
- Display each question using the same MCQ option button component from Commit 37
  (reuse the same button style and layout — do not duplicate the styling)
- "Next" button advances to the next question; final question triggers Step 3
- Skip button available throughout (calls `/complete` with `skipped: true`)

**Step 3 — Placement result**
```
┌─────────────────────────────────────────────────┐
│  ✓  You're placed at: Intermediate              │
│                                                 │
│  You got 2 out of 3 questions right.            │
│  [Backend message from confirmed_level response]│
│                                                 │
│  You'll start with Phase 2 topics:              │
│  · Chunking Strategies                          │
│  · Vector Databases                             │
│  · Retrieval Methods                            │
│  · Context & Prompting                          │
│                                                 │
│                              [ Start learning ] │
└─────────────────────────────────────────────────┘
```

On "Start learning": close modal, refresh profile data, render progression panel.

### Submission flow

Aria collects all 3 answers in a local list during Step 2, then calls:
```
POST /api/onboarding/complete
{"level": "intermediate", "answers": ["A", "C", "B"], "skipped": false}
```

### Skip flow

Any "Skip" click calls:
```
POST /api/onboarding/complete
{"level": "beginner", "answers": [], "skipped": true}
```
Then closes the modal.

---

## Part 2: Phase Progress Panel

### Location

Render in the right sidebar of the chat page (where the existing profile panel lives).
This replaces or extends the current topic_scores display.

### Layout

```
┌──────────────────────────────┐
│  Your Progress               │
│  ──────────────────────────  │
│  Phase 2 · Core RAG          │  ← current phase label
│                              │
│  Topics to complete:         │
│  · Chunking Strategies  0.42 │  ← topic score or "—" if unscored
│  · Vector Databases     0.68 │
│  · Retrieval Methods    —    │
│  · Context & Prompting  —    │
│                              │
│  Advance to Phase 3 when:    │
│  Each topic ≥ 0.70           │
│  Average ≥ 0.75              │
│                              │
│  ──────────────────────────  │
│  Mastery level: Intermediate │
└──────────────────────────────┘
```

### Score display rules

- Score is from profile `topic_scores` dict (loaded at page load + refreshed after each chat turn)
- Display as a 2-decimal float if scored (e.g., `0.68`)
- Display `—` if `None` (unscored)
- Color-code: ≥0.70 → green (`#22c55e`); 0.40–0.69 → amber (`#f59e0b`); <0.40 → red (`#ef4444`); unscored → muted (`#64748b`)

### Advancement message by phase

- Phase 1: "Each Phase 1 topic ≥ 0.70 to reach Phase 2"
- Phase 2: "Each Phase 2 topic ≥ 0.70 and average ≥ 0.75 to reach Phase 3"
- Phase 3: "Each Phase 3 topic ≥ 0.75 to become an expert"
- Expert: "All phases complete — keep sharpening your skills"

### Refresh trigger

After each chat turn completes (SSE done event fires), re-fetch the profile and update
the panel scores. This shows score progress in real time without a page reload.

---

## Quality Gate Triage

| Reviewer | Decision | Reason |
|---|---|---|
| Viktor | **skip** | UI-only commit — no logic paths, no backend routes |
| Sage | **run** | Profile scores and placement result are user data rendered in DOM — verify no XSS path; verify no user input passed into `ui.html()` |
| Quinn | **skip** | No test suite applicable to NiceGUI UI rendering |
| Mira | **run** | Onboarding flow and progression display are core user-facing product behavior — this is the commit Mira has been waiting for |
| Ryan | **run** | Always; full entry — new onboarding interaction pattern and progression display, architectural for user learning journey |

---

## Test Gate

No automated tests apply to NiceGUI UI rendering. Aria validates manually:

**Onboarding wizard:**
- Modal appears on first login (profile with no topic_scores)
- Modal does NOT appear on subsequent logins
- Self-report buttons render correctly for all 3 levels
- Diagnostic MCQ buttons appear and submit answers correctly (same component as Commit 37)
- Placement result shows correct level and topic list
- Skip closes modal and does not block chat access
- "Start learning" closes modal and progression panel appears

**Phase progress panel:**
- Panel shows correct phase name and topics for each user_level
- Scored topics show 2-decimal floats; unscored show `—`
- Color coding applied correctly at thresholds
- Advancement message matches current phase
- Panel updates after each chat turn without page reload

**Cross-browser check:**
- Test in Chrome and Firefox minimum
- Verify modal overlay covers full viewport without scroll issues
