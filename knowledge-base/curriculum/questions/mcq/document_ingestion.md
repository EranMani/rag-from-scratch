# MCQ Bank — document_ingestion
# Topic: document_ingestion
# Phase: 2 (Core Components)
# Questions: 20 (5 novice, 5 intermediate, 5 advanced, 5 expert)
# Last updated: 2026-05-23 (Commit 48)

---

## MCQ-1 — What a document loader returns

**Difficulty:** novice
**Topic:** document_ingestion

**Question:**
In a RAG ingestion pipeline, what does a document loader return as its primary output?

**Options:**
A. A list of embedding vectors, one per document
B. A list of Document objects, each containing page content and metadata
C. A parsed JSON structure representing the document's internal schema
D. A list of strings, one per paragraph in the source file

**Correct answer:** B

**Explanation:**
Document loaders return Document objects — a data structure pairing raw text content (page_content) with metadata (source path, page number, file type, etc.). The embedding step comes later in the pipeline. Loaders do not produce embeddings (A), they do not normalize to JSON schema (C), and they do not enforce paragraph-level splitting (D) — that is the job of a text splitter.

**Why A is wrong:** Embedding happens downstream, after the loader and after chunking. A developer who thinks loaders and embedders are the same stage has not separated ingestion from indexing in their mental model. The loader reads and parses; the embedder converts text to vectors.

**Why C is wrong:** Loaders do not transform documents into a canonical JSON schema. They capture whatever structure the format exposes (e.g., pages for PDFs, rows for CSVs) and attach it as metadata, but the output type is a Document object, not a JSON document.

**Why D is wrong:** Paragraph-level splitting is a text splitter responsibility, not a loader responsibility. A loader returns the full content of a document (or page) as a single page_content string with associated metadata. Splitting that content into smaller units is a separate pipeline stage.

---

## MCQ-2 — Loader vs. splitter distinction

**Difficulty:** novice
**Topic:** document_ingestion

**Question:**
Which of the following correctly describes the division of responsibility between a document loader and a text splitter in a RAG pipeline?

**Options:**
A. The loader splits the document into chunks; the splitter embeds those chunks
B. The loader reads and parses the raw file into Document objects; the splitter divides those Document objects into smaller chunks for embedding
C. The loader handles PDF files; the splitter handles HTML and plain text files
D. The loader and splitter are interchangeable names for the same pipeline component

**Correct answer:** B

**Explanation:**
The loader is responsible for reading a file from disk (or a URL or API), parsing its format, and returning one or more Document objects with text and metadata intact. The splitter then takes those Document objects and divides them into smaller, embedding-ready chunks. These are distinct pipeline stages with distinct responsibilities. A is reversed. C confuses format coverage (loaders exist for all formats) with pipeline stages. D is incorrect — they are different stages with different input/output contracts.

**Why A is wrong:** This reverses the pipeline order. Embedding comes after splitting, not as part of the splitter's job. A developer who is new to RAG pipelines sometimes assumes the last named component does the "output" work, leading to this reversal.

**Why C is wrong:** Format coverage and pipeline stage are orthogonal concerns. Loaders exist for PDFs, HTML, plain text, DOCX, CSV, and many other formats. The distinction between loader and splitter is not about which formats each handles — it is about what operation each performs on the content.

**Why D is wrong:** Treating loader and splitter as synonyms reflects a surface-level reading of pipeline diagrams. They share no interface and have different jobs: one reads from a source, the other divides content. Conflating them causes engineers to skip metadata propagation, which only becomes visible when a splitter's output has no source attached.

---

## MCQ-3 — Metadata a loader should capture

**Difficulty:** novice
**Topic:** document_ingestion

**Question:**
Which of the following is the most important piece of metadata for a document loader to capture, and why?

**Options:**
A. The file's SHA-256 hash, because it enables deduplication at query time
B. The source path or URL, because it allows the system to cite where retrieved content came from
C. The embedding model version, because it determines retrieval accuracy
D. The number of tokens in the document, because it governs chunk size selection

**Correct answer:** B

**Explanation:**
Source provenance — where a chunk came from — is the foundational metadata field. Without it, a RAG system can retrieve relevant content but cannot tell the user which document it came from or route a follow-up to the right source. SHA-256 hashes (A) are useful for deduplication but are a pipeline integrity concern, not a retrieval concern. Embedding model version (C) is stored at the vector store level, not per-document. Token count (D) informs chunking decisions but is not loader metadata — it is computed at split time.

**Why A is wrong:** SHA-256 hashes are a useful ingestion-time deduplication signal, but they are not the most important loader metadata for a RAG system. A system without source metadata cannot cite answers; a system without hash metadata just re-indexes duplicates. The failure modes are not equivalent.

**Why C is wrong:** Embedding model version is a property of the index configuration, not of individual documents. Attaching it to each Document object at load time would make model upgrades require re-reading all source files rather than just re-embedding. This is an architectural concern, not a per-document metadata concern.

**Why D is wrong:** Token count is not loader metadata — it depends on which tokenizer you apply, and loaders do not run tokenization. Token counts are computed at split time or at embedding time. A developer who answers D is confusing the loader stage with the splitter stage.

---

## MCQ-4 — What OCR is needed for

**Difficulty:** novice
**Topic:** document_ingestion

