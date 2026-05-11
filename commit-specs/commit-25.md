# Commit 25 Spec — `profile-scoring-rewrite`
> **Project:** rag-from-scratch · **Assignee:** Rex · **Load only for the active commit.**

---

### Commit 25 — `profile-scoring-rewrite`

**Commit message:** `feat: 8-slug schema migration and test-performance scoring rewrite`

**Body:**
Two changes shipped together because they are coupled: (1) the canonical topic slug
set changes from 6 to 8, requiring a DB migration; (2) `compute_topic_scores` is
rewritten to accept test performance events as defined in `docs/scoring-model.md`.

**Spec reference:** `docs/scoring-model.md` (Commit 23) defines the scoring formula Rex implements.

---

**Slug schema change (`src/agents/state.py`):**

| Action | Slug | Migration |
|---|---|---|
| DROP | `rag_fundamentals` | Migrate scores → `rag_pipeline_architecture` |
| DROP | `langchain` | Discard scores — no migration |
| ADD | `rag_pipeline_architecture` | Receives migrated `rag_fundamentals` scores |
| ADD | `embeddings_and_similarity` | Starts at 0.0 for all users |
| ADD | `context_and_prompting` | Starts at 0.0 for all users |
| ADD | `evaluation_and_metrics` | Starts at 0.0 for all users |
| KEEP | `chunking_strategies` | Unchanged |
| KEEP | `vector_databases` | Unchanged |
| KEEP | `retrieval_methods` | Unchanged |
| KEEP | `production_patterns` | Unchanged |

**`TopicScoresDelta` update:** Remove `rag_fundamentals` and `langchain` fields.
Add `rag_pipeline_architecture`, `embeddings_and_similarity`, `context_and_prompting`,
`evaluation_and_metrics` fields. Total: 8 fields.

**`VALID_MODULE_SLUGS` update:** Replace the 6-slug frozenset with the 8 canonical
slugs from `knowledge-base/curriculum/topic-slugs.json`.

---

**DB migration (`src/app/profile/db.py`):**

Run at startup, idempotently:
1. For each row in `user_profiles.topic_scores`:
   - Copy `rag_fundamentals` value → `rag_pipeline_architecture`
   - Add `embeddings_and_similarity: 0.0`
   - Add `context_and_prompting: 0.0`
   - Add `evaluation_and_metrics: 0.0`
   - Remove `rag_fundamentals` key
   - Remove `langchain` key (discard value)
2. Idempotency check: if `rag_pipeline_architecture` key already exists in a row, skip that row.

---

**`compute_topic_scores` rewrite (`src/app/profile/scoring.py`):**

New signature accepts test performance as defined in `docs/scoring-model.md`:
the scoring formula (delta magnitude per performance level, decay rules, threshold logic)
comes from the product spec — Rex implements it exactly, no improvisation.

---

**Assignee:** Rex

**Files touched:**
- `src/agents/state.py` — update `TopicScoresDelta`, `VALID_MODULE_SLUGS`, `AssessmentOutput`
- `src/app/profile/scoring.py` — rewrite `compute_topic_scores`
- `src/app/profile/db.py` — add idempotent migration logic for `topic_scores` JSON column
- `tests/test_scoring.py` — update for new formula and 8-slug set
- `tests/test_assess_node.py` — update any profile assertions that reference old slugs

**Depends on:** Commit 24 (Nova's assessment node must be complete — Rex's scoring service must match Nova's output contract)

**Testing — done when:**
- [ ] `VALID_MODULE_SLUGS` has exactly 8 entries matching `knowledge-base/curriculum/topic-slugs.json`
- [ ] `TopicScoresDelta` has exactly 8 fields (no `langchain`, no `rag_fundamentals`)
- [ ] DB migration runs idempotently — running twice does not corrupt scores
- [ ] Existing profile with `rag_fundamentals: 0.6` migrates to `rag_pipeline_architecture: 0.6`
- [ ] `langchain` scores discarded without error
- [ ] `compute_topic_scores` formula matches `docs/scoring-model.md` exactly — no approximations
- [ ] All scoring tests pass with the 8-slug set
