# Question Bank: `document_ingestion`
# Phase: 2 — Core Components
# Maintained by: RAG Specialist
# Last updated: 2026-05-23 (Commit 48)
# Questions: 22 (5 novice, 6 intermediate, 6 advanced, 5 expert)

---

## Q1 — What a document loader produces

**Difficulty:** novice

**Question:**
Describe what a document loader returns. What fields does a typical Document object contain, and why does each field matter for downstream RAG pipeline stages?

**Correct answer criteria:**
- A document loader returns a list of Document objects (or equivalent structures)
- Each Document object contains `page_content`: the raw text extracted from the source
- Each Document object contains `metadata`: a dictionary of structured fields such as source path, page number, file type, and creation date
- `page_content` matters because it is the text that gets split, embedded, and retrieved
- `metadata` matters because it enables source citation, filtered retrieval, and post-retrieval provenance tracking

**Partial credit criteria:**
- Correctly identifies that a loader returns text content but cannot name or explain the metadata component
- Mentions metadata but cannot articulate why it matters for retrieval or citation

**Incorrect / no-credit criteria:**
- States that a loader returns embedding vectors (confuses loader stage with embedding stage)
- States that a loader returns plain strings with no associated metadata
- Cannot distinguish what a loader does from what a text splitter does

---

## Q2 — Loader vs. splitter responsibility

**Difficulty:** novice

**Question:**
A junior developer says: "The document loader is responsible for breaking the document into small pieces for embedding." Identify the error in this statement and describe the correct division of responsibility between a loader and a text splitter.

**Correct answer criteria:**
- The error: splitting into small pieces is the text splitter's job, not the loader's job
- A loader's responsibility: reading the source file or URL, parsing its format (PDF, HTML, DOCX, etc.), and returning one or more Document objects with page_content and metadata intact
- A text splitter's responsibility: taking those Document objects and dividing their page_content into smaller, embedding-ready chunks while propagating metadata to each chunk
- The two components operate sequentially: loader first, splitter second

**Partial credit criteria:**
- Identifies that the statement is wrong but cannot articulate what the loader actually does
- Correctly describes one component but conflates the other

**Incorrect / no-credit criteria:**
- Agrees that the loader splits documents
- Cannot name the component that does perform splitting
- Describes both as doing the same thing

---

## Q3 — Why source metadata matters

**Difficulty:** novice

**Question:**
A RAG system returns a correct answer to a user's question but cannot tell the user which document the answer came from. What metadata field was likely missing, and what downstream capabilities does this absence prevent?

**Correct answer criteria:**
- The missing field is the source path or source URL — the provenance identifier that links a chunk back to its origin document
- Downstream capabilities prevented: source citation in responses, linking users to the original document for verification, auditing which documents contributed to an answer, filtering retrieval by document source
- The absence is a loader-stage failure — if the loader does not capture source when creating the Document object, it cannot be added later without re-ingesting

**Partial credit criteria:**
- Identifies that source information is missing but cannot name it as a specific metadata field
- Names the field correctly but can only articulate one downstream impact

**Incorrect / no-credit criteria:**
- Blames the embedding model or vector database for the missing citation capability
- States that page_content should contain the source (not metadata)
- Cannot connect the missing metadata to a specific loader design decision

---

## Q4 — Identifying a scanned PDF

**Difficulty:** novice

**Question:**
A developer runs a PDF loader on a batch of 200 documents. Fifty of them return Document objects with empty or near-empty page_content but no exceptions. What is the most likely explanation, and how would you confirm it?

**Correct answer criteria:**
- Most likely explanation: the 50 documents are scanned image PDFs — they contain images of text rather than machine-readable text, so the PDF text extractor finds nothing to extract
- Confirmation method: open one of the affected PDFs in a viewer and attempt to select or copy text — if selection is impossible, the document is image-only; alternatively, inspect the PDF binary for the presence of text stream objects
- Correct fix: apply OCR (optical character recognition) processing to those documents before or during ingestion to recover the text content
- The pattern is silent data loss: the loader succeeded (no exception) but returned no usable content

**Partial credit criteria:**
- Identifies that the PDFs are image-based but cannot explain why standard loaders fail on them
- Proposes OCR but cannot explain how to confirm which documents need it

**Incorrect / no-credit criteria:**
- Attributes the empty content to a loader bug or configuration error without considering document format
- States that all PDFs should produce content and the empty result indicates file corruption
- Proposes increasing chunk size as a solution

---

## Q5 — Format-appropriate loader selection

**Difficulty:** novice

