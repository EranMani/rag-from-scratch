# MCQ Bank — vector_databases
# Topic: vector_databases
# Phase: 2 (Core Components)
# Questions: 5 (2 beginner, 2 intermediate, 1 advanced)
# Last updated: 2026-05-19 (Commit 33)

---

## MCQ-1 — Vector database primary function

**Difficulty:** beginner
**Topic:** vector_databases

**Question:**
What problem does a vector database solve that a traditional relational database cannot?

**Options:**
A. Storing large binary files such as PDFs and images alongside their metadata
B. Efficiently finding the most semantically similar items to a query vector across millions of stored vectors
C. Distributing data across multiple servers to handle high write throughput
D. Enforcing schema constraints on unstructured text data before storage

**Correct answer:** B

**Explanation:**
Vector databases are purpose-built for nearest-neighbor search in high-dimensional embedding spaces — finding the k most similar vectors to a query vector. Relational databases have no native operator for this; they can store vectors as arrays but would require a full table scan with distance computation for every query. Options A, C, and D describe concerns (file storage, distributed writes, schema enforcement) that both traditional and vector databases can handle and are not the core differentiator.

---

## MCQ-2 — ANN vs. exact nearest neighbor

**Difficulty:** beginner
**Topic:** vector_databases

**Question:**
Most production vector databases use Approximate Nearest Neighbor (ANN) search rather than exact nearest neighbor search. Why?

**Options:**
A. ANN produces higher-quality similarity scores than exact search for high-dimensional vectors
B. Exact nearest neighbor search requires the entire index to be loaded into RAM, making it impractical for large corpora
C. ANN trades a small amount of recall for a large reduction in query latency, making it practical at scale
D. Exact nearest neighbor search is only available in commercial databases, not open-source options

**Correct answer:** C

**Explanation:**
Exact nearest neighbor search computes the distance from the query to every stored vector, which becomes prohibitively slow as the corpus grows (O(n) per query). ANN algorithms (such as HNSW or IVF) use index structures that can skip large portions of the vector space, returning results that are very close to the true nearest neighbors in a fraction of the time. The tradeoff is recall — a small percentage of true nearest neighbors may be missed. Options A, B, and D are incorrect: ANN does not improve score quality (A), exact search is available in open-source tools (D), and the RAM concern (B) applies to ANN indexes too.

---

## MCQ-3 — HNSW index properties

**Difficulty:** intermediate
**Topic:** vector_databases

**Question:**
Which statement correctly describes a key property of the HNSW (Hierarchical Navigable Small World) index?

**Options:**
A. HNSW is an inverted index that maps vector dimensions to document lists, optimized for sparse vectors
B. HNSW builds a layered graph structure where higher layers enable long-range navigation and lower layers enable fine-grained neighbor search
C. HNSW compresses vectors using product quantization, trading accuracy for lower memory usage
D. HNSW is a tree-based index that partitions the vector space into Voronoi cells for fast nearest-neighbor lookup

**Correct answer:** B

**Explanation:**
HNSW (Hierarchical Navigable Small World) constructs a multi-layer graph. The top layers have sparse long-range connections that allow rapid traversal across the vector space; the bottom layer has dense short-range connections for precise neighbor identification. Search starts at the top layer, narrows down through layers, and terminates at the bottom with the final candidates. Option A describes a sparse inverted index (used in BM25, not dense ANN). Option C describes IVF with product quantization. Option D describes a KD-tree or ball-tree structure.

---

## MCQ-4 — Metadata filtering and vector search

**Difficulty:** intermediate
**Topic:** vector_databases

**Question:**
A RAG system needs to retrieve only documents from a specific department and published after a given date, in addition to semantic similarity. How should a vector database handle this?

**Options:**
A. Perform vector similarity search across all documents, then filter the results in application code by metadata fields
B. Use metadata filtering at the index level — the vector database filters candidates by metadata predicates before or during ANN search, so only eligible documents are candidates
C. Create separate vector indexes per department and per time period, then query the appropriate index at runtime
D. Encode metadata fields as additional dimensions in the embedding vector so the similarity search naturally excludes off-topic documents

**Correct answer:** B

**Explanation:**
Modern vector databases support metadata filtering natively — predicates on structured fields (e.g., `department = "engineering" AND date > 2024-01-01`) are applied during ANN search, not after. This is far more efficient than post-filtering (A), which may return a large result set of ineligible documents before applying filters. Separate per-department indexes (C) would work but scale poorly with many metadata combinations. Encoding metadata as embedding dimensions (D) would corrupt the semantic space — the embedding model is not designed to handle mixed semantic + structured fields.

---

## MCQ-5 — Index rebuild and staleness

**Difficulty:** advanced
**Topic:** vector_databases

**Question:**
A production RAG system ingests new documents continuously. The vector database uses an HNSW index. A developer proposes rebuilding the full HNSW index nightly to maintain search quality. What is the precise risk this proposal is designed to address, and what is its main operational tradeoff?

**Options:**
A. Risk: new vectors inserted incrementally degrade the HNSW graph connectivity over time, reducing recall. Tradeoff: a full rebuild is expensive and temporarily unavailable during construction
B. Risk: the embedding model's vocabulary drifts as new documents are added, causing older vectors to become incompatible. Tradeoff: rebuilding requires re-embedding all documents
C. Risk: HNSW indexes do not support deletion, so removed documents must be physically purged via a rebuild. Tradeoff: any documents added after the rebuild starts are excluded from the new index
D. Risk: incremental inserts cause vector dimension count to increase if new documents introduce longer token sequences. Tradeoff: the rebuild must use a different embedding model

**Correct answer:** A

**Explanation:**
HNSW indexes are designed for efficient insertions, but incremental additions over time can produce suboptimal graph structures — newly inserted nodes may have fewer long-range connections than nodes present during initial construction, gradually reducing recall quality. A full rebuild recreates the graph from scratch with optimal connectivity across all nodes. The operational cost is (1) rebuild time scales with corpus size, and (2) the index may need to be served from the old copy during rebuild (requiring a swap). Options B and D are incorrect — embedding model vocabulary does not drift, and vector dimensions are fixed by model choice. Option C overstates the deletion limitation; HNSW supports soft deletion with tombstone marking.

