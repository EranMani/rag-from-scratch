# Commit 45 Spec — `rag-specialist-content`
> **Project:** rag-from-scratch · **Assignee:** rag-specialist · **Load only for the active commit.**
> **Note:** Added in replan 2026-05-20 — question banks are thin (5 questions per topic, no expert tier); RAG Specialist expands with practitioner-depth content.

---

### Commit 45 — `rag-specialist-content`

**Commit message:** `feat: expand question banks — practitioner-depth questions, expert tier, langchain content`

**Body:**
First content pass by the RAG Specialist. Expands all topic question banks from
5 questions to 10–15 questions each, adds expert-tier questions absent from the
current bank, and writes "why wrong" explanation fields for MCQ answers.

**Scope per topic bank:**

Current state: every topic has 5 MCQ questions, difficulty range is roughly
beginner/intermediate only, and the "why wrong" explanation fields are minimal.

Target state after this commit:
- Each topic: 10–12 MCQ questions minimum
- Difficulty tiers present: beginner (2–3), intermediate (4–5), advanced (2–3), expert (1–2)
- Every MCQ option has a "why wrong" explanation for the 3 incorrect options
- Open-ended question banks: add 3 additional questions per topic (targeting
  intermediate-to-advanced reasoning, not recall)

**Priority order (highest leverage first):**
1. `evaluation_and_metrics` — Phase 3; current questions are too recall-heavy for
   a topic that should be taught through scenario reasoning
2. `production_patterns` — Phase 3; failure modes are under-represented
3. `langchain_fundamentals` — new topic from Commit 40; needs a full bank
4. `retrieval_methods` — Phase 2; BM25 vs dense, HyDE questions are currently thin
5. `chunking_strategies` — Phase 2; real-world edge cases (tables, code, mixed) missing
6. All remaining Phase 1 and Phase 2 topics

**Quality bar per question (RAG Specialist must apply):**
- Every MCQ question must reflect a real failure mode, a production distinction, or
  a scenario that only matters when you've deployed a real RAG system
- No "what does X stand for" recall questions
- Wrong answer options must be plausible — a practitioner who hasn't deployed this
  specific pattern should be able to see why each wrong answer is tempting
- "Why wrong" explanations must explain the reasoning failure, not just restate the correct answer

**Files touched:**
- `knowledge-base/curriculum/questions/mcq/embeddings_and_similarity.md` (expand)
- `knowledge-base/curriculum/questions/mcq/rag_pipeline_architecture.md` (expand)
- `knowledge-base/curriculum/questions/mcq/chunking_strategies.md` (expand)
- `knowledge-base/curriculum/questions/mcq/vector_databases.md` (expand)
- `knowledge-base/curriculum/questions/mcq/retrieval_methods.md` (expand)
- `knowledge-base/curriculum/questions/mcq/context_and_prompting.md` (expand)
- `knowledge-base/curriculum/questions/mcq/evaluation_and_metrics.md` (expand)
- `knowledge-base/curriculum/questions/mcq/production_patterns.md` (expand)
- `knowledge-base/curriculum/questions/mcq/langchain_fundamentals.md` (expand — new from Commit 40)
- `knowledge-base/curriculum/questions/embeddings_and_similarity.md` (add 3 open-ended)
- `knowledge-base/curriculum/questions/rag_pipeline_architecture.md` (add 3 open-ended)
- `knowledge-base/curriculum/questions/chunking_strategies.md` (add 3 open-ended)
- `knowledge-base/curriculum/questions/vector_databases.md` (add 3 open-ended)
- `knowledge-base/curriculum/questions/retrieval_methods.md` (add 3 open-ended)
- `knowledge-base/curriculum/questions/context_and_prompting.md` (add 3 open-ended)
- `knowledge-base/curriculum/questions/evaluation_and_metrics.md` (add 3 open-ended)
- `knowledge-base/curriculum/questions/production_patterns.md` (add 3 open-ended)
- `knowledge-base/curriculum/questions/langchain_fundamentals.md` (expand open-ended — Commit 40 initial version)

**Depends on:** 42 (RAG Specialist persona must exist before first invocation)
**Parallel with:** 44 (no shared files — knowledge-base only)

**Scope hard limits:**
- No src/ files touched
- No curriculum-map.md, gates.md, or topic-slugs.json changes — those are Lara's
- No question removal — only additions and "why wrong" field additions to existing questions

**Testing — done when:**
- [ ] Every MCQ topic file has ≥ 10 questions
- [ ] At least 1 expert-tier question exists in each Phase 2 and Phase 3 topic
- [ ] Every MCQ option in every question has a "why wrong" explanation for incorrect options
- [ ] `langchain_fundamentals` MCQ bank has ≥ 10 questions covering LCEL, retriever interface, memory, and failure modes
- [ ] No structural format regressions (existing `_load_mcq_question` loader still parses all files)
