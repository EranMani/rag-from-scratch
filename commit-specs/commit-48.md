# Commit 48 Spec — `document-ingestion-questions`
> **Project:** rag-from-scratch · **Assignee:** RAG Specialist · **Load only for the active commit.**
> **Note:** New commit added in replan 2026-05-23 — question bank for the new document_ingestion Phase 2 topic. Former integration-tests (old 48) renumbered to 55.

---

### Commit 48 — `document-ingestion-questions`

**Commit message:** `feat(EranMani): add question bank for document_ingestion topic (MCQ + open)`

**Body:**
Requested by Eran Mani, our team lead: write the full question bank for the `document_ingestion` Phase 2 topic. Both MCQ and open-question formats. Minimum 5 questions per difficulty tier per format.

**Assignee:** RAG Specialist (knowledge-base only — no src/ files)

**Files touched:**
- `knowledge-base/curriculum/questions/mcq/document_ingestion.md` (new)
- `knowledge-base/curriculum/questions/document_ingestion.md` (new)

**Depends on:** 47 (curriculum-restructure complete — slug is live in curriculum-map before questions are written)

**Content requirements:**

Topics to cover across all tiers:
- Document loaders: what they do, the formats they handle (PDF, HTML, DOCX, TXT, CSV, Markdown)
- Parsing challenges: PDF table extraction, HTML tag noise, DOCX embedded objects
- Encoding and character set handling (UTF-8, Latin-1, BOM markers, mojibake)
- Metadata extraction: what metadata a loader should capture and why (source URL, page number, creation date, file type)
- How document structure (headers, tables, nested sections, page breaks) propagates into chunk quality
- Loader failure modes: silent data loss vs. hard error, and how to detect each
- Format-specific gotchas: multi-column PDFs, scanned documents requiring OCR, HTML with JavaScript-rendered content

Difficulty calibration:
- **Novice**: recognition questions — name the stages, identify what a loader returns, distinguish loader from splitter
- **Intermediate**: comprehension + mechanism — explain why PDF extraction fails for tables, describe metadata importance
- **Advanced**: situational judgment — given a document type and failure symptom, diagnose the root cause
- **Expert**: multi-variable diagnosis — e.g., silent data loss that manifests as retrieval precision drop, tracing it back to a specific encoding issue in the ingestion pipeline

MCQ requirements:
- Exactly 4 options (A–D) per question
- 1 correct answer per question
- "Why X is wrong" explanation for each distractor — must identify the specific misconception, not just "because it's incorrect"
- Minimum 5 questions per tier: novice, intermediate, advanced, expert

Open question requirements:
- Rubric-based: correct answer criteria, partial credit criteria, incorrect/no-credit criteria
- Minimum 5 questions per tier: novice, intermediate, advanced
- Expert tier in open questions is optional but strongly encouraged (no expert open questions exist in most topics)

**Testing — done when:**
- [ ] `knowledge-base/curriculum/questions/mcq/document_ingestion.md` exists with ≥ 5 questions per tier (novice/intermediate/advanced/expert)
- [ ] `knowledge-base/curriculum/questions/document_ingestion.md` exists with ≥ 5 questions per tier (novice/intermediate/advanced)
- [ ] File headers include tier count summary (e.g., `# Questions: N (X novice, Y intermediate, Z advanced, W expert)`)
- [ ] Every MCQ distractor has a "Why X is wrong" explanation
- [ ] No Python API or framework-specific questions — concept-first throughout
