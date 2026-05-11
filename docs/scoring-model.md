# Scoring Model — RAG Curriculum Assessment
# Project: rag-from-scratch
# Authors: Mira (product), Lara (curriculum mechanics)
# Status: Canonical implementation contract — Commits 24 and 25
# Last updated: 2026-05-11 (Commit 23)

---

## Purpose and Scope

This document is the implementation contract for:
- **Nova** (Commit 24): assessment engine — question delivery, LLM evaluation, session scoring
- **Rex** (Commit 25): profile scoring — topic score storage, gate evaluation, `user_level` computation

All scoring mechanics derive from `knowledge-base/curriculum/gates.md`. That file is
authoritative for formulas and thresholds. This document answers the behavioral and
product questions that gates.md does not: when testing happens, how it appears to the
user, whether scores decay, and what `user_level` means at each point in the curriculum.

Do not interpret gate logic from any file other than `knowledge-base/curriculum/gates.md`.

---

## 1. Curriculum Structure

Eight topics across three phases. Topic slugs are defined in
`knowledge-base/curriculum/topic-slugs.json` (canonical, machine-readable).

| Phase | Topic slug | Phase gate minimum |
|-------|-----------|-------------------|
| Phase 1 | `embeddings_and_similarity` | 0.70 per-topic |
| Phase 1 | `rag_pipeline_architecture` | 0.70 per-topic |
| Phase 2 | `chunking_strategies` | 0.70 per-topic, 0.75 mean across Phase 2 |
| Phase 2 | `vector_databases` | 0.70 per-topic, 0.75 mean across Phase 2 |
| Phase 2 | `retrieval_methods` | 0.70 per-topic, 0.75 mean across Phase 2 |
| Phase 2 | `context_and_prompting` | 0.70 per-topic, 0.75 mean across Phase 2 |
| Phase 3 | `evaluation_and_metrics` | 0.75 per-topic |
| Phase 3 | `production_patterns` | 0.75 per-topic |

Phase 2 is the only phase with a mean floor. Individual per-topic minimums apply to
all three phases. See `gates.md` for exact gate logic pseudocode.

---

## 2. Score Mechanics (from gates.md — do not redefine)

### 2.1 Per-question scoring

| LLM evaluator verdict | Score assigned |
|----------------------|----------------|
| `correct` | 1.0 |
| `partial` | 0.5 |
| `incorrect` | 0.0 |

Valid verdicts are exactly `correct`, `partial`, `incorrect`. Any other value is treated
as `incorrect` and must be flagged. Nova enforces this at the evaluator output step.

### 2.2 Session score

```
session_score = mean(question_scores_in_session)
```

Minimum questions per session for a score update to occur: **3**. Sessions with fewer
than 3 questions leave the topic score unchanged. An incomplete session is discarded
entirely — it is not partially applied.

### 2.3 Topic score (spaced repetition weighting)

```
topic_score = 0.7 × current_session_score + 0.3 × best_prior_session_score
```

If no prior session exists for this topic:
```
topic_score = current_session_score
```

`best_prior_session_score` is the highest session score the user has achieved for that
topic across all prior sessions — not the most recent prior session score.

**Concrete example:** A user answers 4 questions: `correct`, `partial`, `partial`, `incorrect`.
```
question_scores = [1.0, 0.5, 0.5, 0.0]
session_score   = 0.5
```
If their best prior session score was 0.65:
```
topic_score = (0.7 × 0.5) + (0.3 × 0.65) = 0.35 + 0.195 = 0.545
```
This is below 0.70 — no gate advancement.

### 2.4 Null vs. 0.0

A topic with no completed sessions has score `null`, not `0.0`. Gate logic must
treat `null` as failing: `null >= threshold` evaluates to `false`. This distinction
is enforced in Rex's gate computation — a topic with score `0.0` means the user
attempted assessment and scored zero; `null` means they have not yet attempted it.

---

## 3. Phase Gate Thresholds (Q4)

Phase gate thresholds are exact. They are not soft targets.

