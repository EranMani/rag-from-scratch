# MCQ Bank — chunking_strategies
# Topic: chunking_strategies
# Phase: 2 (Core Components)
# Questions: 20 (5 novice, 5 intermediate, 5 advanced, 3 expert)
# Last updated: 2026-05-23 (Commit 51)

---

## MCQ-1 — Why chunking is necessary

**Difficulty:** novice
**Topic:** chunking_strategies

**Question:**
Why must documents be split into chunks before embedding in a RAG pipeline?

**Options:**
A. To reduce storage costs in the vector database
B. Because embedding models have a maximum token input length that many documents exceed
C. To improve the quality of cosine similarity scores between documents
D. Because LLMs cannot process text that was embedded as a single unit

**Correct answer:** B

**Explanation:**
Embedding models have a fixed maximum context window (often 512 or 8192 tokens depending on the model). Documents that exceed this limit cannot be embedded in a single pass. Chunking splits documents into pieces that fit within this limit. Storage costs (A) are a secondary consideration. Embedding quality per chunk (C) is a chunking strategy concern, not the reason chunking is necessary. LLM processing (D) is about the generation step, not the embedding step.

**Why A is wrong:** Storage cost is a real but secondary concern. A corpus of 10,000 documents generates roughly the same number of embedding vectors whether chunked or not (document-level or chunk-level storage). The primary driver is the model's input length limit, not storage economics.

**Why C is wrong:** Cosine similarity quality is affected by how well the embedding captures the chunk's meaning, which is related to chunking strategy. But this is not why chunking is necessary in the first place — it does not become necessary until documents exceed the model's token limit.

**Why D is wrong:** LLM context window limits are a constraint on the generation step (what context the LLM can process) and do relate to chunking strategy decisions, but they are separate from why embedding-time chunking is necessary. Embedding happens at indexing time, before the LLM is involved.

---

## MCQ-11 — What chunk size controls

**Difficulty:** novice
**Topic:** chunking_strategies

**Question:**
A developer sets chunk size to 512 tokens when building a RAG index. What does this number directly control?

**Options:**
A. The number of chunks returned per query
B. The maximum number of tokens in each individual piece of text stored in the vector database
C. The minimum length of the LLM's generated response
D. The number of dimensions in each embedding vector

**Correct answer:** B

**Explanation:**
Chunk size determines the maximum length of each text segment that is embedded and stored as a single unit in the vector database. When documents are split, each resulting chunk will contain at most 512 tokens of text. Smaller chunks mean more chunks per document; larger chunks mean fewer but longer segments. Chunk size does not control retrieval count (top-K), response length, or embedding dimensions — those are separate parameters.

**Why A is wrong:** The number of chunks returned per query is controlled by the top-K retrieval parameter, not the chunk size. A developer can retrieve top-5 chunks regardless of whether each chunk is 128 or 1024 tokens. Confusing chunk size with retrieval count is common in beginners who have not separated the indexing configuration from the retrieval configuration.

**Why C is wrong:** LLM response length is controlled by generation parameters (max_tokens) and the grounding instruction in the prompt, not by how the documents were chunked. A chunk size of 512 says nothing about how long the LLM will make its answer.

**Why D is wrong:** Embedding dimensions are fixed by the embedding model's architecture, not by the chunk size. A 512-dimension model produces 512-dimensional vectors regardless of whether the input chunk is 100 tokens or 512 tokens. Chunk size is about the length of the text input, not the length of the vector output.

---

## MCQ-12 — Chunk overlap direction

**Difficulty:** novice
**Topic:** chunking_strategies

**Question:**
A document is chunked with chunk_size=400 tokens and overlap=100 tokens. Which statement correctly describes what this overlap does?

**Options:**
A. Every chunk is padded to exactly 500 tokens by repeating content from the beginning of the document
B. The last 100 tokens of each chunk are repeated at the start of the following chunk
C. Every other chunk is skipped, producing half the total number of chunks
D. The first 100 tokens of each chunk are removed to reduce redundancy

**Correct answer:** B

**Explanation:**
Chunk overlap means consecutive chunks share tokens at their boundary. Chunk N contains tokens 1–400; the next chunk contains tokens 301–700 (the last 100 tokens of chunk N, 301–400, are repeated at the start of the next chunk). This ensures that content spanning the boundary between two chunks appears fully in at least one retrievable unit. Overlap increases the total chunk count — it does not reduce it or pad chunks with unrelated content.

