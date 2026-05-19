# Commit 36 — `onboarding-level-check`
# Assignee: Nova (ai-engineer)
# Phase: Progression System · Wave E (parallel with Commit 35; depends on Commit 34)
# Status: pending

---

## Goal

Add a new onboarding API that places fresh users into the correct curriculum phase
before their first chat. The flow:

1. **Status check** — backend tells the UI whether onboarding is needed for this user
2. **Self-report** — user declares their RAG knowledge level (beginner / intermediate / expert)
3. **Diagnostic questions** — 2–3 MCQ questions calibrated to the self-report level
4. **Placement** — binary scoring determines the confirmed level; profile is written
5. **Skippable** — user can skip onboarding; they start at `novice` by default

Onboarding only runs once (first login). If the user has any topic_scores, onboarding
is not needed and the status endpoint returns `{"needed": false}`.

---

## Context

**From Mira Session 06 (2026-05-19):** "Level-check: agree with self-report + 3-question
diagnostic hybrid."

**From Lara Commit 33 handoff:** `embeddings_and_similarity` and `rag_pipeline_architecture`
MCQ files can source onboarding diagnostics (3 questions each, mixed difficulty).
Onboarding questions are read-only references — do not modify MCQ banks for onboarding.

**From replan (2026-05-19):** "onboarding is self-report + 2–3 diagnostic questions,
skippable." Onboarding is triggered from the UI on first login (Aria handles the UI in
Commit 38). This commit adds the backend API only.

**Diagnostic question selection by self-report level:**
- beginner self-report → 3 questions from `embeddings_and_similarity` (Phase 1, mixed difficulty)
- intermediate self-report → 3 questions from `chunking_strategies` (Phase 2, mixed difficulty)
- expert self-report → 3 questions from `evaluation_and_metrics` (Phase 3, mixed difficulty)

**Placement scoring:**
| Correct answers | Confirmed level |
|---|---|
| 3/3 | Confirmed at self-report level |
| 2/3 | Confirmed at self-report level |
| 1/3 | Drop one level from self-report (min: novice) |
| 0/3 | Drop two levels from self-report (min: novice) |

Level drop mapping: expert → advanced → intermediate → beginner → novice

---

## Files to Modify / Create

| File | Action | What |
|---|---|---|
| `src/app/api/routes/onboarding.py` | **new** | Onboarding endpoints (status, diagnostic, complete) |
| `src/app/main.py` | **update** | Register the onboarding router |

No AgentState changes. No new DB columns (existing `mastery_level` and `topic_scores` are sufficient).

---

## API Design

### `GET /api/onboarding/status`

Auth required (JWT).

**Response:**
```json
{"needed": true}
```
or
```json
{"needed": false}
```

Logic: `needed = True` when the user's profile has no topic_scores (all null or empty dict)
AND `mastery_level == "novice"` (the default — has never been set by onboarding).

```python
profile = get_or_create_profile(user_id)
topic_scores = profile.get("topic_scores") or {}
needed = not any(v is not None for v in topic_scores.values())
```

---

### `POST /api/onboarding/diagnostic`

Auth required (JWT).

**Request body:**
```json
{"level": "beginner" | "intermediate" | "expert"}
```

**Response:**
```json
{
  "questions": [
    {
      "index": 0,
      "text": "Knowledge check: [question text]\n\nA. ...\nB. ...\nC. ...\nD. ..."
    },
    {"index": 1, "text": "..."},
    {"index": 2, "text": "..."}
  ],
  "slug": "embeddings_and_similarity"
}
```

Logic:
- Map `level` to a diagnostic slug (see context section above)
- Call `_load_mcq_question(slug, index)` for indices 0, 1, 2 (first 3 questions)
- Return question text only — do NOT return the correct answer
- The correct answers are stored server-side and used in `/complete`

