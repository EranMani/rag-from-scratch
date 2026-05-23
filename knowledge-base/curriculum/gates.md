# Phase Gates — RAG Curriculum
# Project: rag-from-scratch
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-23 (Commit 49)

---

## Scoring Scale

All topic scores are expressed on a **0.0–1.0 scale**, where:

- `1.0` = perfect mastery (all rubric criteria met across all tested questions)
- `0.0` = no demonstrated understanding

Scores are derived from question bank assessments. Each question produces a score
of `0.0` (incorrect), `0.5` (partial credit), or `1.0` (fully correct). The topic
score is the mean of all question scores for that topic in a given session.

A **session score** is the average of all question scores in the assessment session
for that topic. A **topic score** is computed as a weighted combination:

```
topic_score = 0.7 × current_session_score + 0.3 × best_prior_session_score
```

If no prior session exists, `topic_score = current_session_score`.

---

## Phase Gate Definitions

### Phase 1 Gate

**Topics required:** `embeddings_and_similarity`, `rag_pipeline_architecture`

**Advancement threshold:** Each topic must reach a minimum score of **0.70**.

**Exact rule:**
```
phase_1_passed = (
    score["embeddings_and_similarity"] >= 0.70
    AND score["rag_pipeline_architecture"] >= 0.70
)
```

**Consequence of failure:**
The learner is returned to Phase 1 study. The system identifies which topic(s) are
below threshold and generates targeted remediation questions from that topic's question
bank, weighted toward the question difficulty levels where the learner underperformed.

**Hard gate enforcement:**
Phase 2 topics (`chunking_strategies`, `vector_databases`, `retrieval_methods`,
`context_and_prompting`) are not accessible until `phase_1_passed = true`.

---

### Phase 2 Gate

**Topics required:** `chunking_strategies`, `vector_databases`, `retrieval_methods`, `context_and_prompting`, `document_ingestion`

**Advancement threshold:** Each topic must reach a minimum score of **0.70**.
Additionally, the mean score across all five Phase 2 topics must be at least **0.75**.

**Exact rule:**
```
phase_2_individual_pass = (
    score["chunking_strategies"] >= 0.70
    AND score["vector_databases"] >= 0.70
    AND score["retrieval_methods"] >= 0.70
    AND score["context_and_prompting"] >= 0.70
    AND score["document_ingestion"] >= 0.70
)

phase_2_mean = mean([
    score["chunking_strategies"],
    score["vector_databases"],
    score["retrieval_methods"],
    score["context_and_prompting"],
    score["document_ingestion"]
])

phase_2_passed = phase_2_individual_pass AND phase_2_mean >= 0.75
```

**Rationale for mean threshold:** Phase 2 topics are interconnected — a learner who
scrapes 0.70 on four topics but scores 0.90+ on the fifth may have uneven foundations
that cause confusion in Phase 3. The 0.75 mean ensures balanced competency.

**Consequence of failure:**
Same as Phase 1: targeted remediation for topics below 0.70 first, then re-test.
If individual thresholds pass but mean fails, the learner receives a mixed remediation
session drawing from all Phase 2 topics, weighted by distance from 0.75.

**Hard gate enforcement:**
Phase 3 topics (`evaluation_and_metrics`, `production_patterns`, `langgraph_fundamentals`)
are not accessible until `phase_2_passed = true`. Additionally, `document_ingestion`
(a Phase 2 topic) is not accessible until `phase_1_passed = true`.

---

### Phase 3 Gate (Curriculum Completion)

**Topics required:** `evaluation_and_metrics`, `production_patterns`, `langgraph_fundamentals`

**Advancement threshold:** Each topic must reach a minimum score of **0.75**.

**Exact rule:**
```
phase_3_passed = (
    score["evaluation_and_metrics"] >= 0.75
    AND score["production_patterns"] >= 0.75
    AND score["langgraph_fundamentals"] >= 0.75
)
```

**Rationale for higher threshold:** Phase 3 topics represent operational competency.
A learner who passes at 0.70 may be able to design a RAG system but fail to operate
or improve one safely. The 0.75 floor reflects the higher stakes of production knowledge.

**Consequence of failure:**
Targeted remediation. On completion, the learner is certified as having completed the
full zero-to-hero RAG curriculum.

---

## Score Computation Rules (for Nova / Rex implementation)

### Per-question scoring

| LLM evaluator verdict | Score assigned |
|----------------------|----------------|
| `correct` | 1.0 |
| `partial` | 0.5 |
| `incorrect` | 0.0 |

The LLM evaluator must reference the rubric in the question bank file for each question.
The verdict must be one of exactly `correct`, `partial`, or `incorrect` — no other values
are valid. Invalid verdicts are treated as `incorrect` and flagged for review.

### Session score

```
session_score = mean(question_scores_in_session)
```

Minimum questions per session for a score to be valid: **3**. Sessions with fewer than
3 questions produce no score update — the topic score is unchanged.

### Topic score (with spaced repetition weighting)

```
topic_score = 0.7 × current_session_score + 0.3 × best_prior_session_score
```

If no prior session exists:
```
topic_score = current_session_score
```

The `best_prior_session_score` is the highest session score the learner has ever
achieved for that topic across all prior sessions.

### Null / unassessed topics

A topic with no completed sessions has a score of `null`, not `0.0`. Gate logic must
treat `null` as failing (i.e., `null >= 0.70` is `false`). This prevents a topic
being "skipped" from accidentally passing a gate.

---

## Phase Score Summary (machine-readable reference)

```json
{
  "phase_gates": {
    "phase_1": {
      "required_topics": ["embeddings_and_similarity", "rag_pipeline_architecture"],
      "per_topic_minimum": 0.70,
      "mean_minimum": null
    },
    "phase_2": {
      "required_topics": ["chunking_strategies", "vector_databases", "retrieval_methods", "context_and_prompting", "document_ingestion"],
      "per_topic_minimum": 0.70,
      "mean_minimum": 0.75
    },
    "phase_3": {
      "required_topics": ["evaluation_and_metrics", "production_patterns", "langgraph_fundamentals"],
      "per_topic_minimum": 0.75,
      "mean_minimum": null
    }
  },
  "scoring": {
    "question_scores": {"correct": 1.0, "partial": 0.5, "incorrect": 0.0},
    "min_questions_per_session": 3,
    "topic_score_formula": "0.7 * current_session + 0.3 * best_prior_session",
    "null_topic_passes_gate": false
  }
}
```

---

## MCQ Question Scoring

MCQ questions are scored **binary** — no partial credit:

| Evaluation method | Score |
|---|---|
| Answer matches correct answer key | 1.0 |
| Answer does not match | 0.0 |

MCQ scores feed the same session/topic score formula as open-ended questions:
- `session_score = mean(question_scores_in_session)`
- `topic_score = 0.7 × current_session + 0.3 × best_prior_session`

Minimum questions per session for a valid score (inherited from existing rule): 3.

Because MCQ scoring is binary, per-question scores cluster at 0.0 and 1.0, but
the session and topic scores remain continuous (mean of binary values across all
questions answered in a session).