**Why A is wrong:** Overlap does not pad chunks with content from elsewhere in the document. The overlapping tokens always come from the immediately preceding chunk — they are the tail end of the previous chunk carried forward into the beginning of the current chunk. Padding from the document beginning would corrupt the semantic content of later chunks.

**Why C is wrong:** Overlap causes chunks to partially repeat content, not skip chunks. An overlap of 100 tokens on 400-token chunks produces more chunks than no overlap would, not fewer. Skipping every other chunk would produce severe coverage gaps — the opposite of what overlap is designed to do.

**Why D is wrong:** Removing the first 100 tokens of each chunk would reduce coverage and create gaps at chunk boundaries — the exact problem overlap is designed to prevent. This option inverts the mechanism: overlap adds content at the start of each chunk (from the previous chunk's tail); it does not remove content.

---

## MCQ-13 — Identifying a chunking failure from a symptom

**Difficulty:** novice
**Topic:** chunking_strategies

**Question:**
A user asks "What is the maximum file size limit for uploads?" The RAG system retrieves a chunk that says: "This limit was increased in the 2023 update to better support enterprise workflows." The LLM cannot answer the question. What is the most likely chunking problem?

**Options:**
A. The chunk is too short — it needs more tokens to be embedded correctly
B. The chunk lacks its antecedent — "this limit" refers to something in a preceding chunk that was not included, making the chunk uninterpretable in isolation
C. The embedding model failed to encode the chunk because it contains a year (2023)
D. The chunk should have been stored in a separate index from the rest of the document

**Correct answer:** B

**Explanation:**
The phrase "this limit" is a pronoun reference (anaphora) pointing to something introduced earlier in the document. When the chunker split the document at a boundary before this sentence, the referent ("maximum file size limit" or whatever was named) ended up in a different chunk. The retrieved chunk is semantically incomplete — it cannot stand alone as a retrievable unit. This is the "orphaned chunk" problem: a chunk that contains a reference to context it was separated from by the chunk boundary.

**Why A is wrong:** The problem is not chunk length — adding more tokens to this chunk would not help if those tokens come from later in the document rather than the earlier part that explains what "this limit" refers to. The issue is the direction of context: the missing reference comes before the retrieved chunk, not after it.

**Why C is wrong:** Embedding models handle years, numbers, and all standard text without any issue. There is no category of token that causes an embedding call to fail. The chunk would be embedded normally; the failure is that the resulting embedding and retrieved chunk are useless because the pronoun has no referent.

**Why D is wrong:** Putting the chunk in a separate index would not restore the missing antecedent. The problem is within the document's chunk boundary decision, not the indexing structure. Separate indexes organize retrieval; they do not repair chunks that lack self-contained meaning.

---

## MCQ-14 — Chunk size and LLM context interaction

**Difficulty:** intermediate
**Topic:** chunking_strategies

**Question:**
A developer uses chunk_size=1000 tokens and retrieves top-10 chunks per query. The LLM has a 12,000-token context window and the system prompt uses 500 tokens. What is the most immediate operational risk?

**Options:**
A. The embedding model will fail to embed 1000-token chunks because they exceed its maximum input
B. The total context (10 chunks × 1000 tokens + 500 system prompt) is 10,500 tokens, leaving only 1,500 tokens for the query and LLM response. Under this pressure, the system will silently truncate lower-ranked chunks or fail on long queries
C. The vector database will reject queries that request more than 5 chunks
D. LLMs cannot process more than 5,000 tokens of retrieved context regardless of the stated context window

**Correct answer:** B

**Explanation:**
10 chunks × 1000 tokens = 10,000 context tokens, plus 500 system prompt tokens = 10,500 tokens consumed before the user query or LLM response is even counted. With a 12,000-token context window, only 1,500 tokens remain. A user query of 50–200 tokens leaves 1,300–1,450 tokens for the LLM response. If the user asks a longer question, the system approaches the context limit. Many frameworks silently truncate lower-ranked chunks rather than raising an error, which drops potentially relevant content from the prompt without alerting the engineer.

**Why A is wrong:** Most modern embedding models (text-embedding-3, OpenAI ada-002 successor, sentence-transformers variants) support context windows from 512 to 8192 tokens. A 1000-token chunk may exceed some embedding models' limits, but that is a separate constraint to check. The question asks about the "most immediate operational risk," which is the LLM context window exhaustion — a risk that exists regardless of whether the embedding model handles 1000 tokens.

**Why C is wrong:** Vector databases have no built-in limit on top-K result count. They return however many results are requested, limited only by the number of vectors stored. A request for top-10 on a database with millions of vectors will return 10 results without issue.

**Why D is wrong:** LLMs process up to their stated context window limit — 12,000 tokens in this case. The 5,000-token claim is fabricated. Modern LLMs can process their full stated context window. The constraint is the window size itself, not an imaginary sub-limit on retrieved context.

---

## MCQ-15 — Semantic chunking vs. fixed-size for a specific document type

**Difficulty:** intermediate
**Topic:** chunking_strategies

**Question:**
A corpus contains FAQ pages. Each FAQ entry has a question heading and a 2–5 sentence answer beneath it. Which chunking strategy most directly preserves the retrievable semantic unit?

**Options:**
A. Fixed-size 512-token chunks with 50-token overlap — ensures uniform chunk length for consistent embedding quality
B. One chunk per FAQ entry (question heading + answer body) — preserves the natural semantic unit: a complete Q&A pair that stands alone as a retrievable answer
C. Sentence-level chunking — each sentence becomes its own chunk for maximum granularity
D. Paragraph-level chunking across the entire page — treats all FAQ entries on a page as a single chunk

**Correct answer:** B

**Explanation:**
An FAQ entry is a self-contained semantic unit: the question defines the topic and the answer provides the grounding. Chunking one Q&A pair per chunk means a retrieval hit returns a complete, interpretable unit. A user querying about a topic will retrieve the exact FAQ entry that addresses it, including the question context that disambiguates similar topics. Fixed-size chunking may split a question from its answer; sentence-level chunks make answers too granular; page-level chunks combine unrelated FAQ entries.

**Why A is wrong:** Uniform chunk length does not improve embedding quality — embeddings encode semantic content, not length properties. For FAQ pages, a fixed 512-token chunk may include the end of one FAQ entry and the beginning of another, producing a chunk that represents two unrelated Q&A topics. The embedding of that mixed chunk will be less focused than a single Q&A pair.

**Why C is wrong:** A 2–5 sentence answer split into individual sentence chunks loses the coherence of the answer and the contextual relationship to the question heading. A sentence like "This feature is available in enterprise plans" is meaningless without the preceding question that establishes what "this feature" refers to. Sentence-level granularity produces orphaned chunks for conversational Q&A content.

**Why D is wrong:** A page containing 15 FAQ entries has 15 distinct topics. Embedding all of them as a single chunk produces an embedding that represents an average of 15 topics — the embedding is diluted and will not match precisely against any specific user query. Retrieval precision collapses when chunks contain unrelated content.


---

## MCQ-2 — Chunk overlap purpose

**Difficulty:** novice
**Topic:** chunking_strategies

**Question:**
What is the primary purpose of adding overlap between consecutive chunks?

**Options:**
A. To reduce the total number of chunks needed to cover a document
B. To ensure that sentences or ideas spanning a chunk boundary are represented in at least one retrievable chunk
C. To improve embedding model performance by providing more context per chunk
D. To prevent duplicate document detection from flagging overlapping chunks as copies

**Correct answer:** B

**Explanation:**
When a document is split at a fixed boundary, a sentence or concept that straddles two chunks may be incomplete in both. Overlap (repeating some text at the start of the next chunk) ensures that content near chunk boundaries appears fully in at least one chunk and can be retrieved. Option A is incorrect — overlap increases total chunk count. Option C is a secondary benefit, not the primary purpose. Option D describes a deduplication system concern that is unrelated to why overlap is used.

**Why A is wrong:** Overlap does the opposite — it increases total chunk count because the overlapping text appears in two chunks. Developers who have not worked with chunking pipelines assume overlap is a compression technique rather than a coverage technique.

**Why C is wrong:** Providing more tokens to the embedding model per chunk is a secondary benefit of overlap. The primary reason is boundary continuity, not embedding quality. A developer who is focused on maximizing embedding quality might reach for C without recognizing that C is a side effect rather than the purpose.

**Why D is wrong:** Deduplication systems are concerned with detecting semantically or textually identical documents. Overlap is expected and intended — it is not a sign of duplicate documents. This option confuses the pipeline concern of overlap with the separate concern of document deduplication.

---

## MCQ-3 — Fixed-size vs. semantic chunking tradeoff

**Difficulty:** intermediate
**Topic:** chunking_strategies

**Question:**
A team is chunking a corpus of technical API documentation. They compare fixed-size chunking (500 tokens, 50-token overlap) against semantic chunking (split at paragraph and section boundaries). Which statement correctly describes the key tradeoff?

**Options:**
A. Fixed-size chunking produces higher retrieval precision because equal-length chunks produce more comparable embedding vectors
B. Semantic chunking preserves conceptual boundaries but produces variable-length chunks that may require more complex downstream handling; fixed-size chunking is predictable but may cut mid-sentence or mid-concept
C. Semantic chunking is always superior — fixed-size chunking is only used when no other option is available
D. Fixed-size chunking is superior for technical documentation because API docs have uniform structure

**Correct answer:** B

**Explanation:**
Semantic chunking (splitting at natural boundaries like paragraphs, sections, or sentences) preserves conceptual integrity — retrieved chunks are more likely to contain complete, coherent information. However, variable chunk lengths complicate downstream processing (e.g., fitting into LLM context windows, batching embeddings). Fixed-size chunking is simple and predictable but may cut mid-sentence, splitting a concept across two chunks. Neither is universally superior (eliminating C and D) — the right choice depends on document structure and downstream requirements.

**Why A is wrong:** Equal-length chunks do not produce more comparable embedding vectors. Embedding models encode semantic content, not positional or length features. A 500-token chunk about cryptography and a 500-token chunk about cooking produce distant embeddings despite equal length. The comparability claim has no basis in how embeddings work.

**Why C is wrong:** This is an absolutist claim that does not hold in practice. Fixed-size chunking is widely used in production because it is simple to implement, deterministic, and performs adequately for many document types. The choice between strategies depends on corpus structure, not a universal quality ranking.

**Why D is wrong:** "Uniform structure" is subjective and does not map to a clear chunking advantage. API documentation often has varied structure (overview sections, parameter tables, code examples, caveats) — fixed-size chunking would still cut across these elements mid-concept.

---

## MCQ-4 — Chunk size effect on retrieval

**Difficulty:** intermediate
**Topic:** chunking_strategies

**Question:**
A RAG developer increases chunk size from 256 tokens to 1024 tokens. What is the most likely effect on retrieval quality?

**Options:**
A. Retrieval precision improves because larger chunks contain more context, making them more informative
B. Retrieval precision may decrease because a larger chunk contains multiple topics, diluting the embedding signal and matching queries that are only partially relevant
C. Retrieval recall decreases because fewer total chunks exist in the index
D. Embedding quality improves because the model receives more tokens and produces richer representations

**Correct answer:** B

**Explanation:**
A larger chunk covers more content, which can dilute the embedding — the resulting vector represents an average of multiple topics rather than a focused concept. This means the chunk may score high similarity to a broader range of queries, reducing precision (returning chunks that are only partially relevant). Option A is the intuitive but incorrect response — more context does not improve embedding focus. Option C is technically true (fewer chunks exist) but conflates chunk count with recall. Option D incorrectly assumes more tokens always improve embedding quality; beyond a model's effective attention range, additional tokens add noise.

---

## MCQ-5 — Hierarchical chunking strategy

**Difficulty:** advanced
**Topic:** chunking_strategies

**Question:**
A legal document corpus contains long contracts. Small chunks (128 tokens) produce poor retrieval because individual clauses lack context; large chunks (1024 tokens) dilute the embedding signal. A developer proposes a hierarchical chunking strategy. Which description correctly captures how hierarchical chunking addresses this tradeoff?

**Options:**
A. Documents are chunked at two levels: small chunks for embedding/retrieval and large parent chunks for LLM context — the system retrieves small chunks by similarity, then returns the parent chunk as the LLM's context
B. Each document is embedded at full length for retrieval, then split into small chunks for the LLM prompt
C. The document is split into overlapping small chunks and non-overlapping large chunks, and both sets are indexed; the system retrieves from whichever index returns higher similarity scores
D. Small chunks are clustered into groups by topic, and each cluster is re-embedded as a single synthetic chunk for the final index

**Correct answer:** A

**Explanation:**
Hierarchical (parent-document) chunking separates retrieval granularity from context granularity: small chunks produce focused, discriminative embeddings for high-precision retrieval, while the parent chunk (containing the clause and its surrounding sections) provides the LLM with the broader context it needs to answer accurately. Option B embeds at full document length, which defeats the purpose of chunking for discriminative retrieval. Option C maintains two separate indexes with independent retrieval — this is a different architecture (dual-index retrieval) that does not solve the parent context problem. Option D describes clustering-based re-embedding, which is a topic modeling approach rather than hierarchical chunking.

**Why B is wrong:** Embedding a full document at retrieval time and then splitting it for the LLM inverts the architecture. Full-document embeddings produce poor retrieval precision because the single vector averages the semantics of the entire contract, not the specific clause the query is about. A developer who has seen document-level embedding in other pipelines may reach for this without recognizing that retrieval granularity and context granularity are separate problems.

**Why C is wrong:** Maintaining two parallel indexes and choosing between them by score sounds systematic but it does not solve the core problem: when the high-score winner is a small chunk, the LLM still lacks surrounding context. The architecture in C adds index infrastructure without bridging the retrieval-context granularity gap. Engineers who default to "more indexes, higher recall" mistake this for a retrieval optimization problem rather than a context delivery problem.

**Why D is wrong:** Clustering small chunks by topic and re-embedding them as synthetic aggregates is a form of topic modeling, not hierarchical chunking. It destroys the original clause boundaries and does not preserve the parent-child relationship needed to expand retrieved chunks back to their surrounding context. This option appeals to developers who have worked with topic models and assume cluster-level representations always improve retrieval.

---

## MCQ-6 — Table chunking and header loss

**Difficulty:** advanced
**Topic:** chunking_strategies

**Question:**
A pipeline chunks a financial report at 512 tokens. A revenue table spanning 800 tokens is split into two chunks at row 14. In production, queries about "Q3 revenue by region" consistently return the second chunk (rows 15–28), but the LLM cannot answer correctly. What is the most precise diagnosis?

**Options:**
A. The table's second chunk contains the relevant data but lacks the column headers that identify what each value represents, so the LLM receives numbers with no semantic labels
B. The 512-token chunk size is too small for financial tables; increasing to 1024 tokens will resolve the retrieval failure
C. The embedding of the second chunk scored lower than the first chunk because it lacks the keyword "revenue," causing retrieval to return the wrong chunk
D. Tables should always be excluded from RAG pipelines because structured data cannot be embedded meaningfully

**Correct answer:** A

**Explanation:**
When a table is split mid-body, the second chunk contains data rows without the header row that names the columns. The LLM receives a block of numbers and row labels (region names) but has no column context to understand what the numbers represent — Q1 vs Q3, actual vs forecast, USD vs percentage. This is not a retrieval failure (the right chunk was returned) but a context coherence failure caused by splitting structured data at a token boundary. The fix is table-aware chunking: treat each table as an atomic unit, or if it must split, repeat the header row at the start of each continuation chunk.

**Why B is wrong:** Increasing chunk size addresses the symptom (the split) but does not fix the architecture. Tables of arbitrary length will still be split. The correct fix is table-aware chunking logic that preserves headers, not a larger fixed size. An engineer who defaults to "increase chunk size when things break" will encounter the same failure with any table larger than the new limit.

**Why C is wrong:** The question states the second chunk was retrieved — the retrieval step worked. The failure is in generation, not retrieval. This option misdiagnoses a context coherence problem as a retrieval ranking problem. Developers who only debug retrieval metrics miss the downstream stage where the failure actually occurs.

**Why D is wrong:** Tables can be embedded meaningfully, especially when headers and row labels are intact. The failure here is a chunking boundary problem, not a fundamental incompatibility between tables and embeddings. Excluding all structured data from RAG is an overreaction that sacrifices coverage without addressing the root cause.

---

## MCQ-7 — Code block chunking at token boundary

**Difficulty:** advanced
**Topic:** chunking_strategies

**Question:**
A developer tools documentation corpus is chunked at 256 tokens with no special handling for code blocks. A Python class definition spanning 400 tokens is split: the first chunk contains the class declaration, docstring, and `__init__` method; the second chunk contains three additional methods starting mid-definition. What retrieval problem does this create?

**Options:**
A. Embedding quality degrades because code tokens are out-of-vocabulary for most embedding models trained on natural language
B. A query asking about one of the three methods in the second chunk may retrieve that chunk without any class or method signature context, making the retrieved code uninterpretable without knowing what class it belongs to
C. Python syntax errors in the split code prevent the vector database from indexing the chunk
D. The chunk containing `__init__` will always score higher for any query about the class because it contains the class name

**Correct answer:** B

**Explanation:**
When a code block is split at a token boundary mid-function or mid-class, continuation chunks lose the enclosing namespace context. A retrieved chunk showing three method bodies with no class declaration provides no indication of what class these methods belong to, what the constructor signature looks like, or what instance state they reference. The LLM may generate a plausible-sounding answer about the methods in isolation, but it cannot produce correct usage examples without the class context. Code-aware chunking strategies either keep code blocks atomic or inject a synthetic header (e.g., `# class MyClass`) at the start of continuation chunks.

**Why A is wrong:** Modern embedding models are trained on code (CodeBERT variants, or general models like text-embedding-3 trained on mixed corpora). Out-of-vocabulary is not the issue; the problem is structural context loss, not vocabulary mismatch. Assuming embedding models cannot handle code is a misconception that leads developers to exclude code from their index entirely.

**Why C is wrong:** Vector databases store text as-is and then embed it. Syntactically incomplete code does not cause indexing failures — it simply produces a vector that represents the incomplete fragment. The problem is semantic, not structural.

**Why D is wrong:** Retrieval ranking is based on query-chunk similarity, not on which chunk contains the class name. A query about a specific method will likely match the chunk containing that method, not the `__init__` chunk. This option reflects a misunderstanding of how embedding similarity works — keyword presence does not dominate semantic similarity scoring.

---

## MCQ-8 — Mixed-content pipeline losses

**Difficulty:** expert
**Topic:** chunking_strategies

**Question:**
A corpus of product manuals contains pages with mixed content: narrative paragraphs, specification tables, and embedded diagrams with caption text. The pipeline uses text-only chunking (PDF text extraction, fixed 512-token chunks). After deployment, users report that queries about visual layouts and diagram-referenced specifications return incomplete or incorrect answers. What does the pipeline silently lose, and what is the architectural remedy?

**Options:**
A. The pipeline loses the spatial relationship between diagrams and their reference text — captions are extracted as floating text fragments with no association to the image content; tables may be linearized incorrectly, destroying column alignment. Remedy: use a multimodal document parser (e.g., layout-aware PDF extraction or vision-based OCR) that preserves spatial structure and associates captions with image metadata before chunking
B. The pipeline loses formatting metadata (bold, italic, font size) that signals semantic importance. Remedy: extract formatting as additional embedding features alongside the text
C. The pipeline loses diagram content entirely. Remedy: run a separate image-captioning model on each diagram and append the generated captions to the chunk nearest the diagram in the text flow
D. The pipeline loses table row order because PDF text extraction reads tables column-by-column instead of row-by-row. Remedy: replace fixed chunking with sentence-level chunking to preserve row boundaries

**Correct answer:** A

**Explanation:**
Text-only PDF extraction has two structural losses for mixed-content pages: (1) diagrams are simply absent from the text stream — only their captions survive, and captions without their image are semantically incomplete; (2) tables are often linearized in reading order (left-to-right, top-to-bottom), which may produce row-column mismatches that corrupt table semantics before chunking even occurs. The remedy is layout-aware parsing — tools that understand page structure can preserve table cell positions and associate image bounding boxes with adjacent text. Option C is partially correct (running captioning) but does not address table linearization or caption-image association. Option B describes a real but minor concern. Option D is wrong about column-by-column extraction — this depends on the parser, and sentence-level chunking does not fix linearization.

**Why B is wrong:** Formatting metadata (bold, font size) can signal emphasis but it does not represent content. Embedding "bold text" as a feature would require a custom embedding model. The primary loss is structural and spatial, not typographic. Developers who obsess over rich-text metadata miss the larger data integrity problem.

**Why C is wrong:** Appending auto-generated captions is a useful supplement but it is not a complete remedy. The captions describe image content but do not restore table structure or spatial relationships between text and diagrams. A pipeline built on C will still fail for queries that depend on table data from pages where tables were linearized incorrectly.

**Why D is wrong:** PDF extraction does not universally read tables column-by-column; it depends on the extraction library and the PDF's internal encoding. Sentence-level chunking does not address column alignment — it is still operating on the already-corrupted linearized text. The fix must happen at the parsing layer, before chunking.

---

## MCQ-9 — Semantic chunking CPU cost at scale

**Difficulty:** expert
**Topic:** chunking_strategies

**Question:**
A team replaces fixed-size chunking with semantic chunking using a spaCy sentence tokenizer to split at sentence boundaries. In development (10,000 documents), the indexing pipeline runs in 4 minutes. At production scale (1,000,000 documents), the team estimates 400 minutes. A senior engineer flags this as unacceptable and asks for a production-viable alternative. What is the correct diagnosis and the most operationally sound fix?

**Options:**
A. spaCy sentence tokenization is O(n²) in document length; switching to a simpler regex-based sentence splitter achieves equivalent chunking quality with O(n) complexity
B. spaCy runs a full NLP pipeline (tokenizer, tagger, parser, NER) by default; most of this work is unnecessary for sentence boundary detection alone. Fix: disable unused pipeline components (`nlp.select_pipes`) or replace spaCy with a lightweight sentence boundary detector (e.g., PunktSentenceTokenizer or regex) and parallelize the chunking stage across CPU workers
C. The indexing pipeline is I/O-bound at scale; the spaCy step is not the bottleneck. Fix: use async document loading to overlap I/O and CPU work
D. spaCy requires a GPU for production-scale NLP; moving the tokenization step to a GPU cluster resolves the throughput issue

**Correct answer:** B

**Explanation:**
spaCy's default `en_core_web_sm` or `en_core_web_lg` pipelines run tokenization, part-of-speech tagging, dependency parsing, and named entity recognition even when only sentence boundaries are needed. Parsing and NER alone can account for 60–80% of CPU time. Using `nlp.select_pipes(enable=["senter"])` or `nlp.disable_pipes(["ner", "parser"])` with the `senter` component drops most overhead while retaining sentence boundary detection. For even simpler corpora, a regex-based splitter or NLTK's Punkt tokenizer achieves similar quality at a fraction of the cost. Parallelizing across CPU workers is the second lever. Option A is incorrect about O(n²) complexity — spaCy tokenization is O(n). Option C assumes I/O bottleneck without evidence. Option D is wrong — spaCy is CPU-native and does not benefit from GPU for tokenization.

**Why A is wrong:** spaCy's tokenization is O(n), not O(n²). The correct diagnosis is that the overhead comes from the default pipeline running unnecessary components (parser, NER) rather than algorithmic complexity. A developer who assumes the problem is algorithmic will switch to regex and gain some speedup, but will miss the real lever: disabling unused pipeline stages in spaCy itself.

**Why C is wrong:** At 1M documents, the chunking step is CPU-bound because sentence tokenization is compute-heavy relative to disk read time for plain text. Claiming it is I/O-bound without profiling the actual pipeline is a diagnostic shortcut that leads to the wrong fix. Async I/O helps ingestion, not text processing throughput.

**Why D is wrong:** spaCy's core NLP components (tokenizer, parser, NER) are CPU-only — they do not use GPU acceleration. GPU usage in spaCy is limited to transformer-backed models (`en_core_web_trf`), which are slower for this task, not faster. Recommending a GPU cluster for tokenization is both architecturally incorrect and cost-inefficient.

---

## MCQ-10 — Overlap percentage and precision degradation

**Difficulty:** advanced
**Topic:** chunking_strategies

**Question:**
A developer increases chunk overlap from 10% to 50% (from 50 tokens to 250 tokens on 500-token chunks) to reduce boundary split failures. After re-indexing and evaluating with RAGAS, context_precision drops from 0.78 to 0.61. What is the most precise explanation for this degradation?

**Options:**
A. Higher overlap increases total chunk count, which raises the probability that the ANN index returns approximate rather than exact nearest neighbors, reducing precision
B. With 50% overlap, nearly identical text appears in consecutive chunks. When multiple adjacent chunks score high similarity to a query, the retriever fills its top-k results with redundant variants of the same passage rather than distinct, complementary information — injecting duplicate context into the LLM prompt and lowering context_precision
C. The RAGAS context_precision metric penalizes chunk count; more chunks in the index directly reduces the score regardless of retrieval quality
D. 50% overlap causes the embedding model to produce near-identical vectors for adjacent chunks, triggering deduplication logic in the vector database that removes valid chunks from the index

**Correct answer:** B

**Explanation:**
Context_precision measures how much of the retrieved context is relevant to answering the query — it penalizes retrieving redundant or irrelevant passages. With 50% overlap, chunk N and chunk N+1 share 250 tokens of content. Both will embed to very similar vectors and score nearly equally for any query that matches the shared region. The top-k retriever will return both chunks, injecting 250 tokens of duplicated text into the LLM prompt. This reduces context_precision because the retrieved set contains highly redundant material rather than the k most distinct relevant passages. The fix is to use overlap conservatively (10–15%) or to deduplicate retrieved chunks by similarity score before injection. Option A describes a real ANN approximation effect but it does not scale with overlap percentage in this way. Option C is incorrect — RAGAS context_precision does not penalize raw chunk count. Option D is incorrect — vector databases do not deduplicate stored vectors automatically.

**Why A is wrong:** ANN recall degradation is driven by index construction parameters (ef_search, M in HNSW) and corpus size, not overlap percentage. Overlap at 50% does not meaningfully change the total number of vectors relative to the index structure parameters. The precision drop is a retrieval content problem (duplicate passages), not an index accuracy problem.

**Why C is wrong:** RAGAS context_precision is computed as the fraction of retrieved chunks that are relevant to the ground-truth answer — it is a ratio, not penalized by absolute chunk count. More chunks in the index does not directly change the score. This misunderstanding of how RAGAS metrics are computed is a common source of incorrect diagnosis.

**Why D is wrong:** Vector databases store every vector that is explicitly inserted. They do not apply automatic deduplication based on embedding similarity — that would require computing pairwise distances across the entire index on every insert, which is prohibitively expensive. Deduplication must be built explicitly in the ingestion pipeline, not assumed from the database layer.

---

## MCQ-16 — Large chunk size relative to query length

**Difficulty:** intermediate
**Topic:** chunking_strategies

**Question:**
A RAG system is indexed with 1024-token chunks. Most user queries are 10–20 tokens. The system retrieves top-5 chunks per query. RAGAS shows context_recall = 0.88 but faithfulness = 0.61. What is the most precise explanation for the faithfulness degradation?

**Options:**
A. The embedding model cannot handle queries shorter than 50 tokens, so the query vectors are low-quality and retrieve the wrong chunks, injecting irrelevant context that the LLM uses to hallucinate
B. Large chunks contain many topics per chunk. Each retrieved chunk is genuinely related to the query topic (hence high recall), but also contains substantial off-topic content. The LLM receives five 1024-token chunks — up to 5120 tokens of context — where only a small fraction is relevant to the 15-token query. The LLM generates using all available context including the noise, producing claims not supported by the query-relevant portion of the retrieved text, which RAGAS scores as unfaithful
C. A 1024-token chunk exceeds most embedding models' maximum input length, so chunks are silently truncated during indexing, causing the second half of each chunk to be invisible to retrieval
D. The top-5 retrieval setting is too low for large chunks — increasing top-K to top-20 would give the LLM enough context to generate faithful answers

**Correct answer:** B — Retrieval still works (recall is high) because a 1024-token chunk about a topic will embed near any query about that topic. But the same chunk also contains sub-topics, caveats, examples, and tangential discussion that have nothing to do with the specific 15-token query. The LLM treats the entire retrieved context as relevant grounding. Claims generated from the off-topic portions of the chunks are not supported by the query-relevant content — faithfulness drops. The fix is smaller chunks (256–400 tokens) so each retrieved unit is more focused, or parent-child chunking where a small child chunk drives retrieval and a moderately-sized parent provides generation context.

**Why each wrong answer is wrong:**
- **A:** Embedding models handle short queries normally. Short queries produce valid embedding vectors that retrieve semantically relevant documents — the mechanism is robust to query length. Low-quality short-query embeddings are not a documented failure mode of general-purpose embedding models trained on mixed-length corpora.
- **B:** This is the correct answer.
- **C:** Many production embedding models support 512–8192 token inputs, and 1024 tokens is within range for models like text-embedding-3 (8191 token limit). Even when truncation occurs, it is a chunk coverage problem that would reduce recall, not faithfulness. This option describes a different failure mode — and one that would be caught by monitoring the embedding API's tokenization.
- **D:** Increasing top-K from 5 to 20 with 1024-token chunks injects up to 20,480 tokens of context — far exceeding most LLM context windows. More context here makes faithfulness worse, not better, by amplifying the noise-to-signal ratio. The problem is chunk content quality, not retrieval quantity.

