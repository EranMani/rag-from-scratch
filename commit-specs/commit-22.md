# Commit 22 Spec — `rag-curriculum-design`
> **Project:** rag-from-scratch · **Assignee:** Lara · **Load only for the active commit.**

---

### Commit 22 — `rag-curriculum-design`

**Commit message:** `feat: RAG curriculum — topic map, question bank, phase gates`

**Body:**
Lara builds the complete RAG learning curriculum. This is a knowledge-base-only commit —
no application source code changes. The curriculum artifacts produced here are the
canonical reference for Commits 23–25.

**Canonical topic slugs (replaces the prior 6-slug set):**

| Slug | Phase | What it covers |
|---|---|---|
| `embeddings_and_similarity` | 1 | Vector embeddings, cosine similarity, semantic search intuition |
| `rag_pipeline_architecture` | 1 | Indexing + query phases, context injection, generation loop |
| `chunking_strategies` | 2 | Fixed vs. semantic chunking, overlap, token budgets, recall impact |
| `vector_databases` | 2 | HNSW/IVF index types, ANN tradeoffs, metadata filtering, collection design |
| `retrieval_methods` | 2 | Sparse (BM25), dense, hybrid, reranking, MMR, multi-query, HyDE |
| `context_and_prompting` | 2 | Context window management, prompt templates, hallucination mitigation |
| `evaluation_and_metrics` | 3 | RAGAS, faithfulness, answer relevancy, context precision/recall |
| `production_patterns` | 3 | Caching, async pipelines, observability, cost control, failure modes |

**Three-phase curriculum with hard phase gates:**
- **Phase 1 (Foundations):** `embeddings_and_similarity` + `rag_pipeline_architecture`
  Entry: zero. Exit: both slugs ≥ passing threshold.
- **Phase 2 (Core components):** `chunking_strategies` + `vector_databases` + `retrieval_methods` + `context_and_prompting`
  Entry: Phase 1 gate passed. Exit: all four slugs ≥ passing threshold.
- **Phase 3 (Production):** `evaluation_and_metrics` + `production_patterns`
  Entry: Phase 2 gate passed. Exit: both slugs ≥ passing threshold.

**Assignee:** Lara

**Files touched:**
- `knowledge-base/curriculum/curriculum-map.md` (new) — topic tree, phase assignments, learning objectives per topic
- `knowledge-base/curriculum/topic-slugs.json` (new) — canonical 8-slug list (machine-readable, consumed by Commits 24–25)
- `knowledge-base/curriculum/gates.md` (new) — phase gate score thresholds and advancement criteria
- `knowledge-base/curriculum/questions/embeddings_and_similarity.md` (new) — test question bank with rubrics
- `knowledge-base/curriculum/questions/rag_pipeline_architecture.md` (new)
- `knowledge-base/curriculum/questions/chunking_strategies.md` (new)
- `knowledge-base/curriculum/questions/vector_databases.md` (new)
- `knowledge-base/curriculum/questions/retrieval_methods.md` (new)
- `knowledge-base/curriculum/questions/context_and_prompting.md` (new)
- `knowledge-base/curriculum/questions/evaluation_and_metrics.md` (new)
- `knowledge-base/curriculum/questions/production_patterns.md` (new)

**Depends on:** Commit 21

**Testing — done when:**
- [ ] All 8 question bank files exist with ≥ 5 test questions each, each with a full rubric (correct / partial / incorrect criteria)
- [ ] `topic-slugs.json` contains exactly the 8 canonical slugs, machine-readable array
- [ ] Phase gate thresholds defined in `gates.md` as numeric score values per slug
- [ ] Curriculum map covers the full zero-to-hero arc with clear learning objectives per topic
- [ ] No application source code was modified (Lara's domain is knowledge-base/ only)
