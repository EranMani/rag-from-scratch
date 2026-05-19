# Lara — Worklog
# Project: rag-from-scratch
# Stack: Markdown curriculum artifacts, JSON schemas, docs/ product specs

---

## Current State
*Last updated: Commit 33 · 2026-05-19*

**Last completed:** Commit 33 `question-bank-mcq` (complete)
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- Nova (Commit 35 `mcq-assessment-engine`): MCQ question files live at
  `knowledge-base/curriculum/questions/mcq/[slug].md`. Format schema is at
  `knowledge-base/curriculum/mcq-format.md`. Each file has exactly 5 questions.
  Answer key field: `**Correct answer:** [A|B|C|D]`. Binary scoring only — answer key
  comparison, no LLM rubric evaluation for MCQ. Session minimum of 3 questions still applies.
- Nova (Commit 36 `onboarding-level-check`): `embeddings_and_similarity` and
  `rag_pipeline_architecture` MCQ files can source onboarding diagnostics (3 questions each,
  mixed difficulty). Onboarding questions are read-only references — do not modify MCQ banks
  for onboarding.

**Open Handoffs — Inbound:**
- (none)

**Key Interfaces I Own (for teammates):**
- `knowledge-base/curriculum/topic-slugs.json` — canonical 8-slug list. Rex reads this in Commit 25 to update `VALID_MODULE_SLUGS` and `TopicScoresDelta`.
- `knowledge-base/curriculum/gates.md` — phase gate score thresholds. Nova and Rex implement gate logic from this file.
- `knowledge-base/curriculum/questions/[slug].md` — test question banks with rubrics. Nova's assessment prompt references these in Commit 24.
- `docs/scoring-model.md` — produced jointly with Mira in Commit 23. The canonical scoring contract for Nova and Rex.

**Decisions Other Agents Must Know:**
- Phase 2 has a dual gate: per-topic minimum (0.70) AND a mean threshold (0.75). The mean threshold is not present in Phase 1 or Phase 3. This is by design — Phase 2 topics are interdependent and must be balanced.
- Topic scores use spaced repetition weighting: `0.7 × current_session + 0.3 × best_prior_session`. This formula is in `gates.md` and must be used exactly.
- A null topic score (no sessions completed) must be treated as failing the gate — not as 0.0. The distinction matters: 0.0 means the learner tried and failed; null means they haven't attempted it. Gate logic must handle null explicitly.
- Verdict vocabulary is exact: only `correct`, `partial`, `incorrect` are valid LLM evaluator outputs. Any other value must be treated as `incorrect` and flagged. This must be enforced in Nova's evaluator prompt.

**Scope Overflows Pre-Built:**
- (none)

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 1 | Commit 22 `rag-curriculum-design` | Complete | Dual gate for Phase 2 (per-topic + mean threshold); spaced repetition scoring formula |
| 2 | Commit 33 `question-bank-mcq` | Complete | MCQ as binary-scored gate instrument, separate from open-ended learning questions |

---

## Session 01 — Commit 22: `rag-curriculum-design`

**Date:** 2026-05-11
**Status:** Complete

### Task Brief

Build the complete RAG learning curriculum from scratch. This is a knowledge-base-only
commit — no application source code changes. The artifacts produced here are the
canonical reference for Commits 23–25. Deliverables: curriculum map, topic-slugs.json,
phase gates, and 8 question bank files (one per slug) each with minimum 5 questions
and full rubrics.

Success criteria: all 8 question bank files exist with ≥5 questions each, `topic-slugs.json`
is a valid JSON array of exactly 8 slugs, gate thresholds are defined as precise numerics,
and the curriculum map covers the full zero-to-hero arc with learning objectives per topic.

### Approach

The central design question was how to define phase gates precisely enough for Nova and
Rex to implement gate logic unambiguously, while keeping the thresholds pedagogically
justified — not arbitrary. I chose a 0.70 per-topic floor for all phases as the baseline
competency threshold (low confidence in key concepts should not advance), then added a
0.75 mean floor specifically to Phase 2 because its four topics are deeply interconnected:
a learner who aces vector databases but barely passes retrieval methods will struggle in
Phase 3, where both domains are assumed as fluent foundation.

For the scoring formula, spaced repetition weighting (`0.7 × current + 0.3 × best_prior`)
was chosen over a simple session mean to reward improvement and persistence — a learner
who scores 0.80 after previously scoring 0.60 should not be treated identically to one
who scored 0.80 on their first attempt with no prior sessions.

For question design, the core concern was rubric precision: vague rubrics produce inconsistent
LLM evaluator verdicts, which corrupt topic scores and gate logic downstream. Every question's
correct/partial/incorrect criteria were written with LLM evaluation in mind — the criteria
specify observable indicators in the learner's response, not abstract quality judgments.

The null-topic question required a deliberate decision: should a topic with no sessions score
0.0 or null? I chose null with a hard "null does not pass" rule, because 0.0 conflates
"learner attempted and failed" with "learner has not attempted" — two very different states
for a system that needs to know whether to prompt the learner to attempt a topic or to remediate.