**Phase 1 — Foundations:**
- Topics: `embeddings_and_similarity`, `rag_pipeline_architecture`
- Threshold: each topic score >= **0.70**
- Mean requirement: none

**Phase 2 — Core Components (dual gate):**
- Topics: `chunking_strategies`, `vector_databases`, `retrieval_methods`, `context_and_prompting`
- Per-topic floor: each score >= **0.70**
- Mean floor: mean of all four Phase 2 topic scores >= **0.75**
- Rationale: Phase 2 topics are deeply interdependent — a learner who scrapes 0.70 on
  three topics but spikes one may have uneven foundations that cause confusion in Phase 3.

**Phase 3 — Production:**
- Topics: `evaluation_and_metrics`, `production_patterns`
- Threshold: each topic score >= **0.75** (higher than Phase 1/2 individual floors)
- Rationale: Production knowledge is higher-stakes. A learner who passes at 0.70 may
  design a RAG system but fail to operate or improve one safely.

**Hard gate enforcement:** Phase N+1 topics are inaccessible until the Phase N gate passes.
`null` topic scores always fail gate checks. Topics with null scores must not be treated
as 0.0 in gate evaluation.

---

## 4. Partial Knowledge and Non-Binary Progress (Q5)

A user can hold any topic score between 0.0 and 1.0. A score of 0.60 is a valid,
persistent state — it means the user has demonstrated partial but not passing competency.

Partial knowledge is meaningful:
- It triggers assessment (see Section 5, Condition A)
- It informs remediation: topics scoring between 0.60 and the gate minimum receive
  targeted remediation on the question types the user missed, not a full restart
- It does not prevent the user from continuing to discuss that topic or related topics
  in content mode

The gate threshold is the advancement criterion, not the knowledge criterion. A user
at 0.60 knows something — the system works with them toward passing, not against them
for not having passed yet.

---

## 5. When Assessment Happens (Q1)

### 5.1 Trigger conditions

The agent switches from content delivery to assessment mode when **any** of these
conditions is met for the active topic:

**Condition A — Readiness score:** The user's topic score reaches **0.60 or above**.
Applies to topics that have been previously assessed. A score of 0.60 is above
chance-correct territory and signals meaningful engagement. It also sits below the
0.70 passing gate, so testing here is timely rather than premature.

**Condition B — Engagement without assessment:** The user has exchanged **5 or more
content turns** on a topic with no prior assessment session recorded (score is `null`).
This catches first-time learners who are ready by engagement depth even without a prior score.

**Condition C — Explicit user request:** The user says something clearly indicating
they want to be tested ("quiz me," "test me on this," "give me a practice question").
This always routes to an assessment question immediately, regardless of score or turn count.

Conditions A and B apply independently. Whichever fires first triggers assessment.
Condition C is always honored when detected.

### 5.2 Curriculum constraints on trigger

- The agent must never ask a test question on a Phase N+1 topic before the Phase N
  gate is passed. If `phase_1_passed = false`, assessment questions draw only from
  Phase 1 topics.
- Topics the user has not engaged with at all (no content turns, null score) are never
  proactively assessed. Assessment is offered only for the topic the user is currently studying.

### 5.3 Remediation re-assessment

After a gate failure, the agent delivers targeted remediation content and then re-triggers
assessment for the failing topic(s). Re-assessment follows the same trigger rules.
There is no cooldown period — the user initiates re-assessment by resuming conversation
on that topic.

---

## 6. How Assessment Appears to the User (Q2)

Assessment is **transparent** — the agent does not hide that it is testing the user.
The agent does not, however, expose numeric thresholds or score deltas mid-session.
Showing "you need 0.70 to pass" creates threshold gaming; hiding assessment entirely
erodes trust.

### 6.1 Announcement

Before the first assessment question in a session, the agent delivers a framing
message. The exact phrasing is Nova's responsibility, but it must:
- Name the topic being assessed
- Indicate the number of questions (minimum 3)
- Make clear the user is entering a test, not a content discussion

