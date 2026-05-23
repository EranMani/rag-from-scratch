# RAG Curriculum Map
# Project: rag-from-scratch
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-23 (Commit 47)

---

## Zero-to-Hero Arc

This curriculum takes a learner from zero background to the ability to design, build,
evaluate, and operate a production RAG system. The arc is strictly sequential at the
phase level — you cannot advance to Phase 2 without passing the Phase 1 gate.

Within a phase, topics can be studied in parallel, but the gate requires all phase
topics to pass the score threshold before the learner advances.

```
Phase 1 — Foundations
  └── embeddings_and_similarity    (entry: zero)
  └── rag_pipeline_architecture    (entry: zero; benefits from embeddings first)
      ↓ Phase 1 Gate
Phase 2 — Core Components
  ├── chunking_strategies          (entry: Phase 1 gate)
  ├── vector_databases             (entry: Phase 1 gate)
  ├── retrieval_methods            (entry: Phase 1 gate + vector_databases recommended first)
  ├── context_and_prompting        (entry: Phase 1 gate + rag_pipeline_architecture required)
  └── document_ingestion           (entry: Phase 1 gate + rag_pipeline_architecture required)
      ↓ Phase 2 Gate
Phase 3 — Production
  ├── evaluation_and_metrics       (entry: Phase 2 gate)
  └── production_patterns          (entry: Phase 2 gate)
      ↓ Phase 3 Gate (curriculum complete)
```

---

## Phase 1 — Foundations

### Topic: `embeddings_and_similarity`

**Phase:** 1
**Description:** Understand how text is transformed into dense numerical vectors, how
geometric relationships encode semantic meaning, and how similarity is measured in
vector space. This topic is the mathematical bedrock of all RAG retrieval.

**Prerequisites:**
- None (entry point)

**Learning Objectives:**
1. Explain what an embedding is without reference to any framework — in terms of dimensionality,
   geometry, and what the vector components represent.
2. Describe how cosine similarity differs from Euclidean distance and when each is appropriate
   for semantic comparison.
3. Trace how two semantically similar sentences end up as neighboring points in vector space,
   and two unrelated sentences end up far apart.
4. Identify the limitations of embedding-based search: out-of-vocabulary terms, domain shift,
   polysemy, and the curse of dimensionality at high scales.
5. Explain how the choice of embedding model affects retrieval quality (model dimension,
   training corpus, normalization behavior).

**Typical Misconceptions:**
- "The embedding vector dimensions each correspond to a specific word or concept." (Dimensions
  are learned latent features — they have no human-interpretable meaning.)
- "Cosine similarity of 1.0 means the sentences say the same thing." (It means the vectors
  point in the same direction — identical meaning is a strong signal, but near-duplicate
  phrasing can produce high cosine similarity with different semantics.)
- "You can always use any embedding model for any domain." (Models trained on general web text
  underperform on specialized corpora — legal, medical, code — where domain vocabulary differs.)
- "More dimensions always means better embeddings." (Beyond a threshold, extra dimensions add
  noise and increase compute cost without improving downstream retrieval quality.)

---

### Topic: `rag_pipeline_architecture`

**Phase:** 1
**Description:** Understand the two-phase RAG architecture — indexing and querying — and how
they connect. Learn how documents flow from raw text to stored vectors, how a user query
triggers retrieval, and how retrieved context is injected into a generation prompt.

**Prerequisites:**
- `embeddings_and_similarity` (recommended first — the pipeline uses embeddings throughout)

**Learning Objectives:**
1. Draw the full RAG pipeline from raw document to final LLM response, labeling each
   component (loader, splitter, embedder, vector store, retriever, prompt template, LLM).
2. Distinguish the indexing phase (offline, batch) from the query phase (online, real-time)
   and explain why they are kept separate.
3. Describe what happens when the retrieved context is wrong or irrelevant, and trace where
   in the pipeline that failure originates.
4. Explain the role of the prompt template in bridging retrieval results to generation, and
   what information it must always contain.
5. Compare RAG architectures to fine-tuning: when each approach is appropriate and what
   tradeoffs each makes in terms of freshness, cost, and hallucination risk.

**Typical Misconceptions:**
- "RAG means the LLM searches the internet." (RAG retrieves from a private, pre-indexed
  document store — not the web, unless explicitly designed that way.)