### Decisions Made

**1. Dual gate for Phase 2 (per-topic 0.70 AND mean 0.75)**
Phase 2 topics (chunking, vector databases, retrieval methods, context and prompting) are
interdependent — a weak retrieval methods score implies fragile vector database understanding,
and vice versa. Single-threshold gates would allow a learner to drag the average with one
weak topic. The mean floor (0.75) catches this without being punitive for learners who
genuinely master three topics quickly and need more time on the fourth.
Phase 1 and Phase 3 topics are less interdependent (Phase 1 has only two topics; Phase 3
topics can be studied in sequence), so the mean floor was not applied there.

**2. Phase 3 floor raised to 0.75 (not 0.70)**
Phase 3 covers operational competency (evaluation, production patterns). A learner who
passes at 0.70 may understand the concepts but not the judgment required to safely operate
a production system. The 0.75 floor reflects that production knowledge is higher-stakes
than foundational or core knowledge — errors in production patterns (e.g., incorrect
understanding of cache invalidation or index staleness) have downstream consequences.

**3. Spaced repetition weighting in topic score formula**
The formula `topic_score = 0.7 × current_session_score + 0.3 × best_prior_session_score`
was chosen to:
- Primarily reflect current performance (0.7 weight) — the most recent session is the
  best indicator of current knowledge state
- Reward learning persistence (0.3 weight on best prior) — a learner who improves over
  time should not be scored identically to one who plateaus
- Avoid penalizing early struggle — a poor first-session score does not permanently
  anchor the topic score if the learner improves
Alternative considered: simple current-session average. Rejected because it treats
all sessions equally, ignoring the learning arc.

**4. Null vs. 0.0 for unassessed topics**
Topics with no completed sessions are stored as null, not 0.0. Gate logic must explicitly
handle null as failing (null >= threshold is false). This prevents an unassessed topic
from accidentally "passing" a gate due to a null-handling bug, and preserves the
distinction between "hasn't tried" and "tried and scored zero" for remediation logic.

**5. Minimum 3 questions per session for a valid score update**
Sessions with fewer than 3 questions do not update the topic score. This prevents a
single lucky correct answer from producing a misleadingly high score, or a single unlucky
wrong answer from producing a misleadingly low score. 3 was chosen as the floor because
it is the minimum to produce a score with three possible states (0.0, 0.33/0.67, 1.0)
with partial credit at the intermediate level.

### Issues Found Mid-Task

None. All files were new — no conflicts with existing content.

### Self-Review Checklist

- [x] All 8 question bank files created with >= 5 questions each
- [x] All questions have full rubric: correct / partial / incorrect criteria
- [x] `topic-slugs.json` is valid JSON array with exactly 8 slugs
- [x] `gates.md` defines numeric thresholds for all three phases (0.70/0.75 per-topic, 0.75 mean for Phase 2)
- [x] Scoring formula fully specified in `gates.md` with JSON machine-readable block
- [x] `curriculum-map.md` covers all 8 topics with learning objectives, prerequisites, and misconceptions
- [x] No `src/` files touched
- [x] No `tests/` files touched
- [x] No `docker-compose*.yml` files touched
- [x] Worklog updated with session entry and handoff notes

### Scope Overflow Check

No scope overflows. All deliverables are within the Commit 22 spec.

### Documentation Flags for Claude

**DECISIONS.md:**
- Phase 2 dual gate (per-topic + mean) — Phase 2 topics are interdependent; mean threshold
  prevents a learner from advancing with one weak topic dragging the average below competency
- Spaced repetition weighting formula — rewards learning persistence while primarily
  reflecting current session performance
- Null vs. 0.0 for unassessed topics — null explicitly fails gate checks; prevents
  unassessed-topic-as-passing bug

**ARCHITECTURE.md:**
- `knowledge-base/curriculum/` — new directory containing the complete RAG curriculum:
  topic map, machine-readable slug list, phase gate definitions, and per-slug question banks

**GLOSSARY.md:**
- Phase gate — a score threshold that must be met for all topics in a phase before the
  learner can access the next phase's content
- Topic score — the per-slug competency score, computed as a weighted combination of
  current and best-prior session scores using spaced repetition weighting
- Faithfulness (RAGAS) — the fraction of claims in a generated answer that are
  attributable to the retrieved context
- Context precision (RAGAS) — the fraction of retrieved chunks that are actually
  relevant to answering the question
- Context recall (RAGAS) — the fraction of information needed to answer the question
  that is present in the retrieved chunks

---

---

## Session 02 — Commit 33: `question-bank-mcq`

**Date:** 2026-05-19
**Status:** Complete

### Files Created

