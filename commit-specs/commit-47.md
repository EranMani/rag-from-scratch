# Commit 47 Spec — `curriculum-restructure`
> **Project:** rag-from-scratch · **Assignee:** Lara · **Load only for the active commit.**
> **Note:** New commit added in replan 2026-05-23 — replaces langchain_fundamentals with document_ingestion in the Phase 2 curriculum. Former aws-ec2-deployment (old 47) renumbered to 54.

---

### Commit 47 — `curriculum-restructure`

**Commit message:** `feat(EranMani): replace langchain_fundamentals with document_ingestion in Phase 2 curriculum`

**Body:**
Requested by Eran Mani, our team lead: `langchain_fundamentals` is removed from the active Phase 2 curriculum and replaced with `document_ingestion`. Rationale: the app is "rag-from-scratch" — a dedicated LangChain API slot conflicts with the concept-first identity. Document ingestion is the actual "from scratch" starting point that was absent. LangChain question files are archived, not deleted.

**Assignee:** Lara (knowledge-base only — no src/ files)

**Files touched:**
- `knowledge-base/curriculum/curriculum-map.md` — replace langchain_fundamentals entry with document_ingestion in Phase 2
- `knowledge-base/curriculum/gates.md` — replace langchain_fundamentals with document_ingestion in Phase 2 gate requirements
- `knowledge-base/curriculum/questions/archive/langchain_fundamentals.md` (new — archived)
- `knowledge-base/curriculum/questions/archive/mcq/langchain_fundamentals.md` (new — archived)

**Depends on:** 46 (mastery-matched routing stable before curriculum changes)

**document_ingestion topic spec (for curriculum-map.md):**
- **Phase:** 2
- **Description:** Understand how raw documents flow into a RAG pipeline — format parsing (PDF, HTML, DOCX, TXT, CSV), metadata extraction, encoding handling, and how document structure affects downstream chunking quality. This topic is the practical entry point for building any real RAG system.
- **Prerequisites:** Phase 1 gate passed; `rag_pipeline_architecture` (document loading occurs in the indexing phase)
- **Learning objectives:**
  1. Identify the components of a document loader and explain what each extracts (text, metadata, structure)
  2. Describe at least three format-specific parsing challenges (e.g., PDF table extraction, HTML tag noise, DOCX embedded images) and their mitigations
  3. Explain how encoding issues (UTF-8 vs. Latin-1, BOM markers) cause silent data loss in ingestion pipelines
  4. Trace how a document's structural elements (headers, tables, page breaks) affect chunking quality downstream
  5. Describe two loader failure modes — silent data loss vs. hard error — and how to detect each in a production pipeline
- **Typical misconceptions:**
  - "Any text extracted from a PDF is correct." (PDF text extraction is lossy — tables, multi-column layouts, and scanned pages require special handling.)
  - "Metadata doesn't matter for retrieval." (Source, page number, and timestamp metadata are critical for filtering, citation, and index freshness tracking.)
  - "A document loader and a text splitter do the same job." (The loader extracts raw content; the splitter decides how to partition it — they are separate pipeline stages with different failure modes.)

**Testing — done when:**
- [ ] `curriculum-map.md` no longer references `langchain_fundamentals` in Phase 2
- [ ] `curriculum-map.md` contains a complete `document_ingestion` entry with all required sections
- [ ] `gates.md` Phase 2 gate references `document_ingestion` (not `langchain_fundamentals`)
- [ ] Archived langchain question files exist at `knowledge-base/curriculum/questions/archive/`
- [ ] No `src/` files touched
