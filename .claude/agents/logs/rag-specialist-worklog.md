# RAG Specialist Worklog

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