- "The LLM reads all the documents every time a question is asked." (Only the top-K retrieved
  chunks are injected into the prompt — the LLM never sees the full corpus at query time.)
- "If retrieval returns the right document, the answer is always correct." (The LLM can still
  hallucinate, misread the context, or fail to synthesize across multiple chunks correctly.)
- "Indexing only happens once." (Production systems re-index when documents are added, updated,
  or deleted — index freshness is an operational concern.)

---

## Phase 2 — Core Components

### Topic: `chunking_strategies`

**Phase:** 2
**Description:** Understand how raw documents are split into retrievable units (chunks),
how different splitting strategies affect recall and precision, and how overlap and token
budgets interact with downstream retrieval quality.

**Prerequisites:**
- Phase 1 gate passed
- `rag_pipeline_architecture` (chunking occurs in the indexing phase)

**Learning Objectives:**
1. Contrast fixed-size chunking with semantic chunking: what each optimizes for and when
   each is the better choice.
2. Explain what chunk overlap is, why it exists, and how to reason about the right overlap
   percentage for a given document type.
3. Define the token budget constraint on chunks and describe how exceeding it affects
   retrieval and generation.
4. Trace how a poor chunking strategy causes retrieval failures — e.g., splitting a table
   across chunks, or producing chunks that lack their own context.
5. Describe at least two domain-specific chunking strategies (e.g., by paragraph boundary,
   by Markdown header, by sentence boundary) and when each is appropriate.

**Typical Misconceptions:**
- "Smaller chunks are always better because they're more precise." (Very small chunks often
  lack enough context for the retrieval model to judge relevance — precision gains can
  disappear due to missing context.)
- "Overlap is just redundancy and wastes storage." (Overlap preserves continuity across
  chunk boundaries, preventing key information that spans two chunks from being lost.)
- "The same chunking strategy works for all document types." (Code, legal documents, tables,
  and prose all have different natural boundary structures that naive fixed-size splitting
  ignores.)

---

### Topic: `vector_databases`

**Phase:** 2
**Description:** Understand how vectors are stored, indexed, and retrieved at scale. Learn
the tradeoffs between approximate nearest-neighbor index types (HNSW vs. IVF), metadata
filtering, and collection design decisions.

**Prerequisites:**
- Phase 1 gate passed
- `embeddings_and_similarity` (vector databases store and query embedding vectors)

**Learning Objectives:**
1. Explain the ANN (approximate nearest neighbor) vs. exact nearest neighbor tradeoff: why
   approximate search exists and what is sacrificed for speed.
2. Describe HNSW (Hierarchical Navigable Small World) graph construction and query mechanics
   at a conceptual level — why it's fast and where it fails.
3. Describe IVF (Inverted File Index) clustering approach and contrast it with HNSW on speed,
   recall, and memory usage.
4. Explain how metadata filtering interacts with vector search — pre-filter vs. post-filter
   semantics and when each degrades recall.
5. Design a collection schema for a real-world use case: choose appropriate fields, index
   type, distance metric, and replication strategy.

**Typical Misconceptions:**
- "All vector databases are the same — just pick the most popular one." (Index types, filtering
  semantics, and consistency models differ significantly between systems — choice affects both
  performance and correctness.)
- "ANN search always returns the true nearest neighbor." (ANN trades recall for speed —
  the returned vectors are approximate, meaning the true nearest neighbor may occasionally
  be missed.)
- "Vector databases replace relational databases." (They complement them — vector DBs excel at
  semantic search; relational DBs handle structured queries, joins, and ACID transactions.)
- "Metadata filtering is free." (Pre-filtering reduces the candidate set before ANN search,
  which can hurt recall. Post-filtering applies after search, which can return fewer than K
  results. Both have hidden costs.)

---

### Topic: `retrieval_methods`

**Phase:** 2
**Description:** Understand the full spectrum of retrieval strategies beyond simple dense
vector search: sparse retrieval (BM25), hybrid search, reranking, MMR, multi-query
expansion, and HyDE. Learn when each method addresses which failure mode.

**Prerequisites:**
- Phase 1 gate passed
- `vector_databases` (retrieval operates against a vector/keyword store)

**Learning Objectives:**
1. Explain BM25 (sparse retrieval) — how it scores documents, what "TF-IDF weighting" means
   intuitively, and in which scenarios it outperforms dense retrieval.
