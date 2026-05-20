# Commit 40 Spec — `langchain-curriculum`
> **Project:** rag-from-scratch · **Assignee:** curriculum-specialist (Lara) · **Load only for the active commit.**
> **Note:** Added in replan 2026-05-20 — LangChain topic re-added as Phase 2 bridging topic (dropped in 2026-05-11 replan, restored per Team Lead: "it's the framework that combines everything together").

---

### Commit 40 — `langchain-curriculum`

**Commit message:** `feat: add langchain_fundamentals as Phase 2 bridging topic`

**Body:**
Re-adds LangChain to the curriculum — not as a tool tutorial, but as the practical
bridge from conceptual RAG knowledge to implementation. Positioned at the end of Phase 2
as the "put it all together" topic: learners who have studied chunking, vector databases,
retrieval methods, and context/prompting are now shown how those concepts connect in
a real LangChain pipeline.

This is a knowledge-base-only commit. No src/ files are touched.
Nova wires the new slug into `VALID_MODULE_SLUGS` and `PHASE_2_TOPICS` in Commit 41.

**Topic definition for `langchain_fundamentals`:**

Phase: 2 (bridging topic — after all other Phase 2 topics)
Description: Understand how LangChain connects the RAG components from Phase 2 into
an operational pipeline. Covers the chain abstraction, LCEL, retriever interfaces,
memory management, and composing a production RAG pipeline from components the learner
already understands conceptually.

Prerequisites: Phase 1 gate passed; all other Phase 2 topics recommended first.

Learning Objectives:
1. Describe the LangChain chain abstraction and LCEL pipe syntax — what `|` composes
   and what types are compatible in a chain.
2. Explain how LangChain's retriever interface wraps a vector store — what `.as_retriever()`
   returns, what parameters it accepts, and how it connects to a chain.
3. Trace a `create_retrieval_chain` call from query to response: which components are
   called in which order and what each passes to the next.
4. Explain ConversationBufferMemory and ConversationSummaryMemory — what each stores,
   when each is appropriate, and what happens when the buffer exceeds the context limit.
5. Identify at least three places where a LangChain pipeline can fail silently
   (e.g., retriever returning empty results, chain swallowing exceptions, prompt
   template variable mismatch) and describe how to surface those failures.

Typical Misconceptions:
- "LangChain is a RAG framework." (LangChain is a general LLM orchestration library.
  Understanding the concepts independently of LangChain makes you a stronger practitioner.)
- "LCEL is just Python pipes." (LCEL is a lazy evaluation graph — chains are not
  executed when composed, only when invoked. This has implications for streaming,
  async, and error handling.)
- "LangChain handles memory automatically." (Memory components must be explicitly wired —
  without it, each query has no conversation history.)

**Handoff to Nova (Commit 41):**
After this commit, Nova must add `langchain_fundamentals` to:
- `VALID_MODULE_SLUGS` in `src/agents/state.py`
- `PHASE_2_TOPICS` in `src/app/profile/scoring.py`
- `_ORDERED_SLUGS` in `src/agents/nodes/assess.py` (at end of Phase 2 block)

**Files touched:**
- `knowledge-base/curriculum/curriculum-map.md` — add langchain_fundamentals topic entry
- `knowledge-base/curriculum/topic-slugs.json` — add `"langchain_fundamentals"` to array
- `knowledge-base/curriculum/gates.md` — update Phase 2 required topics list to include langchain_fundamentals
- `knowledge-base/curriculum/questions/langchain_fundamentals.md` — new open-ended question bank (5 questions with rubrics)
- `knowledge-base/curriculum/questions/mcq/langchain_fundamentals.md` — new MCQ question bank (5 questions, difficulty stratified)

**Depends on:** 38.5
**Parallel with:** 39 (no shared files — knowledge-base only, no src/ overlap)

**Testing — done when:**
- [ ] `topic-slugs.json` is valid JSON and contains `"langchain_fundamentals"`
- [ ] `curriculum-map.md` Phase 2 section includes the new topic with full spec
- [ ] Both question bank files exist and follow the established format
- [ ] `gates.md` Phase 2 gate rule lists langchain_fundamentals as required
- [ ] Handoff note for Nova is explicit in Lara's worklog