Example framing (Nova may adapt):
> "You've built a solid foundation on retrieval methods. Let's check your understanding
> with a few questions — I'll ask you 3 to 5, then we'll see where you stand."

This framing is required before the first question in every assessment session,
including re-assessment after remediation.

### 6.2 Deferral

The user may defer assessment once per topic per session. When the trigger fires and
the agent offers assessment, the user can signal they are not ready ("not yet,"
"can we continue talking through this first").

After one deferral: the next content reply from the user on that topic re-triggers
the assessment offer. The user cannot defer a second time in the same session.
If the user attempts a second deferral, the agent acknowledges it and delivers the
first assessment question anyway. Phrasing must not be punitive — e.g., "Let's go
ahead and get these questions in while the material is fresh."

**Deferral state is session-scoped.** A new conversation session resets deferral state
for all topics.

### 6.3 During assessment

- Questions are delivered one at a time.
- After the user responds, the agent delivers the next question — no scoring commentary
  between questions.
- After the final question (minimum 3), the agent summarizes: which questions were
  correct, partial, or incorrect, and whether the gate threshold for that topic is met.
  The agent does not expose the numeric score delta at this point.
- The profile UI panel reflects the updated score after the session completes.

The post-assessment summary is non-optional. The user must receive their result.

---

## 7. Score Decay Policy (Q6)

**There is no score decay.**

Topic scores do not decrease over time due to inactivity. Once a topic score is recorded,
it persists until the user completes a new valid assessment session for that topic.

Rationale:
- The 0.7/0.3 weighted formula already handles recency. A poor current session at 0.7
  weight will pull the topic score down even if the best prior session was strong.
  Decay is an output of new assessment, not a time-based penalty.
- Explicit decay would punish users who pause for personal reasons without reflecting
  any actual change in knowledge. A self-paced learning tool that silently degrades a
  user's standing while they are absent creates distrust and discourages return.
- This curriculum tests conceptual and applied understanding of RAG, not factual recall.
  Conceptual knowledge degrades more slowly than isolated fact memorization.

**Implementation contract:** Nova and Rex must implement no decay logic. Decay, if ever
added, requires a separate commit with its own spec.

---

## 8. `user_level` Mapping (Q7)

`user_level` is a string field on the user profile. Valid values:
`novice`, `beginner`, `intermediate`, `advanced`, `expert`.

The mapping is determined entirely by phase gate state — not by topic score average.
Score-average mapping conflates "scored high on few topics" with "scored adequately
across many topics," producing misleading `user_level` labels for the adaptive prompt system.

| `user_level` | Gate state |
|-------------|-----------|
| `novice` | All Phase 1 topic scores are `null` (no assessment attempted) |
| `beginner` | At least one Phase 1 topic has a non-null score, AND `phase_1_passed = false` |
| `intermediate` | `phase_1_passed = true` AND `phase_2_passed = false` |
| `advanced` | `phase_2_passed = true` AND `phase_3_passed = false` |
| `expert` | `phase_3_passed = true` |

### Implementation rules for Rex:

1. Evaluate in order from `expert` down to `novice`. Return the first match.
2. `novice` is the default when no assessment has been attempted. It is not a failed
   state — it is the entry state for every new user.
3. A user remains `beginner` for the entire duration of Phase 1 work, regardless of
   partial scores. They become `intermediate` only when the Phase 1 gate fully passes.
4. A user in remediation holds the same `user_level` as before the failed gate check.
   `user_level` does not retrograde. A user who was `intermediate` before a failed Phase 2
   attempt is still `intermediate` while in Phase 2 remediation.
5. `user_level` is recomputed by Rex after every valid assessment session. It is not
   cached between sessions.
6. Null topic scores are excluded from any intermediate computation — they are not
   treated as 0.0 when evaluating the `beginner` condition.

### `user_level` in the chat interface

The `user_level` value drives adaptive response depth. It must not appear as a raw
string in the UI. Any UI label derived from `user_level` must use a human-readable
equivalent (e.g., "Intermediate learner," not "intermediate").