- `knowledge-base/curriculum/mcq-format.md` — MCQ schema, field definitions, quality constraints, scoring rules, file organization reference
- `knowledge-base/curriculum/questions/mcq/embeddings_and_similarity.md` — 5 MCQs
- `knowledge-base/curriculum/questions/mcq/rag_pipeline_architecture.md` — 5 MCQs
- `knowledge-base/curriculum/questions/mcq/chunking_strategies.md` — 5 MCQs
- `knowledge-base/curriculum/questions/mcq/vector_databases.md` — 5 MCQs
- `knowledge-base/curriculum/questions/mcq/retrieval_methods.md` — 5 MCQs
- `knowledge-base/curriculum/questions/mcq/context_and_prompting.md` — 5 MCQs
- `knowledge-base/curriculum/questions/mcq/evaluation_and_metrics.md` — 5 MCQs
- `knowledge-base/curriculum/questions/mcq/production_patterns.md` — 5 MCQs

### Files Modified

- `knowledge-base/curriculum/gates.md` — appended MCQ scoring addendum (binary scoring, same session/topic formula, same 3-question session minimum)

### Key Decisions

**1. MCQ files stored in a separate subdirectory (`questions/mcq/`)**
Separating MCQ files from open-ended question banks prevents Nova from accidentally
loading MCQ rubric logic into the LLM evaluator prompt. The two formats serve different
pipeline stages and must be clearly distinguished by path. If they were co-located in
the same directory, a glob pattern like `questions/*.md` would pick up both formats.

**2. Binary scoring — no partial credit for MCQ**
MCQ questions either match the answer key (1.0) or do not (0.0). Partial credit
requires rubric evaluation, which defeats the purpose of MCQ as a deterministic,
LLM-evaluator-free instrument for phase gate advancement. The session/topic formula
remains identical — only the per-question score range changes (0/1 instead of 0/0.5/1).

**3. Difficulty distribution: 2 beginner + 2 intermediate + 1 advanced per topic**
The distribution weights toward approachable questions. A gate test that is heavily
advanced would produce low pass rates not because learners lack mastery but because
advanced questions require synthesis beyond what a gate test should measure. The single
advanced question per topic is sufficient to distinguish thorough from surface understanding.

**4. No framework-specific questions**
All 40 questions are answerable from RAG concept knowledge. No question references
LangChain, LlamaIndex, or any specific library. This ensures the MCQ bank remains
valid regardless of which frameworks the learner has worked with.

### Self-Review Checklist

- [x] All 8 MCQ files exist under `knowledge-base/curriculum/questions/mcq/`
- [x] Every file has exactly 5 questions
- [x] Every question has all required fields: Question, Options (A-D), Correct answer, Explanation
- [x] No question has more than 1 correct answer marked
- [x] Difficulty distribution per file: 2 beginner + 2 intermediate + 1 advanced
- [x] `mcq-format.md` exists with schema and scoring rules
- [x] `gates.md` has MCQ scoring addendum appended
- [x] Worklog updated

### Scope Overflow Check

No scope overflows. All deliverables are within the Commit 33 spec. No `src/` files,
no test files, no infrastructure files touched.

---

## 📋 Replan Notice — 2026-05-11

Lara onboarded as new team member via mid-project replan.

**Context:** The knowledge profile scoring model was broken — it inferred user understanding
from question content (what the user *asked*) rather than test performance (how well the user
*answered*). The fix requires a curriculum-first, test-answer-based redesign.

**Lara's role in this project:**
- Commit 22: Build the complete RAG curriculum (topic map, question bank, phase gates)
- Commit 23: Joint product spec with Mira — how curriculum test performance maps to scores

**Slug schema Lara defined (replaces the prior 6-slug set):**
- DROP: `rag_fundamentals` (split), `langchain` (removed)
- ADD: `embeddings_and_similarity`, `rag_pipeline_architecture`, `context_and_prompting`, `evaluation_and_metrics`
- KEEP: `chunking_strategies`, `vector_databases`, `retrieval_methods`, `production_patterns`

**Next commit:** Commit 22 `rag-curriculum-design`

---

## Replan Notice — 2026-05-19

The commit plan has been updated. Here is what changed for you:

**What was removed:** nothing

**What was added:**
- Commit 33 `question-bank-mcq` — add 3–4 MCQ questions (4-choice format) per topic to all 8 question banks; tag every existing question as tier: advancement or tier: learning; define MCQ block format in each file header; knowledge-base/ only, no code

**What changed in your sequence:**
- Commit 33 is new and comes immediately after Commit 32 (already done)
- Commit 33 can run in parallel with Commit 34 (Nova, Wave D) — no shared files
- Nova's Commit 35 (mcq-assessment-engine) depends on your Commit 33 being complete

**MCQ format guidance:**
- advancement questions = designated assessment questions that gate phase progression
- learning questions = conversational probes the agent uses while teaching (do not gate)
- MCQ format: question + 4 options (A/B/C/D), one marked correct, all options plausible
- Ratio target: 60% MCQ for factual/definitional questions, 40% open for reasoning/synthesis
- All existing open questions keep their existing format — just add the tier tag

**Your next commit is now: Commit 33 `question-bank-mcq`**