2. Describe hybrid search: how sparse and dense signals are combined and what fusion
   strategies exist (RRF, weighted sum).
3. Explain cross-encoder reranking: why a first-stage retriever is needed, and what a
   reranker adds in terms of relevance at the cost of latency.
4. Define MMR (Maximal Marginal Relevance) and explain why diversity in retrieved results
   sometimes matters more than pure relevance.
5. Explain multi-query expansion and HyDE (Hypothetical Document Embeddings): what problem
   each solves and what risks each introduces.

**Typical Misconceptions:**
- "Dense retrieval is always better than BM25 because it understands meaning." (Dense
  retrieval underperforms BM25 on exact-match queries, rare terms, and highly technical
  vocabulary where BM25's keyword frequency weighting excels.)
- "Reranking is just retrieving more documents." (A reranker is a separate cross-encoder
  model that scores (query, doc) pairs jointly — it is computationally expensive and
  qualitatively different from first-stage retrieval.)
- "HyDE always improves results." (HyDE generates a hypothetical answer to use as the query
  embedding — if the LLM generates a hallucinated or off-topic hypothetical, retrieval
  quality degrades.)

---

### Topic: `context_and_prompting`

**Phase:** 2
**Description:** Understand how to construct effective prompts for RAG generation: how to
inject retrieved context, manage context window constraints, reduce hallucination risk, and
design prompt templates that produce consistent, grounded responses.

**Prerequisites:**
- Phase 1 gate passed
- `rag_pipeline_architecture` (prompting occurs at the generation stage)

**Learning Objectives:**
1. Describe the anatomy of a RAG prompt: system instruction, retrieved context block, user
   question, and output format directive — and explain why each element is present.
2. Explain context window management: what happens when retrieved chunks exceed the context
   limit, and how to prioritize or truncate gracefully.
3. Identify at least three prompt design patterns that reduce hallucination (e.g., explicit
   "answer only from context" instruction, uncertainty signaling, citation formatting).
4. Explain why prompt template consistency matters for evaluation: how variable templates
   make it impossible to isolate retrieval quality from generation quality.
5. Describe how different LLMs respond differently to the same RAG prompt and what
   prompt-level controls can compensate for model differences.

**Typical Misconceptions:**
- "Just put the documents in the prompt and the LLM will figure it out." (Unstructured context
  injection leads to the model ignoring key passages, blending context with world knowledge,
  or producing overlong responses.)
- "A longer context window means you can skip chunking and just inject whole documents."
  (Even with 100K+ token windows, LLMs exhibit "lost in the middle" behavior — they attend
  less to information in the middle of very long contexts.)
- "Telling the LLM not to hallucinate is sufficient." (Instruction-level hallucination
  mitigation helps but does not eliminate the problem — retrieval quality and prompt structure
  both matter independently.)

---

### Topic: `document_ingestion`

**Phase:** 2
**Description:** Understand how raw documents flow into a RAG pipeline — format parsing
(PDF, HTML, DOCX, TXT, CSV), metadata extraction, encoding handling, and how document
structure affects downstream chunking quality. This topic is the practical entry point
for building any real RAG system.

**Prerequisites:**
- Phase 1 gate passed
- `rag_pipeline_architecture` (document loading occurs in the indexing phase)

**Learning Objectives:**
1. Identify the components of a document loader and explain what each extracts (text,
   metadata, structure).
2. Describe at least three format-specific parsing challenges (e.g., PDF table extraction,
   HTML tag noise, DOCX embedded images) and their mitigations.
3. Explain how encoding issues (UTF-8 vs. Latin-1, BOM markers) cause silent data loss in
   ingestion pipelines.
4. Trace how a document's structural elements (headers, tables, page breaks) affect chunking
   quality downstream.
5. Describe two loader failure modes — silent data loss vs. hard error — and how to detect
   each in a production pipeline.

**Typical Misconceptions:**
- "Any text extracted from a PDF is correct." (PDF text extraction is lossy — tables,
  multi-column layouts, and scanned pages require special handling.)
- "Metadata doesn't matter for retrieval." (Source, page number, and timestamp metadata
  are critical for filtering, citation, and index freshness tracking.)
- "A document loader and a text splitter do the same job." (The loader extracts raw content;
  the splitter decides how to partition it — they are separate pipeline stages with different
  failure modes.)

---

## Phase 3 — Production

### Topic: `evaluation_and_metrics`

**Phase:** 3
**Description:** Understand how to measure RAG system quality rigorously: RAGAS metrics
(faithfulness, answer relevancy, context precision, context recall), offline vs. online
evaluation, and how to use metrics to identify which pipeline stage is failing.

**Prerequisites:**
- Phase 2 gate passed

**Learning Objectives:**
1. Define faithfulness in RAGAS: what it measures, how it is computed, and what a low
   faithfulness score indicates about the generation stage.
2. Define answer relevancy in RAGAS: how it differs from faithfulness and what a low score
   indicates about the retrieval or prompt stage.
3. Define context precision and context recall: how each is computed and what failure mode
   each surfaces (over-retrieval vs. under-retrieval).
4. Design an evaluation dataset for a RAG system: how to construct (question, ground truth
   context, ground truth answer) triples and why ground truth quality matters.
5. Explain the difference between offline evaluation (against a labeled test set) and online
   evaluation (production traffic signals), and when each is actionable.

**Typical Misconceptions:**
- "High user satisfaction means the RAG system is working well." (User ratings are a lagging,
  biased signal — a confidently wrong answer often receives high ratings.)
- "RAGAS scores are absolute — a faithfulness of 0.8 is always good." (Scores are relative
  to the task domain and baseline — a 0.8 on a medical QA system may be dangerously low.)
- "You only need to evaluate the final answer." (Evaluating at the retrieval stage separately
  from the generation stage is critical — without it, you cannot distinguish a retrieval
  failure from a generation failure.)

---

### Topic: `production_patterns`

**Phase:** 3
**Description:** Understand the operational concerns of a live RAG system: caching strategies,
async pipeline design, observability instrumentation, cost control levers, and common failure
modes at scale.

**Prerequisites:**
- Phase 2 gate passed
- `evaluation_and_metrics` (recommended first — production monitoring requires metric
  definitions)

**Learning Objectives:**
1. Describe semantic caching: how it differs from exact-match caching, how similarity
   thresholds are set, and what the failure modes are.
2. Explain async pipeline design for RAG: where async boundaries belong, what blocking
   operations to avoid on the hot path, and how queue-based architectures decouple indexing
   from serving.
3. List the minimum observability instrumentation for a RAG system: which latencies to
   trace, which retrieval signals to log, and how to connect traces to quality metrics.
4. Identify the three primary cost drivers in a RAG system (embedding calls, LLM tokens,
   vector store queries) and describe a concrete mitigation strategy for each.
5. Describe at least three production failure modes (e.g., index staleness, embedding model
   version drift, context length overflow under high query complexity) and their detection
   and mitigation strategies.

**Typical Misconceptions:**
- "If it works in development, it will work in production." (Development datasets are small,
  clean, and static — production surfaces index staleness, query distribution shift,
  throughput limits, and cost surprises that development never exercises.)
- "Caching responses is always safe." (RAG responses are context-sensitive — a cached answer
  to a query may become wrong when the underlying documents are updated. Cache invalidation
  strategy is mandatory.)
- "Observability means logging the final answer." (Useful RAG observability traces the entire
  path: query received, retrieval latency, chunks returned, prompt token count, generation
  latency, and output token count — along with quality signals.)

---

## Curriculum Summary

| Slug | Phase | Level | Key Concept |
|------|-------|-------|-------------|
| `embeddings_and_similarity` | 1 | Foundations | Vectors, cosine similarity, semantic search |
| `rag_pipeline_architecture` | 1 | Foundations | Indexing loop, query loop, context injection |
| `chunking_strategies` | 2 | Core | Fixed vs. semantic, overlap, token budgets |
| `vector_databases` | 2 | Core | HNSW, IVF, ANN tradeoffs, metadata filtering |
| `retrieval_methods` | 2 | Core | BM25, hybrid, reranking, MMR, HyDE |
| `context_and_prompting` | 2 | Core | Prompt anatomy, window management, grounding |
| `document_ingestion` | 2 | Core | Format parsing, metadata, encoding, structure |
| `evaluation_and_metrics` | 3 | Production | RAGAS, faithfulness, precision, recall |
| `production_patterns` | 3 | Production | Caching, async, observability, cost |
