# Commit 39 Spec — `scoring-correctness`
> **Project:** rag-from-scratch · **Assignee:** backend + ai-engineer (Rex + Nova) · **Load only for the active commit.**
> **Note:** Added in replan 2026-05-20 — scoring bugs discovered in Mira/Nova learning flow review.

---

### Commit 39 — `scoring-correctness`

**Commit message:** `fix: scoring correctness — question index modulo, passive delta path, session guard`

**Body:**
Three correctness bugs in the assessment scoring layer, all discovered during a
Mira/Nova learning flow audit. These are live issues affecting every user session.

**Bug 1 — `% 8` hardcoded in `_select_question_index` (Nova owns assess.py)**
`src/agents/nodes/assess.py`: `_select_question_index` computes `len(messages) % 8`
but every MCQ file has exactly 5 questions (MCQ-1 through MCQ-5). On turns 5, 6, and 7
the index is out of range — `_load_mcq_question` raises `ValueError`, `assessment_error`
is returned, and the question is silently suppressed. Fix: change `% 8` → `% 5`.
(Long-term the count should come from the loaded file dynamically, but `% 5` is the
correct immediate fix matching the current bank size.)

**Bug 2 — Passive deltas decay MCQ-earned scores (Rex owns scoring.py)**
`src/app/profile/scoring.py`: passive assessment deltas (capped at 0.3) enter
`compute_topic_scores` through the same path as full MCQ session scores. Because the
spaced-rep formula is `0.7 × session + 0.3 × best_prior`, a passive delta of 0.3 on a
topic where the user previously scored 1.0 produces: `0.7 × 0.3 + 0.3 × 1.0 = 0.51`.
A strong MCQ result is erased by casual conversation. Fix: add an `is_passive: bool`
parameter to `compute_topic_scores`. When `is_passive=True`, use additive clamped logic
(`min(existing_score + delta, 0.3)` on top of the existing score rather than replacing
the session score). Passive signals cannot exceed 0.3 total and cannot reduce an existing score.

**Bug 3 — Minimum session length not enforced (Rex owns scoring.py)**
`gates.md` specifies: sessions under 3 questions produce no score update. Currently
`compute_topic_scores` applies any delta regardless of question count — a single correct
MCQ can pass a Phase 1 gate (1 question → session_score=1.0 → topic_score=1.0).
Fix: add `session_question_count: int = 1` parameter to `compute_topic_scores`. When
`session_question_count < 3` and `is_passive=False`, log a warning and return the
current scores unchanged. Nova wires the actual session counter from AgentState in
Commit 41. For this commit, Rex adds the guard; the default of 1 means existing
callers that don't pass the count continue to behave as before until Commit 41 wires it.

**Assignee split:**
- Rex: `src/app/profile/scoring.py` — bugs 2 and 3
- Nova: `src/agents/nodes/assess.py` — bug 1

**Files touched:**
- `src/agents/nodes/assess.py` — fix `% 8` → `% 5` in `_select_question_index` (Nova)
- `src/app/profile/scoring.py` — add `is_passive` and `session_question_count` params to `compute_topic_scores` (Rex)

**Depends on:** 38.5 (all prior work complete)

**Testing — done when:**
- [ ] Turn 5+ in a conversation correctly cycles back to question 0 (no `assessment_error`)
- [ ] A passive delta of 0.3 on a topic scored 1.0 does NOT reduce the topic score
- [ ] Passive score for an unscored topic adds up to max 0.3, never triggers gate passage
- [ ] `compute_topic_scores` called with `session_question_count=1` returns unchanged scores with a logged warning
- [ ] Existing tests in test suite still pass (no regressions in scoring logic)