---

## 9. Edge Cases — Required Handling

These cases must be handled explicitly. Silence here does not mean the case is
acceptable to ignore.

| Case | Required behavior |
|------|-------------------|
| Session ends with fewer than 3 questions | No score update. Topic score is unchanged. Incomplete sessions are discarded entirely — not partially applied. |
| LLM evaluator returns an invalid verdict | Treat as `incorrect`. Log the invalid verdict for review. Do not crash or skip the question. |
| `best_prior_session_score` comes from an invalid session | Invalid sessions produce no score record. If one somehow exists in storage, it must not be used — treat `best_prior_session_score` as null and fall back to `topic_score = current_session_score`. |
| Phase 2 individual thresholds pass but mean fails | User receives mixed remediation across all Phase 2 topics, weighted by distance from 0.75. The agent explains why the gate has not passed despite per-topic scores being above 0.70. |
| User defers assessment twice in the same session | The second deferral is not honored. The agent acknowledges it and delivers the first question anyway. Phrasing must not be punitive. |
| User's `user_level` would be `novice` but they have many content turns | `user_level` is determined by gate state only, not by content engagement. A user with 20 content turns but no completed assessment session is `novice`. Assessment is what changes the level. |

---

## 10. Known Discrepancies — Must Be Resolved in Commits 24/25

The current codebase does not yet implement the gates.md scoring model. These are
not bugs to preserve — they are the precise items Nova and Rex must replace.

1. **`VALID_MODULE_SLUGS` in `src/agents/state.py` is stale.** Contains `rag_fundamentals`
   and `langchain` — neither exists in the Commit 22 curriculum. The canonical slug list is
   in `knowledge-base/curriculum/topic-slugs.json`. Nova's Commit 24 must update
   `VALID_MODULE_SLUGS` and `TopicScoresDelta` from this file.

2. **`compute_topic_scores` uses additive deltas, not the session-score formula.**
   `src/app/profile/scoring.py` currently adds a float delta to the existing score and
   clamps to [0.0, 1.0]. The correct formula is `0.7 × session_score + 0.3 × best_prior_session_score`.
   Rex's Commit 25 must replace the accumulator model entirely.

3. **`get_mastery_level` uses score averages, not phase gate state.**
   The current implementation in `src/app/profile/scoring.py` derives the level from
   the mean of all topic scores. Rex's Commit 25 must rewrite this to the phase-position
   mapping defined in Section 8 above.

---

## 11. Machine-Readable Reference

```json
{
  "assessment_triggers": {
    "readiness_score_threshold": 0.60,
    "content_turns_without_assessment": 5,
    "explicit_user_request": true
  },
  "session_validity": {
    "min_questions": 3
  },
  "deferral": {
    "max_deferrals_per_topic_per_session": 1,
    "deferral_state_scope": "session"
  },
  "score_decay": {
    "enabled": false
  },
  "user_level_mapping": {
    "novice": "all Phase 1 topic scores null",
    "beginner": "at least one Phase 1 topic non-null AND phase_1_passed = false",
    "intermediate": "phase_1_passed = true AND phase_2_passed = false",
    "advanced": "phase_2_passed = true AND phase_3_passed = false",
    "expert": "phase_3_passed = true"
  },
  "user_level_evaluation_order": ["expert", "advanced", "intermediate", "beginner", "novice"],
  "gate_thresholds": "see knowledge-base/curriculum/gates.md"
}
```

---

## 12. Cross-References

| File | What it defines |
|------|----------------|
| `knowledge-base/curriculum/gates.md` | Per-question scores, session formula, topic score formula, gate thresholds — authoritative source |
| `knowledge-base/curriculum/topic-slugs.json` | Canonical 8-slug list — Rex uses this for `VALID_MODULE_SLUGS` |
| `knowledge-base/curriculum/questions/[slug].md` | Per-topic question banks with rubrics — Nova references these in the evaluator prompt |
| `docs/scoring-model.md` | This file — behavioral and product layer on top of gates.md |