**Server-side answer storage:** Store the 3 correct answers in the user's session.
Use `app.storage.user` (NiceGUI session storage) if called from UI context, OR
store temporarily in a short-lived in-memory dict keyed by `user_id + diagnostic_slug`.
Simplest safe approach: re-read the MCQ files in `/complete` to verify answers —
no server-side caching needed (files are static).

---

### `POST /api/onboarding/complete`

Auth required (JWT).

**Request body:**
```json
{
  "level": "beginner" | "intermediate" | "expert",
  "answers": ["A", "C", "B"],
  "skipped": false
}
```

If `skipped: true`, set `mastery_level = "novice"` and return immediately.

**Response:**
```json
{
  "confirmed_level": "intermediate",
  "correct_count": 2,
  "message": "Great start! You're placed at intermediate level."
}
```

Logic:
1. If `skipped`, write `mastery_level = "novice"` via `update_profile()`, return
2. Map `level` to diagnostic slug (same mapping as `/diagnostic`)
3. Re-read correct answers: call `_load_mcq_question(slug, index)` for indices 0–2,
   extract `correct_answer` from each
4. Score: count matches between `answers[i]` and `correct_answer[i]` (case-insensitive)
5. Apply placement scoring table (see context section) to get `confirmed_level`
6. Write `mastery_level = confirmed_level` via `asyncio.to_thread(update_profile, user_id, mastery_level=confirmed_level)`
7. Return `confirmed_level`, `correct_count`, and a user-facing message

**Import note:** `_load_mcq_question` is defined in `src/agents/nodes/assess.py`.
To avoid circular imports, Nova should extract the MCQ parsing logic into a shared
utility module (e.g., `src/agents/mcq_utils.py`) that both `assess.py` and
`onboarding.py` import from. This is a scope decision Nova must make upfront.

---

## Cross-Domain Notes

- `update_profile` and `get_or_create_profile` are Rex's functions in `profile/db.py`
  — used here read-only (status) and for write (complete). This is a declared
  cross-domain touch, not a violation.
- `main.py` registration is a one-line router include — not a logic change.
- The MCQ parsing logic extraction to `mcq_utils.py` (if Nova chooses this path)
  is a new shared utility — flag as handoff to Aria if she needs to import it.

---

## Quality Gate Triage

| Reviewer | Decision | Reason |
|---|---|---|
| Viktor | **run** | New routes, answer-scoring logic, cross-module import decisions |
| Sage | **run** | New auth-gated routes with user input (answers array); validate input bounds |
| Quinn | **skip** | Wave ran at Commit 35; next wave at Commit 40 |
| Mira | **skip** | Backend-only this commit; UI is Commit 38 |
| Ryan | **run** | Always; full entry — new route pattern, scoring logic, cross-domain import decision |

---

## Test Gate

Existing test suite must pass. Nova must add tests covering:

**`/api/onboarding/status`:**
- Fresh user (no topic_scores) → `{"needed": true}`
- User with any scored topic → `{"needed": false}`
- Unauthenticated → 401

**`/api/onboarding/diagnostic`:**
- Returns 3 questions for each valid self-report level
- Each question text contains "Knowledge check:" and A–D options
- Invalid level value → 422
- Unauthenticated → 401

**`/api/onboarding/complete`:**
- 3/3 correct → confirmed at self-report level
- 1/3 correct → one level below self-report
- 0/3 correct → two levels below self-report
- `"beginner"` + 0/3 → `"novice"` (floor enforcement)
- `skipped: true` → `confirmed_level = "novice"`, profile written
- Unauthenticated → 401

---

## Handoff Outputs

**→ Aria (Commit 38 `progression-ui`):**
- `GET /api/onboarding/status` returns `{"needed": bool}`
- `POST /api/onboarding/diagnostic` accepts `{"level": str}`, returns `{"questions": [...], "slug": str}`
- `POST /api/onboarding/complete` accepts `{"level": str, "answers": list[str], "skipped": bool}`
- Response includes `confirmed_level` (string) and `correct_count` (int) for UI display
- If Nova created `mcq_utils.py`, document its import path here
