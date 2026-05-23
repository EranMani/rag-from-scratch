# MCQ Format — RAG Curriculum
# Project: rag-from-scratch
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-19 (Commit 33)

---

## Purpose

MCQ (multiple-choice question) banks serve as phase-gate advancement instruments.
They are scored deterministically via answer key comparison — no LLM evaluator is
required. This makes them reliable for gate progression logic, unlike open-ended
questions whose rubric-based scoring depends on LLM evaluator accuracy.

Open-ended questions remain the primary learning instrument. MCQs are the gating
instrument — used exclusively at phase transitions until the open-ended scorer is
validated.

---

## Question Format

Every MCQ must follow this exact structure:

```markdown
## MCQ-[N] — [Short title]

**Difficulty:** novice | intermediate | advanced
**Topic:** [slug]

**Question:**
[Question text]

**Options:**
A. [Option text]
B. [Option text]
C. [Option text]
D. [Option text]

**Correct answer:** [A | B | C | D]

**Explanation:**
[1–3 sentences: why the correct answer is right; why the most tempting wrong option is incorrect]
```

---

## Field Definitions

| Field | Requirement |
|---|---|
| `MCQ-[N]` | Sequential number within the topic file, starting at 1 |
| Short title | 3–6 words identifying the concept tested |
| `Difficulty` | Exactly one of: `novice`, `intermediate`, `advanced` |
| `Topic` | Exactly one canonical slug from `topic-slugs.json` |
| `Question` | Single clear question. No compound questions ("X and Y?"). No trick framing. |
| `Options` | Exactly 4 options labeled A, B, C, D. No more, no fewer. |
| `Correct answer` | Exactly one of: `A`, `B`, `C`, or `D` |
| `Explanation` | 1–3 sentences. Must state why the correct answer is right and why the most tempting wrong option is incorrect. Must not simply restate the correct answer. |

---

## Quality Constraints

**Mutual exclusivity.** Options must be mutually exclusive — a learner who understands
the topic cannot reasonably argue more than one option is correct.

**No ambiguous framing.** Never use "best answer" framing. There is exactly one correct
answer, and an informed learner should agree.

**No framework trivia.** Questions must be answerable from RAG concept knowledge alone.
Questions like "which LangChain class implements reranking?" are forbidden. Questions
like "what is the purpose of a reranker in a RAG pipeline?" are correct.

**Plausible distractors.** Wrong options must represent realistic confusions a learner
might have — not absurd or obviously irrelevant choices. A distractor should reflect a
genuine misconception or a related concept that could be confused with the correct one.

**Single topic focus.** Each question tests one concept from its topic. Questions that
span multiple topics are not permitted in the MCQ bank — they belong in open-ended questions.

---

## Difficulty Distribution

Every topic file must contain exactly 5 questions with this distribution:

| Difficulty | Count |
|---|---|
| novice | 2 |
| intermediate | 2 |
| advanced | 1 |

Beginner questions test definition and basic concept recall. Intermediate questions
test application and tradeoff understanding. Advanced questions test architectural
judgment or subtle failure modes.

---

## Scoring Rules

MCQ questions are scored **binary** — no partial credit:

| Evaluation method | Score |
|---|---|
| Answer matches correct answer key | 1.0 |
| Answer does not match | 0.0 |

Evaluation is performed by exact string comparison against the `Correct answer` field.
Valid answer values: `A`, `B`, `C`, `D`. Any other value is treated as incorrect.

MCQ scores feed the same session/topic score formula as open-ended questions:

```
session_score = mean(question_scores_in_session)
topic_score = 0.7 × current_session_score + 0.3 × best_prior_session_score
```

Minimum questions per session for a valid score: **3** (inherited from gates.md).

Because MCQ scoring is binary, per-question scores cluster at 0.0 and 1.0. The session
and topic scores remain continuous (mean of binary values across all questions answered
in a session).

---

## Relationship to Open-Ended Questions

| Attribute | MCQ | Open-ended |
|---|---|---|
| Scoring method | Answer key comparison (deterministic) | LLM rubric evaluation |
| Partial credit | No | Yes (0.5) |
| Primary use | Phase gate advancement | In-session learning and assessment |
| Evaluator required | No | Yes |
| Question files | `questions/mcq/[slug].md` | `questions/[slug].md` |

---

## File Organization

MCQ files are stored separately from open-ended question banks:

```
knowledge-base/curriculum/questions/
  mcq/
    embeddings_and_similarity.md
    rag_pipeline_architecture.md
    chunking_strategies.md
    vector_databases.md
    retrieval_methods.md
    context_and_prompting.md
    evaluation_and_metrics.md
    production_patterns.md
  embeddings_and_similarity.md     ← open-ended (existing)
  rag_pipeline_architecture.md     ← open-ended (existing)
  ... (other existing open-ended files)
```
