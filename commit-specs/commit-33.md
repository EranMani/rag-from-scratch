# Commit 33 — `question-bank-mcq`
# Assignee: Lara (curriculum-specialist)
# Phase: Progression System · Wave D (parallel with Commit 34)
# Status: pending

---

## Goal

Add multiple-choice question (MCQ) banks to all 8 topic areas in the RAG curriculum.
MCQ questions are the gated format for phase advancement tests — used exclusively until
an open-ended response scorer is validated. This commit is knowledge-base only: no source
code is touched.

---

## Context

The existing question banks (`knowledge-base/curriculum/questions/[slug].md`) contain
open-ended questions with rubric-based grading for LLM evaluation. MCQ questions serve
a different purpose: phase gate advancement tests, where binary scoring (correct/incorrect)
is sufficient and reliable. The open-ended questions remain for in-session learning; MCQ
questions are gated assessment instruments.

**Why MCQ for advancement gates:**
- Binary scoring (no LLM evaluator needed — answer key comparison is deterministic)
- Faster to evaluate at scale
- Lower false-negative risk than open-ended rubric evaluation during progression checkpoints
- Will be replaced/supplemented by open-ended assessments once the scorer is validated

---

## Files to Create or Modify

| File | Action | What |
|---|---|---|
| `knowledge-base/curriculum/mcq-format.md` | **new** | MCQ question schema, scoring rules, and field definitions |
| `knowledge-base/curriculum/questions/mcq/rag_pipeline_architecture.md` | **new** | 5 MCQ questions |
| `knowledge-base/curriculum/questions/mcq/embeddings_and_similarity.md` | **new** | 5 MCQ questions |
| `knowledge-base/curriculum/questions/mcq/chunking_strategies.md` | **new** | 5 MCQ questions |
| `knowledge-base/curriculum/questions/mcq/vector_databases.md` | **new** | 5 MCQ questions |
| `knowledge-base/curriculum/questions/mcq/retrieval_methods.md` | **new** | 5 MCQ questions |
| `knowledge-base/curriculum/questions/mcq/context_and_prompting.md` | **new** | 5 MCQ questions |
| `knowledge-base/curriculum/questions/mcq/evaluation_and_metrics.md` | **new** | 5 MCQ questions |
| `knowledge-base/curriculum/questions/mcq/production_patterns.md` | **new** | 5 MCQ questions |
| `knowledge-base/curriculum/gates.md` | **update** | Add MCQ scoring addendum (binary: no partial credit) |

---

## MCQ Format Specification

Lara must define and use this exact format in `mcq-format.md` and all MCQ question files:

```markdown
## MCQ-[N] — [Short title]

**Difficulty:** beginner | intermediate | advanced
**Topic:** [slug]

**Question:**
[Question text — single clear question, no compound questions]

**Options:**
A. [Option A text]
B. [Option B text]
C. [Option C text]
D. [Option D text]

**Correct answer:** [A | B | C | D]

**Explanation:**
[Why the correct answer is right. 1–3 sentences. Mention why the most tempting wrong option is incorrect — this serves as learning feedback.]
```

**Field constraints (must be enforced in mcq-format.md):**
- Exactly 4 options per question (A–D). No more, no fewer.
- Exactly 1 correct answer per question. No ambiguous "best answer" framing.
- Options must be mutually exclusive — a learner who understands the topic cannot
  reasonably argue more than one is correct.
- Question text must be answerable from RAG curriculum knowledge alone — no trick questions,
  no questions requiring framework-specific knowledge (e.g., "which LangChain class...")
- Explanation must reference why the correct answer is right, not merely restate it.
- Distractors (wrong options) should be plausible confusions, not obviously absurd choices.

**Difficulty distribution per topic (5 questions):**
- 2 beginner
- 2 intermediate
- 1 advanced

---

## Scoring Rules Addendum for gates.md

Lara must append to `gates.md` an MCQ scoring section:

```
## MCQ Question Scoring

MCQ questions are scored **binary** — no partial credit:

| Evaluation method | Score |
|---|---|
| Answer matches correct answer key | 1.0 |
| Answer does not match | 0.0 |

MCQ scores feed the same session/topic score formula as open-ended questions:
- session_score = mean(question_scores_in_session)
- topic_score = 0.7 × current_session + 0.3 × best_prior_session

Minimum questions per session for a valid score (inherited from existing rule): 3.

Because MCQ scoring is binary, the topic score distribution will cluster at
0.0 and 1.0 per question, but the session and topic score remain continuous
(mean of binary values).
```

---

## Handoff Outputs

After this commit, Lara must produce these handoff notes in her worklog:

**→ Nova (Commit 35 `mcq-assessment-engine`):**
- MCQ question files are at `knowledge-base/curriculum/questions/mcq/[slug].md`
- Format schema is in `knowledge-base/curriculum/mcq-format.md`
- Each file has exactly 5 questions, fields: `Correct answer:` is the answer key
- Binary scoring: answer key comparison only — no LLM rubric evaluation for MCQ
- Session minimum of 3 questions still applies

**→ Nova (Commit 36 `onboarding-level-check`):**
- The `embeddings_and_similarity` and `rag_pipeline_architecture` MCQ files can serve
  as diagnostic question sources for onboarding (3 questions from each, mixed difficulty)
- Onboarding questions are read-only references — do not modify the MCQ banks for onboarding

---

## Quality Gate Triage

| Reviewer | Decision | Reason |
|---|---|---|
| Viktor | **skip** | Knowledge-base Markdown only — no code, no logic |
| Sage | **skip** | No auth, no secrets, no user data, no external API |
| Quinn | **skip** | No test suite applicable to curriculum content |
| Mira | **skip** | Knowledge-base content only — no user-facing behavior change in this commit |
| Ryan | **run** | Always runs; one-liner entry (content addition, no architectural change) |

---

## Test Gate

No automated test suite for knowledge-base content. Lara validates:
- All 8 MCQ files exist with exactly 5 questions each
- Every question has fields: Question, Options (A–D), Correct answer, Explanation
- No question has more than 1 correct answer marked
- Difficulty distribution: 2 beginner + 2 intermediate + 1 advanced per topic
- `mcq-format.md` exists with format schema and scoring rules
- `gates.md` has MCQ scoring addendum appended

---

## Parallel Dependency Note (Wave D)

This commit runs in parallel with Commit 34 (`phase-gate-enforcement`, Nova).
They do not share files. Nova's Commit 34 wires phase gate logic into
`assess_node._select_test_slug()` — it does not need the MCQ question content.
Commit 35 (`mcq-assessment-engine`) depends on BOTH Commits 33 and 34 being complete.