**Question:**
A PDF document loads successfully without errors, but the extracted page_content is empty or contains only garbled characters. What is the most likely cause?

**Options:**
A. The PDF's metadata fields are corrupt, causing the loader to skip content extraction
B. The PDF contains scanned images of text rather than machine-readable text, requiring OCR to extract content
C. The embedding model rejected the document because it exceeds the maximum token length
D. The text splitter ran before the loader completed, producing empty chunks

**Correct answer:** B

**Explanation:**
PDFs come in two variants: those with embedded machine-readable text (text-layer PDFs) and those that are scanned images stored inside a PDF container. Standard PDF loaders extract the text layer; they cannot read image-embedded text. If a PDF is image-only, the loader returns empty or corrupt content without raising an error — a classic silent data loss pattern. OCR (optical character recognition) must be applied to recover the text. A describes metadata corruption, which would not produce garbled content. C is an embedding-stage concern, not a loader concern. D is a pipeline ordering error that would not cause empty page_content.

**Why A is wrong:** Metadata corruption in a PDF does not cause page content to be empty or garbled. Metadata fields (author, creation date, title) are separate from the content stream. A developer who conflates PDF metadata with PDF content structure may reach for this answer.

**Why C is wrong:** The embedding model operates on text that has already been loaded. If the loader returned empty content, the embedding model would embed an empty string or skip the document — it would not retroactively cause the loader to fail. Embedding-stage failures manifest differently (e.g., API errors, dimension mismatches).

**Why D is wrong:** Pipeline component ordering is controlled by the application code. A text splitter does not execute autonomously before a loader. This answer describes an application bug, not a document format issue. The symptom (empty content) points to a parsing failure at load time, not a sequencing error.

---

## MCQ-5 — Format loader selection

**Difficulty:** novice
**Topic:** document_ingestion

**Question:**
A developer needs to ingest a directory of files with mixed formats: `.pdf`, `.html`, `.txt`, and `.csv`. Which approach is correct?

**Options:**
A. Use a single universal loader that auto-detects format from file extension and applies the appropriate parser
B. Use a directory loader that dispatches to format-specific loaders based on file extension
C. Convert all files to plain text first, then use a single text loader for all of them
D. Use the PDF loader for all files, since PDF is the most structurally complex format and its parser handles simpler formats by fallback

**Correct answer:** B

**Explanation:**
Handling mixed-format directories requires dispatching to format-specific loaders. A directory loader (or equivalent routing logic) maps file extensions to the appropriate parser — PDF files go to a PDF parser, HTML files go to an HTML parser, and so on. Each format has distinct structural elements (PDF pages, HTML tags, CSV rows) that require a dedicated parser. A "universal" loader that handles all formats does not exist as a single component. C is a viable approach but loses format-specific metadata (page numbers, HTML structure, CSV column headers) and requires a preprocessing step. D is incorrect — PDF parsers cannot parse HTML or CSV.

**Why A is wrong:** No single production-ready loader component auto-detects and correctly parses all formats without configuration. What exists is routing logic (e.g., a dictionary mapping extensions to loader classes). A developer who assumes framework magic handles format detection will encounter silent failures when an unregistered extension falls through.

**Why C is wrong:** Converting all files to plain text before loading is technically possible but discards format-specific structure. A PDF's page numbers, an HTML page's section headings, and a CSV's column names are all lost in a plain-text conversion. This matters for metadata propagation and for understanding chunk context during retrieval.

**Why D is wrong:** PDF parsers are designed to read the PDF binary format. They cannot parse HTML tag structures or CSV row delimiters. There is no "simpler format fallback" in PDF parsing — feeding an HTML file to a PDF parser will produce an error or empty content.

---

## MCQ-6 — PDF table extraction failure

**Difficulty:** intermediate
**Topic:** document_ingestion

**Question:**
A RAG system ingests a PDF containing financial tables. At query time, users report that retrieved chunks contain jumbled numbers with no clear row or column structure. What is the most accurate diagnosis?

**Options:**
A. The embedding model is not trained on tabular data and is returning low-confidence vectors
B. Standard PDF text extraction reads characters in page-order, which collapses multi-column table structure into a linear stream that does not preserve rows or columns
C. The text splitter is splitting table rows across chunk boundaries, destroying the numeric context
D. The vector database is truncating long chunks, and financial tables tend to exceed the storage limit

**Correct answer:** B

**Explanation:**
Standard PDF text extraction works by reading character positions on the page and streaming them in reading order (left to right, top to bottom). A table stored as positioned text elements gets linearized: cells from the same row may appear non-contiguous in the extracted stream, and column alignment is lost entirely. The result is a stream of numbers and labels with no structural meaning. This is a parser-level failure, not an embedding failure (A), a splitting failure (C), or a storage failure (D). Correct handling requires a table-aware extraction library that reconstructs row/column structure from bounding box coordinates.

**Why A is wrong:** Embedding models do not have confidence levels for specific data types. An embedding model will embed jumbled text just as willingly as well-structured text — the vector will simply not capture useful table semantics. The failure is upstream at the parsing stage, not at the embedding stage.

**Why C is wrong:** Chunk boundary splitting could cause issues if a table is split mid-row, but the symptom described (jumbled numbers, no row/column structure) indicates the structure was lost before chunking, at the extraction stage. Splitter-induced problems produce complete but contextually severed chunks, not structurally incoherent content.