**Question:**
A corpus contains files with extensions `.pdf`, `.docx`, `.html`, `.csv`, and `.txt`. Explain why a single generic text loader is insufficient for this corpus, and describe the correct approach for format-specific loading.

**Correct answer criteria:**
- Each format has distinct structure that a generic text reader cannot parse: PDFs have binary-encoded pages, DOCX files are ZIP archives with XML, HTML has tag-based markup, CSV has delimited rows and columns
- A generic text reader applied to a PDF or DOCX binary will produce garbled content or fail entirely
- The correct approach: use format-specific loaders (PDF parser for .pdf, DOCX parser for .docx, HTML parser for .html, CSV parser for .csv, text reader for .txt) and route each file to the appropriate loader based on its extension or MIME type
- A directory loader with extension-to-loader mapping is a practical implementation pattern

**Partial credit criteria:**
- Correctly argues that a generic loader is insufficient but can only give one example of why
- Describes format-specific loaders but cannot explain the routing mechanism

**Incorrect / no-credit criteria:**
- Claims a generic text reader can handle all formats if the files are named correctly
- Proposes converting all files to plain text before ingestion without acknowledging the loss of structure and metadata
- Cannot explain what makes each format distinct from plain text

---

## Q6 — PDF table extraction failure

**Difficulty:** intermediate

**Question:**
A RAG system ingests financial reports in PDF format. Users querying for specific revenue figures consistently retrieve chunks with correct surrounding text but garbled or missing numeric data. Explain the mechanism that causes this, and describe two approaches to address it.

**Correct answer criteria:**
- Mechanism: standard PDF text extraction reads character positions in page-order (top to bottom, left to right), linearizing multi-column table structures. Table cells that appear at the same vertical position on the page interleave in the extracted stream, breaking row and column relationships
- Approach 1: use a layout-aware PDF extraction library that identifies table bounding boxes and reconstructs row/column structure from spatial coordinates before returning text
- Approach 2: detect table regions during extraction and convert them to a structured format (e.g., Markdown table representation) that preserves relational context in the chunk
- The failure is at the extraction stage — downstream components (splitter, embedder, retriever) receive already-corrupted content and cannot recover the structure

**Partial credit criteria:**
- Correctly identifies that extraction order causes the problem but cannot explain the spatial mechanism
- Proposes layout-aware extraction but cannot explain why standard extraction fails
- Can identify the failure mode but only proposes one corrective approach

**Incorrect / no-credit criteria:**
- Attributes the garbled numbers to the embedding model or vector database
- Proposes increasing chunk size as the primary fix
- States that PDFs cannot contain retrievable table data

---

## Q7 — HTML noise in ingested content

**Difficulty:** intermediate

**Question:**
An HTML loader is ingesting product documentation pages. Retrieved chunks frequently contain navigation menu text, footer boilerplate, and cookie consent UI strings alongside the actual documentation content. Describe the root cause and the correct loader configuration or preprocessing steps to address it.

**Correct answer criteria:**
- Root cause: an unconfigured HTML loader converts the entire HTML document to text, including all rendered elements — navigation, footers, scripts, ads, and consent banners receive the same treatment as main content
- Correct approach 1: configure the loader to extract only specific CSS selectors or HTML elements (e.g., `<main>`, `<article>`, specific `class` or `id` attributes that contain content)
- Correct approach 2: apply a content extraction heuristic (e.g., readability-style algorithms) to identify and isolate the main content block before returning page_content
- Correct approach 3: strip known noise tags (script, style, nav, footer, aside) before text conversion
- The fix must happen at load time — once noise is embedded in page_content, it cannot be removed without re-ingestion

**Partial credit criteria:**
- Identifies that unconfigured HTML loading includes all content but proposes fixing it at the retrieval stage rather than the ingestion stage
- Proposes CSS selector targeting but cannot explain readability heuristics or tag stripping as alternatives

**Incorrect / no-credit criteria:**
- Proposes training the embedding model on clean documentation text to make it ignore navigation content
- States that the retriever should filter out chunks containing navigation words
- Cannot explain why the noise appears in page_content in the first place

---

## Q8 — Encoding detection and mojibake

**Difficulty:** intermediate

**Question:**
A legacy document corpus was created by regional offices across different countries over a decade. When ingested, approximately 15% of files produce output containing `Ã©`, `â€™`, and similar character sequences instead of accented letters and curly quotes. Explain what has happened at the byte level, and describe a robust encoding handling strategy for a production ingestion pipeline.

