# RAG Specialist Worklog

## Current State Header — Session 9 (Commit 51 complete)

**Commit:** 51 — bank-expansion
**Status:** Complete — all 8 MCQ files and all 8 open question files at >=5 novice and >=5 intermediate (verified by script)
**Session count:** 9

**MCQ files modified (all 8 original topics):**
- embeddings_and_similarity: 5 novice, 5 intermediate
- rag_pipeline_architecture: 5 novice, 5 intermediate
- chunking_strategies: 5 novice, 5 intermediate
- vector_databases: 5 novice, 5 intermediate
- retrieval_methods: 5 novice, 5 intermediate
- context_and_prompting: 5 novice, 5 intermediate
- evaluation_and_metrics: 5 novice, 5 intermediate
- production_patterns: 5 novice, 5 intermediate

**Open question files modified (all 8 original topics):**
- embeddings_and_similarity: 5 novice, 5 intermediate
- rag_pipeline_architecture: 5 novice, 5 intermediate
- chunking_strategies: 5 novice (Q1, Q2, Q12, Q13, Q14), 5 intermediate (Q3, Q4, Q5, Q6 + confirmed existing)
- vector_databases: 5 novice (Q1, Q12, Q13, Q14, Q15), 5 intermediate (Q2, Q3, Q4, Q5, Q6)
- retrieval_methods: 5 novice (Q1, Q2, Q12, Q13, Q14), 5 intermediate (Q3, Q4, Q5, Q6, Q15)
- context_and_prompting: 5 novice (Q1, Q2, Q12, Q13, Q14), 5 intermediate (Q3, Q4, Q5, Q6, Q15)
- evaluation_and_metrics: 5 novice (Q1, Q2, Q12, Q13, Q14), 5 intermediate (Q3, Q4, Q5, Q6, Q15)
- production_patterns: 5 novice (Q1, Q12, Q13, Q14, Q15), 5 intermediate (Q2, Q3, Q4, Q5, Q16)

**No open blockers.**

---

## Current State Header — Session 8 (Commit 50 complete)

**Commit:** 50 — langgraph-questions
**Status:** Complete — both question banks written for langgraph_fundamentals topic
**Session count:** 8

**Files created:**
- `knowledge-base/curriculum/questions/mcq/langgraph_fundamentals.md` — 20 MCQs (5 novice, 5 intermediate, 5 advanced, 5 expert)
- `knowledge-base/curriculum/questions/langgraph_fundamentals.md` — 19 open-ended questions (5 novice, 5 intermediate, 5 advanced, 4 expert)

**Content coverage:**
- Nodes (discrete operations that read and write shared state), edges (directed connections defining execution flow), state (shared data structure passed between all nodes)
- Acyclic vs. cyclic graphs: what cycles enable (loops, self-correction, iterative refinement) vs. what sequential chains can express
- Graph compilation: structural validation (entry/exit points, node reachability, edge integrity), produces an executable artifact, does not run behavioral tests
- Conditional routing: routing functions inspect state and return the next node identifier; why this differs from in-node if-statements (visibility, separation of computation from control flow)
- Checkpointing and multi-turn memory: state persistence per thread identifier, resume from saved state on restart, frequency/granularity tradeoffs, side effect idempotency requirements
- Graph topology as capability boundary: the LLM is one node; topology determines what execution paths exist; structural enforcement vs. probabilistic prompt-based enforcement
- Fan-out and fan-in for parallel execution: both retrieval nodes connected from a common predecessor; state accumulates both results before synthesis node executes
- State schema as interface contract: field name mismatches cause silent quality degradation (None default, no exception); compile-time validation does not catch data flow gaps
- Cycle termination: iteration counter in state, hard cap in routing function, detection of non-updating state between iterations
- Expert scenarios: diagnosing always-one-branch routing (state write gap vs. routing function bug), multi-agent coordination (planner/executor patterns with separate compiled graphs), graph versioning and checkpoint migration under schema evolution, self-correction loop design with faithfulness checks

**Curriculum gap noted (flag for Lara if relevant):**
LangSmith / graph observability tooling — tracing which nodes executed, what state looked like at each step, and which routing decisions were made is referenced across multiple diagnostic questions but has no dedicated topic. Graph execution traces are the primary debugging surface for graph agents and may warrant a standalone observability topic in a future curriculum expansion.