**Why D is wrong:** Vector databases do not truncate chunks silently — they either store the full content or raise an error at insert time if a limit is exceeded. Silent truncation at the storage layer is not a standard vector database behavior. The symptom points to an extraction problem, not a storage problem.

---

## MCQ-7 — HTML loader noise

**Difficulty:** intermediate
**Topic:** document_ingestion

**Question:**
An HTML loader is ingesting a web documentation site. The retrieved chunks contain fragments like `<script>`, navigation menu text, and cookie consent banners. What is the root cause, and what is the correct fix?

**Options:**
A. The embedding model is including HTML tags in its vocabulary; the fix is to retrain the embedding model on clean text
B. The loader is not configured to strip non-content elements; the fix is to apply tag filtering or use a content-extraction heuristic before returning page_content
C. The text splitter is including adjacent pages' content; the fix is to reduce chunk overlap to zero
D. The vector database is not filtering metadata fields during retrieval; the fix is to add a metadata filter excluding script-type chunks

**Correct answer:** B

**Explanation:**
Raw HTML loaders that convert the full HTML document to text will include everything: navigation, footers, script blocks, cookie banners, and ads alongside the actual content. A well-configured HTML loader should strip non-content tags (script, style, nav, footer) and apply content-extraction heuristics (e.g., main content block identification). This is a loader configuration issue, not an embedding issue (A), a splitting issue (C), or a retrieval filtering issue (D). The problem is introduced at load time and must be fixed at load time.

**Why A is wrong:** Embedding models operate on the text they receive — they do not "include HTML tags in vocabulary" in a way that causes retrieval noise. The text the loader produces is what gets embedded. If that text contains script fragments, those fragments will be embedded. Fixing the embedding model cannot fix a loader that is not stripping noise.

**Why C is wrong:** Chunk overlap controls how much text is repeated between adjacent chunks — it has no effect on whether non-content HTML elements are included. Reducing overlap to zero would not remove navigation text or script blocks from page_content.

**Why D is wrong:** The vector database retrieves based on vector similarity, not metadata type. There is no "script-type chunk" flag that the vector database could filter on — the loader never labeled those chunks as noise. Even if you added such a filter, the correct fix is to not ingest the noise in the first place.

---

## MCQ-8 — Encoding detection and mojibake

**Difficulty:** intermediate
**Topic:** document_ingestion

**Question:**
A document loader ingests a legacy text file and produces output like `Ã©`, `â€™`, and `Ã ` where accented characters and punctuation should appear. What has happened, and what is the correct diagnosis?

**Options:**
A. The document contains Unicode characters that the embedding model cannot represent; they are being replaced with error codes
B. The file is encoded in Latin-1 (ISO-8859-1) but the loader is reading it as UTF-8, causing multi-byte sequences to be misinterpreted as individual Latin-1 characters
C. The vector database is corrupting special characters during storage; the fix is to switch to a database with Unicode support
D. The text splitter is cutting multi-byte characters at chunk boundaries, producing malformed sequences

**Correct answer:** B

**Explanation:**
This symptom is classic mojibake — the result of reading a Latin-1 encoded file as if it were UTF-8. Characters like `é` (Latin-1 byte `0xE9`) are rendered as `Ã©` when the single byte `0xE9` is incorrectly interpreted as the start of a two-byte UTF-8 sequence. The fix is to detect the file's actual encoding (using a library like chardet) and pass it explicitly to the loader. A is incorrect — embedding models do not produce "error codes." C is incorrect — the corruption occurs at load time, not at storage time. D is incorrect — chunk boundary splitting does not misinterpret byte sequences.

**Why A is wrong:** Embedding models accept text strings, not raw bytes. By the time text reaches the embedding model, encoding has already been resolved (or misresolved) by the loader. Error codes like `Ã©` are character rendering artifacts, not embedding model outputs. A developer who has never debugged encoding issues may assume the failure is downstream.

**Why C is wrong:** Vector databases store text strings, not raw bytes. If the mojibake is already in the string at load time, the database stores the corrupted string faithfully. The corruption originates at the file-reading step, not at the storage step. Switching databases would have no effect.

**Why D is wrong:** Text splitters operate on already-decoded Python strings. They do not handle raw bytes and cannot produce mojibake artifacts. Chunk boundary issues cause contextual discontinuities in meaning, not character encoding corruption.

---

## MCQ-9 — Silent data loss vs. hard error

**Difficulty:** intermediate
**Topic:** document_ingestion

**Question:**
A document loader processes 1,000 PDF files. For 50 of them — all scanned images without a text layer — the loader returns Document objects with empty page_content strings and no exception. Which statement correctly characterizes this behavior and its operational risk?

**Options:**
A. This is expected behavior; empty Document objects are a valid loader output and cause no downstream issues
B. This is silent data loss — 50 documents contributed zero retrievable content, but the pipeline completed without error, making the loss invisible to monitoring
C. This is a hard error condition; all downstream embedding calls will fail when they receive empty strings, surfacing the problem
D. This is a partial success; the metadata was preserved even though the content was empty, so retrieval can still use those documents

**Correct answer:** B