**Correct answer criteria:**
- What happened: the affected files are encoded in Latin-1 (ISO-8859-1) or Windows-1252, but the loader is reading them as UTF-8. Single bytes in Latin-1 that represent accented characters (e.g., `0xE9` for `é`) are being misinterpreted as the first byte of a multi-byte UTF-8 sequence, producing mojibake
- Robust strategy step 1: use an encoding detection library (chardet or charset-normalizer) to detect the actual encoding of each file before opening it
- Robust strategy step 2: open files with the detected encoding explicitly; treat detection confidence below a threshold (e.g., 70%) as an alert requiring manual review
- Robust strategy step 3: add a post-load validation step that flags chunks containing high proportions of replacement characters (`U+FFFD`) or known mojibake sequences, and quarantine them for re-processing
- Never use `errors='replace'` as the primary strategy — it converts hard failures into silent corruption

**Partial credit criteria:**
- Correctly identifies the encoding mismatch as the cause but proposes only `errors='ignore'` or `errors='replace'` as the fix
- Identifies encoding detection as the solution but cannot describe a validation step or explain when detection fails

**Incorrect / no-credit criteria:**
- Attributes the garbled characters to PDF parsing issues (confuses text file encoding with PDF extraction)
- Proposes re-saving all files as UTF-8 without addressing the detection problem for existing files
- States that the embedding model should handle mixed-encoding input

---

## Q9 — Metadata propagation through splitting

**Difficulty:** intermediate

**Question:**
A loader correctly captures `source`, `page_number`, and `ingestion_timestamp` for every document. After text splitting, a developer runs a spot check and finds that 40% of chunks have only `source` in their metadata and are missing `page_number` and `ingestion_timestamp`. Describe the two most likely causes and how you would diagnose which one is responsible.

**Correct answer criteria:**
- Likely cause 1: the text splitter is not configured to copy all metadata fields from the parent Document to child chunks — some splitters require explicit metadata fields to be listed for propagation, and the default may only propagate a subset
- Likely cause 2: the documents with missing metadata were loaded by a different loader code path (e.g., a fallback loader for a different file type) that only populates `source` and not the other fields — the 40% may correspond to a specific file format or directory
- Diagnosis step 1: check whether the 40% corresponds to a specific document type, date range, or directory — if yes, the cause is likely a different loader code path
- Diagnosis step 2: inspect the splitter configuration and test it on a single Document object with all three metadata fields — if the child chunks lose fields, the cause is splitter configuration
- The fix depends on the cause: update loader code path to capture missing fields, or update splitter configuration to propagate all metadata

**Partial credit criteria:**
- Identifies one cause correctly but not both
- Correctly diagnoses the cause without proposing a fix

**Incorrect / no-credit criteria:**
- Attributes missing metadata to the vector database stripping fields during upsert
- Proposes adding metadata post-retrieval rather than fixing the ingestion stage
- Cannot distinguish between a loader-side and splitter-side root cause

---

## Q10 — JavaScript-rendered page ingestion

**Difficulty:** intermediate

**Question:**
A team is building a RAG system over a competitor's public API documentation site. Their HTML loader returns Document objects with nearly empty page_content, even though the pages are content-rich when viewed in a browser. Explain the technical reason for this failure and describe the correct ingestion approach.

**Correct answer criteria:**
- Technical reason: the documentation site uses a JavaScript rendering framework (React, Vue, Next.js, etc.). When an HTTP request fetches the page, the server responds with a minimal HTML shell. The actual content is injected into the DOM by JavaScript running in the browser. An HTTP-based HTML loader never executes JavaScript, so it only receives and parses the empty shell
- Correct approach: use a headless browser loader that launches a real browser engine (e.g., via Playwright or Puppeteer), loads the page, waits for JavaScript execution and DOM population, and then extracts the rendered HTML
- Trade-offs of headless browsing: significantly slower than HTTP fetching (seconds per page vs. milliseconds), requires browser installation in the ingestion environment, and is sensitive to dynamic content loading timing (may require explicit wait conditions)

**Partial credit criteria:**
- Correctly identifies JavaScript rendering as the cause but proposes HTTP request header changes (user-agent spoofing) as the fix
- Identifies headless browser as the solution but cannot explain why it succeeds where HTTP fetching fails

**Incorrect / no-credit criteria:**
- Attributes the empty content to HTTPS restrictions or CORS policies
- Proposes using a more powerful embedding model to recover content from empty strings
- Cannot explain the difference between server-rendered and client-rendered HTML

---

## Q11 — Post-load content validation

**Difficulty:** intermediate

**Question:**
A production ingestion pipeline processes 10,000 documents per batch. Describe a post-load validation layer that catches the three most common loader failure modes before those documents enter the vector database.

