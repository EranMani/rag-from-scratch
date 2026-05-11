# Lara — Worklog
# Project: rag-from-scratch
# Stack: Markdown curriculum artifacts, JSON schemas, docs/ product specs

---

## Current State
*Last updated: Replan · 2026-05-11*

**Last completed:** none (onboarded via replan 2026-05-11)
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- (none yet)

**Open Handoffs — Inbound:**
- (none)

**Key Interfaces I Own (for teammates):**
- `knowledge-base/curriculum/topic-slugs.json` — canonical 8-slug list. Rex reads this in Commit 25 to update `VALID_MODULE_SLUGS` and `TopicScoresDelta`.
- `knowledge-base/curriculum/gates.md` — phase gate score thresholds. Nova and Rex implement gate logic from this file.
- `knowledge-base/curriculum/questions/[slug].md` — test question banks with rubrics. Nova's assessment prompt references these in Commit 24.
- `docs/scoring-model.md` — produced jointly with Mira in Commit 23. The canonical scoring contract for Nova and Rex.

**Decisions Other Agents Must Know:**
- (populate after Commit 22)

**Scope Overflows Pre-Built:**
- (none)

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|

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