**Explanation:**
Empty page_content strings are valid at the Python level — the loader does not raise an exception. The pipeline continues: the empty strings get embedded (producing meaningless or zero vectors), get stored in the vector database, and silently occupy index slots. The 50 scanned documents are effectively absent from retrieval, but nothing in the pipeline signals this. This is silent data loss. Monitoring on exception count or document count will show 1,000 documents processed successfully. The correct fix is to add a post-load validation step that checks for empty or suspiciously short page_content and alerts or quarantines those documents.

**Why A is wrong:** Empty Document objects are not a valid successful outcome — they represent documents that contributed no searchable content to the index. A developer who accepts empty content without validation has a coverage gap: users asking questions about those 50 documents will never get relevant results, and the pipeline logs will show nothing wrong.

**Why C is wrong:** Embedding APIs generally accept empty strings without raising exceptions (they return a zero vector or a vector for the empty-string token). The failure mode is not a hard error — it is a silent semantic failure. A developer who expects the embedding step to surface this will be surprised when the pipeline runs cleanly.

**Why D is wrong:** Metadata without content is useless for retrieval. The vector database stores the empty content's embedding (which is meaningless) and the metadata. Similarity search will never retrieve an empty-content chunk for a meaningful query — the zero vector has near-zero cosine similarity with any real query vector. The metadata cannot compensate for absent content.

---

## MCQ-10 — Multi-column PDF linearization

**Difficulty:** intermediate
**Topic:** document_ingestion

**Question:**
A two-column academic paper is ingested using a standard PDF loader. Users report that retrieved paragraphs from the paper are incoherent — mixing sentences from what were originally separate columns. What is the correct explanation?

**Options:**
A. The PDF file is corrupt; the loader is falling back to raw byte extraction
B. The text splitter's chunk size is too large, causing it to merge content from adjacent pages
C. Standard PDF text extraction reads all text in page-order by y-coordinate, causing text from the left and right columns to interleave based on their vertical position on the page
D. The embedding model is combining vectors from spatially close text elements, producing mixed-column chunks

**Correct answer:** C

**Explanation:**
In a two-column PDF, text elements from both columns are positioned at varying y-coordinates (vertical positions) on the page. A standard PDF text extractor that reads in top-to-bottom, left-to-right page order will interleave text from both columns whenever a left-column paragraph and a right-column paragraph appear at the same vertical range. The result is sentences from the left column alternating with sentences from the right column. Handling this correctly requires a layout-aware PDF parser that identifies column boundaries and processes each column as a separate text stream. A, B, and D do not describe parsing-level spatial layout issues.

**Why A is wrong:** File corruption would produce decoding errors, not coherent-looking but mixed content. The symptom here is readable text in the wrong order, which indicates a structural parsing problem rather than a data integrity problem.

**Why B is wrong:** Chunk size affecting page boundaries is a text splitter concern. The interleaving described in the question happens at extraction time — before the splitter runs. Even with a very small chunk size, if the extractor produces an interleaved text stream, the resulting chunks will contain mixed-column content.

**Why D is wrong:** Embedding models operate on text strings that have already been assembled by the loader. They do not combine text based on spatial proximity — that is a property of the PDF layout, which must be handled at the parsing stage. Embeddings cannot retroactively fix interleaved source text.

---

## MCQ-11 — Metadata propagation to chunks

**Difficulty:** advanced
**Topic:** document_ingestion

**Question:**
A document loader correctly captures page numbers and source URLs in Document object metadata. After text splitting, a developer discovers that 60% of the resulting chunks have empty metadata. What is the most likely cause?

**Options:**
A. The text splitter discards metadata by default; metadata must be re-attached post-split using the original Document objects as a lookup key
B. The text splitter was not configured to propagate metadata from parent Document objects to child chunks; the default behavior in many splitters is to propagate metadata, but incorrect configuration can suppress it
C. The vector database strips metadata fields during upsert to reduce storage cost
D. Metadata fields are lost during embedding because embedding APIs do not accept metadata parameters

**Correct answer:** B

**Explanation:**
Text splitters have different default behaviors around metadata propagation. Some splitters copy the parent Document's metadata to every child chunk by default. Others require explicit configuration. If a splitter is initialized with incorrect parameters or a custom subclass that does not propagate metadata, child chunks will have empty metadata dictionaries. The fix is to verify the splitter's metadata propagation behavior and configure it explicitly. A is incorrect — the common default is to propagate metadata, not discard it. C is incorrect — vector databases store metadata faithfully. D is incorrect — embeddings are stored alongside metadata, not passed together to the embedding API.

**Why A is wrong:** The standard behavior for most production text splitters is to copy parent Document metadata to all child chunks. A developer who believes metadata is always discarded will add unnecessary post-processing logic, and may do so incorrectly (e.g., by matching on content similarity rather than a stable chunk ID). The failure here is incorrect configuration, not a universal default.

**Why C is wrong:** Vector databases are designed to store metadata alongside vectors — that is one of their primary value propositions. A database that silently stripped metadata during upsert would be unusable for filtered search. If metadata is missing after storage, the problem is upstream (in the loader or splitter), not in the database.

**Why D is wrong:** The embedding API call and the metadata storage are separate operations in the indexing pipeline. An embedding API accepts text and returns a vector. Metadata is stored separately in the vector database record. They are not passed together to the embedding API, and the embedding step cannot cause metadata loss.