**Correct answer criteria:**
- Failure mode 1 (empty content): check that `len(doc.page_content.strip()) > minimum_threshold` for each Document; quarantine documents below the threshold for manual review or OCR fallback — catches scanned PDFs and JavaScript-rendered pages
- Failure mode 2 (encoding corruption): check for a high proportion of Unicode replacement characters (`U+FFFD`) or known mojibake sequences in page_content; quarantine documents exceeding a corruption rate threshold — catches encoding mismatch cases
- Failure mode 3 (missing required metadata): verify that all required metadata keys are present and non-empty for each Document; quarantine documents with missing fields — catches loader configuration gaps and format-specific loader failures
- The validation layer should produce a report: total documents, quarantine count per failure mode, and document identifiers for quarantined items
- Quarantined documents should not enter the vector database — they should go to a separate queue for human review or re-processing

**Partial credit criteria:**
- Describes two of the three failure modes with appropriate detection logic
- Describes all three failure modes but proposes logging-only (no quarantine or re-processing path)

**Incorrect / no-credit criteria:**
- Proposes catching exceptions only (misses silent failure modes that do not raise exceptions)
- Describes validation at query time rather than at ingestion time
- Cannot identify more than one failure mode

---

## Q12 — Multi-column PDF layout handling

**Difficulty:** advanced

**Question:**
A legal document corpus contains contracts formatted in two columns per page. When ingested with a standard PDF loader and retrieved, chunks frequently contain text from both columns interleaved — e.g., a sentence from the left column followed by a sentence from the right column that was at the same page height. Trace the failure to its root cause in the extraction process, and describe the minimum change required to fix it.

**Correct answer criteria:**
- Root cause: standard PDF text extraction reads character objects from the PDF content stream in positional order. In a two-column layout, characters from both columns are scattered across the page at overlapping y-coordinate ranges. The extractor sequences them by y-coordinate and then x-coordinate, causing left-column and right-column text at the same page height to interleave in the output stream
- The failure occurs at extraction time, before the splitter runs — the interleaving is already in page_content when the Document object is created
- Minimum fix: use a layout-aware PDF extraction library that explicitly identifies column boundaries (e.g., by clustering text elements into vertical bands) and processes each column as a separate text stream before concatenating
- A more complete fix segments each column independently and creates one content block per column per page, preserving reading order within each column
- Testing the fix requires visual comparison of extracted text against the original document, not just absence of exceptions

**Partial credit criteria:**
- Correctly identifies the positional extraction order as the cause but proposes reducing chunk size as the fix (which does not address the interleaving)
- Proposes a layout-aware extractor but cannot explain why standard extraction fails

**Incorrect / no-credit criteria:**
- Attributes the interleaving to the text splitter crossing column boundaries
- Proposes post-retrieval reranking to restore column order
- States that two-column PDFs cannot be correctly ingested

---

## Q13 — Silent data loss detection strategy

**Difficulty:** advanced

**Question:**
A document corpus is updated weekly with 500 new documents. Over six months, user-reported answer quality for a specific domain degrades noticeably, but RAGAS scores do not drop significantly. Investigation reveals that 200 of the domain's documents were scanned PDFs that produced empty page_content at ingestion time. The pipeline never raised an exception. Design a monitoring strategy that would have caught this failure within one week of it first occurring.

**Correct answer criteria:**
- Detection signal 1: track `empty_content_rate` per batch — the percentage of ingested Documents with `len(page_content.strip()) < threshold`. Alert if this exceeds a baseline (e.g., 1% per batch)
- Detection signal 2: track `avg_content_length` per batch by file format. A sudden drop in average content length for PDF documents in a batch signals a new pattern of extraction failures
- Detection signal 3: track domain coverage — the number of indexed chunks per known topic or document category. A batch that adds 200 PDFs but contributes near-zero chunks to a domain is anomalous
- Why RAGAS did not catch it: RAGAS measures quality of retrieval for test queries. If the test queries do not specifically target the 200 missing documents, RAGAS scores remain stable even while coverage degrades. Ingestion-side monitoring is needed in addition to retrieval-side evaluation
- The monitoring should run per-batch at ingestion time, not just during periodic evaluation runs

**Partial credit criteria:**
- Proposes one monitoring signal that would catch the failure but not two or more
- Correctly identifies why RAGAS did not surface the problem but cannot propose a monitoring approach

**Incorrect / no-credit criteria:**
- Proposes increasing RAGAS evaluation frequency as the primary fix (does not address why RAGAS misses it)
- Proposes user feedback collection as the only monitoring strategy
- Cannot explain why empty page_content is not caught by exception monitoring

---

## Q14 — DOCX embedded object extraction

**Difficulty:** advanced