**Format decisions:**
Followed Lara's format exactly. Zero Python syntax anywhere in either file — all questions are framed in terms of graph concepts (nodes, edges, state, routing, compilation) without any API references. Every MCQ distractor targets a named practitioner misconception. File headers include tier count summaries.

**No open blockers.**

---

## Current State Header — Session 7 (Commit 48 complete)

**Commit:** 48 — document-ingestion-questions
**Status:** Complete — both question banks written for document_ingestion topic
**Session count:** 7

**Files created:**
- `knowledge-base/curriculum/questions/mcq/document_ingestion.md` — 20 MCQs (5 novice, 5 intermediate, 5 advanced, 5 expert)
- `knowledge-base/curriculum/questions/document_ingestion.md` — 22 open-ended questions (5 novice, 6 intermediate, 6 advanced, 5 expert)

**Content coverage:**
- Document loader output (Document object, page_content, metadata)
- Loader vs. splitter division of responsibility
- Format-specific loaders (PDF, HTML, DOCX, CSV, TXT) and why a generic loader fails
- PDF extraction failures: scanned images (silent empty content), table linearization (multi-column interleaving), two-column layout spatial reordering
- HTML noise: unconfigured loaders capturing nav/footer/JS content; JavaScript-rendered pages returning empty content via HTTP fetchers
- DOCX embedded OLE objects: why Excel spreadsheets in DOCX are invisible to standard parsers
- Encoding and mojibake: UTF-8 vs. Latin-1/Windows-1252 mismatch, BOM handling (UTF-8-with-BOM producing `ï»¿`), `errors='replace'` silent corruption pattern
- Metadata propagation: loader captures vs. splitter propagation failures, required field schema enforcement
- Silent data loss vs. hard errors: post-load validation layer design, quarantine queues
- Incremental indexing: chunk ID stability (source + position vs. content-only hash), cross-document collision failure mode
- Loader upgrade migration: delete-before-insert atomicity, staged rollout, evaluation gating
- Expert scenarios: retrieval precision drop diagnosis after batch ingestion, encoding pipeline for heterogeneous enterprise corpora, metadata schema evolution in live index, tiered ingestion for latency vs. accuracy tradeoff, loader library version regression audit, end-to-end ingestion pipeline audit

**Curriculum gap noted (no action taken — flag for Lara if relevant):**
OCR pipeline design (when to invoke OCR, confidence thresholds, integration with standard PDF loader) appears across multiple questions as a referenced technique but has no dedicated topic. Currently treated as a document_ingestion subtopic, not a standalone topic. If the curriculum expands to cover computer vision inputs or document digitization workflows, a standalone OCR topic may be warranted.

**Format decisions:**
Followed Lara's format exactly. File header includes tier count summary. Every MCQ distractor has a "Why X is wrong" block identifying the specific practitioner misconception. No framework-specific API questions — all questions are concept-first and applicable to any implementation.

**No open blockers.**

---

## Current State Header — Session 6 (Commit 45 complete)

**Commit:** 45 — rag-specialist-content
**Status:** Complete — all MCQ and open-ended banks expanded
**Session count:** 6 (tool cap reached per session)

**MCQ banks (all 9) — questions before → after:**
- evaluation_and_metrics: 5 → 12
- production_patterns: 5 → 11
- langchain_fundamentals: 5 → 11
- retrieval_methods: 5 → 10
- chunking_strategies: 5 → 10
- embeddings_and_similarity: 5 → 10
- rag_pipeline_architecture: 5 → 10
- context_and_prompting: 5 → 10
- vector_databases: 5 → 10

**Open-ended banks (all 9) — 8 questions → 11 questions each**

**Curriculum gap flag — handoff to Lara:**
`langsmith_tracing` as a potential Phase 3 topic. LangSmith tracing and evaluation tooling is referenced incidentally across langchain_fundamentals, evaluation_and_metrics, and production_patterns but has no dedicated topic. A standalone topic would allow focused questions on trace anatomy, LangSmith dataset management, custom evaluator configuration, and comparing runs across experiments. This is a structural decision for Lara — I have not created any topic files.

**Format decisions:**
Followed Lara's existing format exactly. No structural deviations. "Why wrong" explanations added as inline labeled blocks under each distractor option in MCQ format.

**No open blockers.**