---

## MCQ-12 — BOM marker handling

**Difficulty:** advanced
**Topic:** document_ingestion

**Question:**
A text file loader ingests a UTF-8 encoded file and the first chunk consistently begins with the characters `ï»¿` prepended to the actual content. Users report that exact-match metadata filters on the first chunk fail. What is the cause?

**Options:**
A. The file begins with a UTF-8 BOM (Byte Order Mark) that is being read as literal text characters instead of being stripped as a file encoding marker
B. The embedding model prepends a CLS token to every sequence, and the loader is incorrectly including it in page_content
C. The vector database is prepending an internal document ID to the chunk content during storage
D. The text splitter is including the file header as content in the first chunk

**Correct answer:** A

**Explanation:**
`ï»¿` is the UTF-8 BOM (EF BB BF) rendered as Latin-1 characters — a sign that the loader opened a UTF-8-with-BOM file without specifying the BOM-aware encoding (`utf-8-sig` in Python). The BOM is meant to be a file encoding marker, invisible to readers, but when read as regular content it appears as three garbled characters at the start of the file. This corrupts the first chunk's content and causes exact-match filters (which compare against a clean string) to fail. The fix is to open files with `utf-8-sig` encoding, which automatically strips the BOM. B, C, and D describe components that do not inject characters into page_content.

**Why B is wrong:** CLS tokens are internal to transformer model tokenization — they are never present in the text string that a loader produces. Loaders work with raw text, not with tokenized sequences. A developer familiar with transformer internals might reach for this answer without recognizing that tokenization is invisible to the text pipeline.

**Why C is wrong:** Vector databases store document IDs in separate fields (e.g., an `id` field), not prepended to the content string. If an ID were being prepended to content, it would appear consistently across all chunks, not just the first one. The symptom here is first-chunk-only corruption, which points to a file-start marker, not a database behavior.

**Why D is wrong:** A "file header" in the text splitter sense does not exist. Text splitters divide content at token or character boundaries, not at semantic sections like headers. If there were a structural header issue, it would be caused by the file format or the loader configuration, not by the splitter prepending characters.

---

## MCQ-13 — JavaScript-rendered content

**Difficulty:** advanced
**Topic:** document_ingestion

**Question:**
A team is ingesting a documentation site where pages are rendered by a JavaScript framework. Their HTML loader produces Document objects with nearly empty page_content despite the pages being full of text in a browser. What is the root cause?

**Options:**
A. The HTML loader is not handling HTTPS URLs; the fix is to use HTTP instead
B. Standard HTTP-based HTML loaders fetch the raw HTML response, which for JavaScript-rendered pages contains only the shell HTML with no content — the actual text exists only in the browser's JavaScript runtime after JS execution
C. The embedding model is filtering out dynamically generated content because it cannot be verified against training data
D. The text splitter is removing HTML comment blocks that contain the page's actual content

**Correct answer:** B

**Explanation:**
JavaScript-rendered pages (Single Page Applications, React, Vue, Angular sites) send minimal HTML in the initial HTTP response. The actual content is injected into the DOM by JavaScript that runs in the browser. An HTTP-fetching HTML loader never executes JavaScript — it receives the shell HTML and parses that, producing empty or near-empty page_content. Handling these pages requires a headless browser loader (e.g., one using Playwright or Selenium) that renders the page fully before extracting content. A is incorrect — HTTPS has no bearing on JavaScript rendering. C is incorrect — embedding models do not filter content. D is incorrect — content is not hidden in HTML comments.

**Why A is wrong:** Whether a site uses HTTP or HTTPS affects transport security, not JavaScript rendering. Both HTTP and HTTPS sites can be JavaScript-rendered. A developer who changes the URL scheme will see the same empty content because the fundamental problem is JS execution, not protocol.

**Why C is wrong:** Embedding models are stateless functions that convert input text to vectors. They do not have a concept of "verifying content against training data" or filtering dynamic content. Whatever text they receive is embedded. The failure is that no text was produced by the loader in the first place.

**Why D is wrong:** HTML comment blocks (`<!-- -->`) are occasionally used for conditional content or template markers, but they do not contain the main rendered text of a JavaScript application. The text a user sees in a browser is in the DOM, injected by JavaScript after execution — not in HTML comments.

---

## MCQ-14 — DOCX embedded objects

**Difficulty:** advanced
**Topic:** document_ingestion

**Question:**
A DOCX loader ingests a Word document that contains an embedded Excel spreadsheet with financial data. The loader produces page_content with no trace of the spreadsheet data. Users querying for financial figures from that document get no results. What is the correct explanation?

**Options:**
A. Excel data exceeds the DOCX loader's maximum file size limit and is truncated silently
B. Embedded OLE objects (such as Excel spreadsheets) within DOCX files are binary blobs from the perspective of the DOCX text parser — standard loaders do not extract content from embedded objects
C. The text splitter removes numeric content because it cannot be meaningfully chunked
D. The vector database does not index numeric tokens, so financial figures are never retrievable

**Correct answer:** B