**Question:**
A compliance documentation system ingests DOCX files. Several documents contain embedded Excel tables with regulatory data. At query time, users cannot retrieve specific compliance figures that exist only in those embedded tables. Explain why standard DOCX loaders miss this content, describe how you would detect it, and propose a production-ready extraction strategy.

**Correct answer criteria:**
- Why it is missed: DOCX files are ZIP archives containing XML for text content and relationships. Embedded Excel spreadsheets are stored as OLE (Object Linking and Embedding) binary objects inside the ZIP — separate from the XML text content. Standard DOCX text parsers read only the XML text stream and do not attempt to parse embedded binary objects
- Detection: inspect the DOCX ZIP archive's relationship files (`_rels/`) for entries pointing to embedded objects; the presence of `oleObject` entries confirms embedded OLE content; alternatively, check whether extracted page_content is suspiciously short compared to the document's visual complexity
- Production extraction strategy: after loading the DOCX text, inspect the archive for embedded OLE objects; extract each embedded object as a binary blob; identify its type (e.g., Excel) and route it to the appropriate secondary loader (spreadsheet parser); merge the extracted table content back into the Document's page_content with structural markers indicating table boundaries and their source location within the document
- Trade-off: this adds pipeline complexity and latency; an alternative is to flag documents with embedded objects for manual preprocessing (export tables to standalone CSV files) before ingestion

**Partial credit criteria:**
- Correctly identifies that OLE embedded objects are not parsed by standard loaders but cannot describe a detection or extraction approach
- Proposes a detection approach but cannot describe a production extraction strategy

**Incorrect / no-credit criteria:**
- Attributes missing table content to text splitter truncation
- Proposes embedding the Excel spreadsheet separately as a standalone document without addressing how to identify which DOCX files contain embedded objects
- States that embedded objects in DOCX files cannot be extracted programmatically

---

## Q15 — Incremental ingestion and chunk ID stability

**Difficulty:** advanced

**Question:**
A production RAG system re-indexes updated documents nightly. The team wants to avoid re-embedding documents that have not changed. Describe a chunk ID scheme that supports stable incremental indexing, and identify two failure modes that an unstable ID scheme would introduce.

**Correct answer criteria:**
- Stable chunk ID scheme: construct the ID as a deterministic hash of (source_identifier + chunk_position_or_sequence_number). The source_identifier is a stable document identifier (canonical file path, document UUID, or document-level content hash). The chunk position ensures uniqueness within a document even when text is identical across chunks
- Why content-only hashing fails: identical text appearing in multiple documents (boilerplate, repeated disclaimers) produces the same ID, causing cross-document collisions where one document's chunk silently overwrites another
- Failure mode 1 (cross-document collision): updating a disclaimer in document B overwrites document A's disclaimer chunk in the index because they share the same content hash ID. Document A's chunk now contains document B's updated text with document A's metadata — a provenance corruption
- Failure mode 2 (false skip): a chunk whose text was updated but whose ID is based on old metadata (e.g., just file path without content change detection) is not detected as changed and is never re-indexed. The index contains stale content that serves outdated answers
- The stable scheme requires a two-layer change detection: document-level (has the source document changed?) and chunk-level (which chunks within the document changed?)

**Partial credit criteria:**
- Describes a stable ID scheme but cannot identify both failure modes
- Identifies both failure modes but cannot describe the ID scheme that prevents them

**Incorrect / no-credit criteria:**
- Proposes using the vector database's auto-generated UUIDs as chunk IDs (prevents stable incremental indexing — new IDs are generated on every ingestion run)
- Suggests re-indexing all documents on every run as an equivalent alternative (defeats the purpose of incremental indexing at scale)
- Cannot explain why content-only hashing is insufficient

---

## Q16 — Loader upgrade migration strategy

**Difficulty:** advanced

**Question:**
A team is upgrading their PDF loader from a basic text extractor to a layout-aware extractor that correctly handles tables, multi-column text, and headers. The upgrade will change the extracted content for approximately 30% of the corpus. Describe the migration strategy to roll this out without degrading retrieval quality during the transition.

**Correct answer criteria:**
- Step 1 (scope assessment): identify which documents are affected by running both loaders on a representative sample and comparing output — quantify the proportion of the corpus that will change
- Step 2 (staged rollout): do not upgrade the entire corpus at once; begin with a subset of lower-risk documents to validate that the new loader improves rather than degrades content quality
- Step 3 (atomic document replacement): for each affected document, delete all existing chunks (by source identifier) before inserting new chunks from the upgraded loader — never upsert new alongside old, as this creates dual-version contamination
- Step 4 (evaluation gate): after each batch, run retrieval evaluation on queries known to cover the updated documents; confirm that precision improves or holds before continuing to the next batch
- Step 5 (rollback plan): maintain the ability to revert to old chunks by keeping a snapshot of affected document IDs and their old vectors until the upgrade is fully validated
- The migration must be atomic per document: no document should have a mix of old-loader and new-loader chunks in the index simultaneously

