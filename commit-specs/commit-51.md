# Commit 51 Spec — `bank-expansion`
> **Project:** rag-from-scratch · **Assignee:** RAG Specialist · **Load only for the active commit.**
> **Note:** New commit added in replan 2026-05-23 — expand novice and intermediate question tiers to minimum depth across all 8 original topics.

---

### Commit 51 — `bank-expansion`

**Commit message:** `feat(EranMani): expand novice and intermediate question tiers to 5/tier across original 8 topics`

**Body:**
Requested by Eran Mani, our team lead: current bank has 1–2 novice questions per topic — repetition is guaranteed within 2–3 sessions. Expand to a minimum of 5 questions per tier for both novice and intermediate tiers, across all 8 original topics. This is pure content addition — no existing questions are modified or removed.

**Assignee:** RAG Specialist (knowledge-base only — no src/ files)

**Files touched (all additions, no modifications to existing questions):**
- `knowledge-base/curriculum/questions/mcq/embeddings_and_similarity.md`
- `knowledge-base/curriculum/questions/mcq/rag_pipeline_architecture.md`
- `knowledge-base/curriculum/questions/mcq/chunking_strategies.md`
- `knowledge-base/curriculum/questions/mcq/vector_databases.md`
- `knowledge-base/curriculum/questions/mcq/retrieval_methods.md`
- `knowledge-base/curriculum/questions/mcq/context_and_prompting.md`
- `knowledge-base/curriculum/questions/mcq/evaluation_and_metrics.md`
- `knowledge-base/curriculum/questions/mcq/production_patterns.md`
- `knowledge-base/curriculum/questions/embeddings_and_similarity.md`
- `knowledge-base/curriculum/questions/rag_pipeline_architecture.md`
- `knowledge-base/curriculum/questions/chunking_strategies.md`
- `knowledge-base/curriculum/questions/vector_databases.md`
- `knowledge-base/curriculum/questions/retrieval_methods.md`
- `knowledge-base/curriculum/questions/context_and_prompting.md`
- `knowledge-base/curriculum/questions/evaluation_and_metrics.md`
- `knowledge-base/curriculum/questions/production_patterns.md`

**Depends on:** 50 (all new topic banks complete — document_ingestion and langgraph_fundamentals already at target depth; skip those)

**Scope boundary:**
- Target topics: the 8 original topics listed above only
- Do NOT touch: `document_ingestion` (written fresh at depth in C48), `langgraph_fundamentals` (written fresh at depth in C50)
- Do NOT modify existing questions — append only
- Tiers to expand: novice and intermediate only (advanced and expert are adequately stocked per Lara's audit)
- MCQ and open question banks both need expansion

**Quality requirements (RAG Specialist self-check before committing):**
- Novice questions must test recognition and identification — not mechanism or application
- Novice MCQ distractors must be wrong for the reason a true beginner would choose them, not a practitioner who partially understands
- Intermediate questions must test mechanism and comprehension — not recall, not multi-variable diagnosis
- All new MCQs must have "Why X is wrong" explanations targeting a specific named misconception (not "because it's incorrect")
- New questions must not duplicate the conceptual coverage of existing questions — they should probe different aspects of the same topic

**Testing — done when:**
- [ ] All 8 MCQ files: novice tier has ≥ 5 questions
- [ ] All 8 MCQ files: intermediate tier has ≥ 5 questions
- [ ] All 8 open question files: novice tier has ≥ 5 questions
- [ ] All 8 open question files: intermediate tier has ≥ 5 questions
- [ ] No existing questions removed or modified
- [ ] All new MCQ distractors have "Why X is wrong" explanations