**Explanation:**
DOCX files are ZIP archives containing XML files for text content. When a Word document contains an embedded Excel spreadsheet, that spreadsheet is stored as an embedded OLE (Object Linking and Embedding) binary object — a separate binary blob inside the DOCX container. Standard DOCX text parsers read the XML text content; they do not extract and parse embedded binary objects. The spreadsheet's data is simply not accessible to the text parser. Handling this case requires either extracting the embedded object separately and parsing it with a spreadsheet loader, or pre-processing the document to export the spreadsheet as a standalone file. A, C, and D describe non-existent limits or behaviors.

**Why A is wrong:** DOCX loaders do not have a file size limit that causes silent truncation. File size limits, if any, would produce an error, not silent data loss. The embedded spreadsheet is simply not parsed — not truncated.

**Why C is wrong:** Text splitters do not filter content by data type. They split on character or token boundaries regardless of whether the content is text, numbers, or mixed. A splitter that removed numeric content would break every financial or scientific document in the corpus.

**Why D is wrong:** Vector databases index all tokens including numbers. Financial figures are retrievable if they were correctly extracted and embedded. The failure in this scenario is at the loader stage — the numbers never made it into the text pipeline to be embedded or stored.

---

## MCQ-15 — Re-indexing after loader change

**Difficulty:** advanced
**Topic:** document_ingestion

**Question:**
A team upgrades their PDF loader from a basic text extractor to a layout-aware extractor that correctly handles tables and multi-column layouts. They run the new loader on their document corpus and upsert the results into the existing vector database without deleting old entries. What production failure mode does this create?

**Options:**
A. The embedding dimension mismatch between old and new vectors will cause the database to reject the upsert
B. The vector database now contains duplicate entries for each document — the old poorly-extracted version and the new correctly-extracted version — and retrieval may return either, non-deterministically
C. The new loader produces larger chunks that exceed the embedding model's token limit, causing silent truncation
D. The retrieval precision metric will temporarily drop because the new vectors are not yet warmed up in the ANN index

**Correct answer:** B

**Explanation:**
When you upsert new document embeddings without first deleting the old ones, both versions coexist in the index if they have different chunk IDs (which they likely will if chunking strategy also changed with the loader upgrade). At query time, the retrieval system may return old poorly-extracted chunks, new correctly-extracted chunks, or a mix — depending on which version happens to score higher for a given query. This is a silent correctness failure: the system works (no errors), but retrieval quality is inconsistent and unpredictable. The correct migration procedure is to delete old entries for affected documents before inserting new entries, or to use a versioned index with a clean cutover. A is incorrect if the embedding model did not change. C and D describe non-standard behaviors.

**Why A is wrong:** Embedding dimension mismatches only occur if the embedding model changed. If the same embedding model is used with the new loader, all vectors have the same dimension. Upsert succeeds without errors, which is precisely what makes this failure mode dangerous — it looks like a success.

**Why C is wrong:** A loader upgrade does not automatically change chunk size. Chunk size is controlled by the text splitter configuration, which is separate from the loader. Even if the new loader produces longer per-document content, the splitter divides it into the same size chunks as before.

**Why D is wrong:** ANN (Approximate Nearest Neighbor) indexes do not have a "warmup" period for individual vectors. New vectors are indexed and immediately retrievable. Retrieval precision drop would be caused by the coexistence of two document versions in the index, not by an indexing warmup delay.

---

## MCQ-16 — Encoding detection strategy

**Difficulty:** expert
**Topic:** document_ingestion

**Question:**
A production ingestion pipeline processes files uploaded by users from diverse regional offices. The pipeline sees files encoded in UTF-8, UTF-16 LE, Latin-1, and Windows-1252. A developer proposes always opening files with `errors='replace'` to avoid decoding exceptions. What is the critical flaw in this approach?

**Options:**
A. `errors='replace'` is not a valid Python file open mode and will raise a ValueError at runtime
B. `errors='replace'` silently substitutes the Unicode replacement character (`U+FFFD`, rendered as `?`) for undecodable bytes, converting encoding errors into invisible content corruption that will not appear in logs or exception counts
C. `errors='replace'` causes the loader to skip files with more than 5% undecodable bytes, creating silent data loss for heavily non-ASCII documents
D. `errors='replace'` triggers automatic re-encoding to UTF-8, which may alter the meaning of diacritical characters

**Correct answer:** B

**Explanation:**
`errors='replace'` is valid Python — but it converts hard decoding errors into silent content corruption. Every undecodable byte sequence is replaced by `?` (or `U+FFFD`) in the output string. The pipeline continues without raising an exception. A file with hundreds of misread accented characters produces a Document object full of replacement characters, which gets embedded and stored. No exception fires, no metric increments, no log line indicates the problem. The correct approach is to detect file encoding before opening (using chardet or charset-normalizer) and open with the detected encoding, raising an explicit error for truly undetectable cases. B correctly identifies the silent corruption pattern.

**Why A is wrong:** `errors='replace'` is a standard Python `open()` and `bytes.decode()` error handler. It is fully valid. A developer who has not read the Python docs on error handlers may assume it is invalid, but this assumption would be quickly disproved in development — the silent corruption problem only surfaces in production with real heterogeneous file corpora.

**Why C is wrong:** `errors='replace'` does not skip files or apply a threshold. It processes every byte of every file, replacing undecodable sequences inline. There is no 5% threshold or any skip behavior. This answer describes a behavior that does not exist in Python's encoding error handler.