**Partial credit criteria:**
- Describes atomic document replacement but skips evaluation gating between batches
- Describes evaluation gating but does not address the delete-before-insert requirement

**Incorrect / no-credit criteria:**
- Proposes upsert-only migration (adding new chunks without removing old ones)
- Proposes re-indexing the entire corpus in one batch without staged rollout
- Cannot explain why document-level atomicity is required

---

## Q17 — Diagnosing a retrieval precision drop after ingestion batch

**Difficulty:** expert

**Question:**
A production RAG system processes a weekly ingestion batch of 3,000 new documents. After this week's batch, RAGAS context_precision drops from 0.81 to 0.58. Exception logs are clean. Describe a systematic, step-by-step diagnostic procedure to identify the root cause, and for each step, specify what finding would confirm or rule out that step's hypothesis.

**Correct answer criteria:**
- Step 1 (scope isolation): run RAGAS on the original corpus (excluding new documents) using the same evaluation set. If precision recovers to 0.81, the problem is confined to the new batch. Confirms: new documents introduced the degradation. Rules out: model or configuration regression.
- Step 2 (content quality audit): inspect the new batch's Documents for empty page_content, high replacement character rates, abnormal content lengths, and missing metadata. If 10%+ of new documents show quality issues, the loader is the primary suspect. Confirms: ingestion-stage failure. Rules out: retrieval configuration issue.
- Step 3 (format distribution check): compare the file format distribution of this week's batch against prior weeks. A new format (e.g., first batch of scanned PDFs, or files with a new encoding) would explain a sudden quality drop. Confirms: format-specific loader failure. Rules out: random quality variation.
- Step 4 (embedding space inspection): sample 20 chunks from the new batch and examine their embedding vectors for anomalies (near-zero vectors, vectors that cluster far from the rest of the corpus). Near-zero vectors confirm embedding of empty or meaningless content. Confirms: embedding-stage receiving bad content. Rules out: retrieval parameter change needed.
- Step 5 (dual-version check): verify that no documents in the new batch also have old chunks in the index (from a previous ingestion run without deletion). If duplicates exist, retrieval is returning both old and new versions inconsistently. Confirms: migration procedure gap. Rules out: content quality issue.
- The correct order: cheapest and most direct first (scope isolation, then content audit). Do not adjust retrieval parameters until the root cause is confirmed.

**Partial credit criteria:**
- Describes 3 of the 5 steps with correct confirm/rule-out framing
- Describes all 5 steps without the confirm/rule-out framework (demonstrates diagnostic thinking but not operational rigor)

**Incorrect / no-credit criteria:**
- Proposes adjusting top-k or reranker thresholds as a first step
- Begins with embedding model rollback before any content inspection
- Cannot distinguish between a loader-side, splitter-side, and retrieval-side root cause

---

## Q18 — Encoding pipeline for heterogeneous corpus

**Difficulty:** expert

**Question:**
An enterprise ingestion pipeline must handle documents from 12 regional offices, each with different historical encoding practices. Files arrive in UTF-8, UTF-16 LE with BOM, Latin-1, Windows-1252, and occasionally CP932 (Japanese Shift-JIS variant). Design the encoding detection and handling layer of this pipeline, including how to handle detection failures and how to monitor encoding health in production.