**Why D is wrong:** `errors='replace'` does not re-encode data. It is an error handler for decoding (bytes to string), not an encoding transformation. It does not alter the encoding of the output — it produces a Python string with replacement characters where decoding failed. There is no diacritical alteration involved.

---

## MCQ-17 — Ingestion pipeline monitoring gap

**Difficulty:** expert
**Topic:** document_ingestion

**Question:**
A production RAG system shows a steady RAGAS context_precision of 0.85 for six months. After a batch of 2,000 new documents is ingested, context_precision drops to 0.62 without any change to the retrieval or generation configuration. The engineering team checks exception logs and finds zero errors. What is the most operationally rigorous next diagnostic step?

**Options:**
A. Roll back the embedding model to the previous version, because model drift commonly causes precision drops after corpus expansions
B. Inspect the newly ingested documents' page_content fields for empty strings, encoding corruption, and abnormally short chunks — a loader-side issue may have silently degraded content quality for the new batch
C. Increase the number of retrieved chunks (top-k) to compensate for the precision drop, because the new documents dilute the retrieval pool
D. Re-run the RAGAS evaluation on the original document set only, to determine whether the metric degradation is confined to the new documents

**Correct answer:** B

**Explanation:**
A precision drop with zero exceptions after corpus expansion points to a data quality problem in the new batch, not a model or configuration change. The first diagnostic step is to inspect what the loader actually produced for the new documents: are there empty page_content fields (scanned PDFs)? Encoding corruption (mojibake)? Chunks that are suspiciously short (loader truncation)? Silent loader failures produce low-quality embeddings that dilute the index and surface irrelevant content at query time. D is a reasonable second step to isolate the scope, but B is the operationally correct first step because it examines the failure closest to its likely source. A and C do not diagnose — they apply interventions before understanding the cause.

**Why A is wrong:** Embedding model versions are a configuration artifact. A model does not "drift" between ingestion batches unless you changed the model or its configuration. Rolling back without diagnosing the root cause would restore the metric only if the model was the cause — and the batch-correlated timing points to a data issue, not a model issue.

**Why C is wrong:** Increasing top-k is a retrieval parameter change that would reduce precision further (more retrieved chunks means a higher chance of irrelevant ones being included). This is the opposite of the correct response. A developer who reaches for this answer is treating the symptom rather than diagnosing the cause.

**Why D is wrong:** Re-running RAGAS on the original set is a useful isolation step, but it should not be the first step. The first step is to look at what the ingestion pipeline produced. RAGAS is expensive to run, and running it first before inspecting the raw loader output inverts the debugging order — start at the failure source, then validate with evaluation.

---

## MCQ-18 — Loader output schema contract

**Difficulty:** expert
**Topic:** document_ingestion

**Question:**
A downstream component expects every chunk to have `source`, `page`, and `doc_type` fields in its metadata. The loader currently populates `source` and `page` but `doc_type` is absent for 30% of the corpus (files loaded before the field was added). At retrieval time, filters on `doc_type` silently exclude those 30% from results. What is the correct architectural fix?

**Options:**
A. Add a post-retrieval filter that appends a default `doc_type` to any result that lacks it
B. Re-ingest the 30% with the updated loader and update their vector database entries, ensuring no document in the index is missing the required metadata field
C. Make the downstream `doc_type` filter optional by adding a null check that falls back to returning all documents when the field is absent
D. Store `doc_type` as part of page_content rather than metadata, so it is always present in the retrieved text regardless of metadata schema evolution

**Correct answer:** B

**Explanation:**
The correct fix is to close the data gap at the source: re-ingest the affected documents with the updated loader that populates `doc_type`, and upsert the corrected entries into the vector database. This ensures the index is consistent — every document has the required metadata fields — and downstream components can rely on the schema contract without defensive null checks. A and C are defensive workarounds that paper over a data quality problem without fixing it; they leave the index inconsistent and make the schema contract unreliable. D is an anti-pattern — metadata that belongs in structured fields should not be embedded into unstructured content.

**Why A is wrong:** Post-retrieval metadata injection is a band-aid that fixes display but does not fix the index. The documents are still retrievable without `doc_type` in filtered searches — adding it at display time does not make them accessible to filter-based queries. The silent exclusion problem remains.

**Why C is wrong:** Making filters optional preserves access to the 30% but defeats the purpose of having `doc_type` as a filter field. If the filter falls back to returning all documents when the field is absent, queries that should be scoped to a specific document type will return unscoped results for the legacy portion. This inconsistency will produce confusing retrieval behavior that is difficult to debug.

**Why D is wrong:** Embedding metadata like `doc_type` into page_content converts a structured query parameter into an unstructured text signal. Retrieval based on `doc_type` becomes a semantic similarity problem rather than an exact filter. A query that should return only PDFs would need to semantically match "doc_type: pdf" in the text rather than use an equality filter. This degrades precision and makes the system harder to reason about.

---

## MCQ-19 — Ingestion latency vs. accuracy tradeoff

**Difficulty:** expert
**Topic:** document_ingestion

**Question:**
An ingestion pipeline must process 500,000 documents per day. The team evaluates two PDF loaders: Loader A extracts text in 0.1 seconds per document with 95% content accuracy (5% documents have extraction errors). Loader B extracts text in 2 seconds per document with 99.5% content accuracy (0.5% errors). Given a hard deadline of 8 hours for daily ingestion, which loader is operationally viable, and what is the correct risk assessment for the inaccurate loader?

**Options:**
A. Both loaders are viable; Loader A's 5% error rate is acceptable because user queries hit only a small fraction of the corpus at any time
B. Only Loader A is viable within the 8-hour window; its 5% error rate means 25,000 documents per day have extraction errors, which must be quarantined and re-processed with a slower fallback to manage the accuracy gap
C. Only Loader B is viable because data quality always takes priority over throughput; the team must negotiate the 8-hour deadline
D. Neither loader is viable; the correct approach is to parallelize Loader B across enough workers to meet the throughput target while maintaining 99.5% accuracy

**Correct answer:** B

**Explanation:**
Loader B at 2 seconds/document requires 1,000,000 seconds (277 hours) for 500,000 documents — far outside the 8-hour window even with aggressive parallelization. Loader A at 0.1 seconds/document requires 50,000 seconds (13.9 hours) for single-threaded processing, which is within reach with modest parallelization. Loader A is the only viable choice. However, its 5% error rate is not "acceptable" without mitigation — 25,000 documents per day receive bad extractions. The correct operational response is to detect error cases (via post-load content quality checks), quarantine them, and re-process them with a more accurate fallback loader (Loader B or an OCR fallback) as a separate slower queue. This manages the accuracy gap without blocking the main pipeline.

**Why A is wrong:** "Users only query a small fraction of the corpus" does not make an error rate operationally acceptable. Over time, 25,000 bad documents per day accumulates into a large portion of the index with degraded content. Users who query topics covered by those documents will receive poor results, and there is no mechanism to know which documents are affected.

**Why C is wrong:** "Data quality always takes priority" is a policy statement, not an engineering analysis. Loader B cannot process 500,000 documents in 8 hours — single-threaded it would take 277 hours. Even with 50 parallel workers it requires 5.6 hours per document-set, which is within range but leaves no margin. The pragmatic solution is a tiered approach: Loader A for the bulk, with error detection and Loader B as a fallback for identified failures.

**Why D is wrong:** Parallelizing Loader B to meet the throughput target is technically possible but computationally expensive and potentially fragile. With 50 workers, Loader B processes 500,000 documents in approximately 5.6 hours, which is viable — but D presents this as the only option without acknowledging Loader A as viable. More importantly, D ignores the risk management dimension of the question: the correct answer addresses what to do about the accuracy gap, not just which loader to use.

---

## MCQ-20 — Chunk ID stability for incremental indexing

**Difficulty:** expert
**Topic:** document_ingestion

**Question:**
An incremental ingestion pipeline should only re-index documents that have changed since the last run. A developer proposes generating chunk IDs using `hash(page_content)` so that unchanged content produces the same ID and can be skipped. A colleague objects that this will cause silent re-indexing failures. Who is correct and why?

**Options:**
A. The developer is correct — content hashing is the standard approach for stable chunk IDs, and the same content always produces the same ID across runs
B. The colleague is correct — content hashing alone is insufficient because two different chunks with identical text (e.g., a repeated disclaimer paragraph) would share the same ID, and updating one would silently overwrite the other in the vector database
C. The colleague is correct — hash functions are not deterministic across Python versions, so the same content may produce different IDs in different runtime environments
D. The developer is correct — the vector database deduplicates identical vectors automatically, so hash collisions in IDs are resolved at the storage layer

**Correct answer:** B

**Explanation:**
Content hashing alone produces collisions for genuinely duplicate text across different documents. A "Terms and Conditions" footer, a repeated disclaimer, a standard header — any text that appears verbatim in multiple documents will hash to the same ID. When the incremental pipeline processes document A (which has an unchanged disclaimer), it skips the chunk. When it processes document B (which has an identical but updated disclaimer), it upserts a new vector under the same ID, overwriting document A's disclaimer entry. Document A's chunk now points to document B's content. The correct chunk ID includes both a document identifier (stable file path or document hash) and a chunk position or sequence number, ensuring uniqueness across documents. C is incorrect — Python's hash functions are deterministic for the same input and version. D is incorrect — vector databases do not deduplicate at the storage layer.

**Why A is wrong:** Content hashing is not the standard approach for chunk ID stability — source-plus-position is. A developer who uses only content hashing has a working system until they encounter repeated text across documents, at which point the collision causes silent cross-document contamination that is extremely difficult to diagnose.

**Why C is wrong:** Python's built-in `hash()` function is deliberately randomized across process invocations for security reasons (hash randomization, PEP 456). However, cryptographic hash functions like `hashlib.md5()` or `hashlib.sha256()` are deterministic across versions for the same input. The developer likely intends a cryptographic hash, not `hash()`. Even if non-determinism were the issue, the correct fix would be to use a stable hash function — not to abandon content hashing entirely, as the colleague suggests.

**Why D is wrong:** Vector databases do not deduplicate based on vector content or record ID collisions. If two different calls upsert records with the same ID, the second upsert overwrites the first. This is exactly the failure mode described. The database does not detect or resolve collisions — that is the application's responsibility.

---