**Correct answer criteria:**
- Detection: apply charset-normalizer or chardet to each file before opening; record the detected encoding and confidence score as metadata fields on the Document object
- Opening strategy: open with detected encoding; for confidence below 0.75, flag the document for secondary review rather than proceeding with low-confidence detection
- BOM handling: UTF-16 LE files with BOM must be opened with `utf-16` or `utf-16-le` encoding (Python's `utf-16` codec auto-detects BOM); UTF-8 files with BOM must be opened with `utf-8-sig` to strip the BOM from content
- Detection failure handling: for files where detection confidence is below threshold, do not silently fall back to UTF-8 — quarantine the file, log the source identifier and detected encoding with confidence, and route to a manual review queue; regional office can be contacted for encoding specification
- Post-load validation: check each Document's page_content for a high ratio of `U+FFFD` replacement characters (>0.5% suggests encoding error); re-quarantine and flag
- Production monitoring metrics: track `encoding_detection_confidence_p10` per batch (10th percentile confidence), `encoding_error_rate` (fraction of documents with >0.5% replacement characters), and `quarantine_rate` per regional office; alert on regression

**Partial credit criteria:**
- Describes detection and opening strategy correctly but omits BOM-specific handling
- Describes post-load validation but cannot specify production monitoring metrics

**Incorrect / no-credit criteria:**
- Proposes `errors='replace'` as the primary strategy
- Cannot explain the difference between UTF-8, UTF-8-with-BOM, and UTF-16 LE handling
- Treats all encoding failures as hard errors rather than proposing a quarantine workflow

---

## Q19 — Metadata schema evolution in a live index

**Difficulty:** expert

**Question:**
A RAG system has been in production for 8 months with 500,000 indexed documents. The team adds a new required metadata field `doc_category` to support filtered retrieval. New documents capture this field. But 500,000 legacy documents are missing it, and filters on `doc_category` silently exclude them from results. Describe the full strategy to close this gap, including the migration approach, the risk of a naive re-ingestion, and how to validate that migration is complete.

**Correct answer criteria:**
- Migration approach: re-ingest legacy documents through the updated loader (which now captures `doc_category`), then upsert only the metadata for existing vector database entries if the platform supports metadata-only updates; if not, delete and re-insert the full document chunks with updated metadata
- Risk of naive re-ingestion (batch everything at once): if 500,000 documents are deleted and re-ingested in a single operation, the index is effectively unavailable (or severely degraded) during the migration window; retrieval fails or returns incomplete results for hours; the risk is complete service degradation
- Preferred approach: incremental batch migration — process documents in batches of 5,000–10,000, updating metadata atomically per document (delete old chunks, insert new chunks with `doc_category`), maintaining the rest of the index as live throughout
- Validation step 1: after migration, run a query that counts documents with `doc_category` present vs. absent; the absent count should be zero
- Validation step 2: run a filtered retrieval query on each known `doc_category` value and verify that results count matches the expected number of documents in each category
- Validation step 3: compare RAGAS context_precision for filtered queries before and after migration to confirm the new field does not degrade retrieval quality
- The migration must not result in a mixed-state index where some documents have the field and some do not — implement a circuit breaker that pauses ingestion of net-new documents until migration is complete if the category-filtered search is business-critical

**Partial credit criteria:**
- Describes incremental batching correctly but omits validation steps
- Describes all three validation steps but proposes naive full-corpus re-ingestion without addressing service availability risk

**Incorrect / no-credit criteria:**
- Proposes adding a fallback in retrieval code to return all documents when `doc_category` is missing (treats the symptom, leaves the index inconsistent)
- Cannot explain why atomic per-document delete-and-insert is required
- Proposes running this migration during business hours without a service availability plan

---

## Q20 — Ingestion latency vs. content fidelity tradeoff

**Difficulty:** expert

**Question:**
A legal RAG system ingests 10,000 contract PDFs daily. Contracts contain dense tables with financial terms, multi-column text, and embedded footnotes. A layout-aware PDF extractor captures this structure correctly but takes 8 seconds per document (22+ hours for the full batch). A fast extractor takes 0.3 seconds per document but produces degraded table content for 40% of contracts. The legal team requires same-day indexing (completed within 6 hours). Describe how you would design a tiered ingestion architecture to meet both the latency and accuracy constraints.

**Correct answer criteria:**
- Tier 1 (fast path): run the fast extractor on all 10,000 documents — this completes in approximately 50 minutes (with modest parallelization). Publish these results immediately to serve same-day retrieval.
- Tier 2 (quality assessment): run a content quality classifier on fast-extractor output to identify the ~4,000 documents (40%) with likely table extraction degradation. The classifier can use heuristics: unusually low numeric density for a financial contract, irregular character spacing artifacts, or known table structure signals in the extracted text.
- Tier 3 (slow path re-extraction): queue the identified 4,000 documents for layout-aware extraction. At 8 seconds/document with 10 parallel workers, this completes in approximately 54 minutes. Upsert the improved chunks, replacing the fast-extractor versions atomically per document.
- Service contract: Tier 1 satisfies the 6-hour deadline for all documents. Tier 3 improves content quality for the affected 40% within the same business day, without blocking same-day availability.
- Monitoring requirement: track which documents are in "fast-only" vs. "quality-upgraded" state; downstream retrieval should be aware of this state to enable confidence weighting or user-facing indicators of content quality
- Risk: the window between Tier 1 and Tier 3 completion exposes users to degraded table retrieval for the affected documents; this window must be minimized and its length should be SLA-documented

**Partial credit criteria:**
- Describes the two-tier approach but cannot quantify the latency math showing feasibility
- Correctly sizes the parallel processing to fit the time window but does not address the transitional state risk

**Incorrect / no-credit criteria:**
- Proposes using only one extractor without addressing the constraint that is violated
- Proposes a solution that exceeds the 6-hour window without justification
- Cannot explain how per-document atomicity is maintained during the upgrade from Tier 1 to Tier 3

---

## Q21 — Chunk quality regression after loader version change

**Difficulty:** expert

**Question:**
A PDF loader library releases a minor version update. An engineer applies the update in the staging environment and notices that RAGAS context_recall drops from 0.79 to 0.71 on a representative evaluation set. No configuration was changed. Describe a systematic process to determine whether the library update is safe to deploy, including what you would instrument and what rollback criteria you would set.

**Correct answer criteria:**
- Step 1 (diff the extraction): run both loader versions on the same 50 representative documents; diff the extracted page_content for each. Identify categories of change: whitespace normalization, header/footer stripping differences, table handling changes, encoding behavior changes. Quantify what fraction of documents changed and by how much.
- Step 2 (classify changes): for each category of change, determine whether it is an improvement (e.g., cleaner table extraction), a regression (e.g., content removed that should not be removed), or neutral (e.g., whitespace normalization). Contact the library's changelog or release notes to understand intended behavior.
- Step 3 (recall root cause): identify which specific evaluation queries drove the recall drop. Trace those queries to the documents that changed between versions. Confirm that the recall-reducing changes are regressions, not improvements on different queries.
- Step 4 (instrumentation): add per-document extraction diff metrics to the staging pipeline: `content_length_change_p50`, `fraction_documents_changed`, `fraction_documents_shorter` (content loss indicator). A minor update that reduces content by >5% in >10% of documents should be flagged.
- Rollback criteria: deploy only if (a) RAGAS context_recall on the evaluation set is within 2% of the current production value, (b) no document shows content reduction >20% (indicating content loss), and (c) the staging evaluation covers at least 200 documents spanning all format variants in the corpus.
- If the update passes but recall has not recovered: the evaluation set may not cover the regression cases; expand the evaluation set before proceeding.

**Partial credit criteria:**
- Describes extraction diffing and rollback criteria but does not instrument specific metrics
- Identifies the correct metrics but cannot connect the library changelog to classifying changes as improvements vs. regressions

**Incorrect / no-credit criteria:**
- Proposes rolling back immediately without diagnosing what changed
- Accepts the recall drop as acceptable because it is a "minor version" update
- Cannot describe what content-level changes would constitute a blocking regression

---

## Q22 — End-to-end ingestion pipeline audit

**Difficulty:** expert

**Question:**
A team inherits a RAG system that has been in production for 14 months. They suspect ingestion quality issues but have no baseline metrics. Describe a practical audit procedure to assess the health of the document ingestion layer without re-ingesting the corpus.

**Correct answer criteria:**
- Step 1 (index content sampling): sample 200 random chunks from the vector database; retrieve their page_content and metadata; compute: fraction with empty or very short content (<50 characters), fraction with encoding artifacts (replacement characters, mojibake patterns), fraction missing any required metadata field
- Step 2 (format coverage check): identify the file formats in the original source corpus; verify that the index contains expected proportions of content from each format; a format that contributes significantly fewer chunks than expected points to a loader failure for that format
- Step 3 (metadata completeness audit): for each required metadata field, compute the fraction of indexed chunks where the field is absent or null; any field missing in >5% of chunks indicates a loader or splitter configuration gap
- Step 4 (content length distribution): plot chunk length distribution; bimodal distributions (many very short chunks alongside normal-length chunks) suggest loader failures producing empty or minimal content for a subset of documents; single-document format analysis (e.g., "all very short chunks have source matching *.pdf") isolates the failure
- Step 5 (query recall spot-check): select 10 documents from the source corpus whose content is known; formulate 2–3 queries per document that should retrieve content from that document; verify that top-5 retrieval includes content from the correct document; failure here indicates either missed content or a source attribution problem
- Produce a findings report with: estimated fraction of corpus affected by each issue, severity rating per issue, and recommended remediation priority; do not re-ingest until the findings are reviewed and a migration plan is approved

**Partial credit criteria:**
- Describes 3 of the 5 audit steps
- Describes all 5 steps but cannot propose a findings report format or remediation prioritization

**Incorrect / no-credit criteria:**
- Proposes re-ingesting the full corpus as the first step
- Audits only the retrieval layer (RAGAS scores only) without examining raw ingestion output
- Cannot explain why format-specific coverage analysis is necessary

---
