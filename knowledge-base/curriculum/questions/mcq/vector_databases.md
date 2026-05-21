# MCQ Bank — vector_databases
# Topic: vector_databases
# Phase: 2 (Core Components)
# Questions: 10 (2 beginner, 4 intermediate, 2 advanced, 2 expert)
# Last updated: 2026-05-21 (Commit 45)

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

**Why A is wrong:** Storing large binary files (PDFs, images) is a problem solved by object storage (S3, GCS, blob storage) and is equally outside the core function of a vector database as a relational database. A developer who reaches for a vector database to store raw documents has confused the vector index (which stores embeddings and metadata) with a document store. In a RAG system, raw documents are stored separately and the vector database stores only the embeddings and chunk text.

**Why C is wrong:** Distributed write throughput is a scalability concern addressed by partitioning and replication strategies available in both relational and vector databases. It is not unique to vector databases. Choosing a vector database on the basis of write throughput rather than similarity search capability reflects a fundamental misunderstanding of what problem the technology was designed to solve.

**Why D is wrong:** Schema enforcement on unstructured text is a data governance concern addressed at the application or pipeline layer before data enters any database. Vector databases do store metadata alongside embeddings (allowing structured filtering), but "enforcing schema constraints on unstructured text" is not their defining function and is not something they do better than a relational database.

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

**Why A is wrong:** ANN algorithms trade a small amount of recall (the chance of missing the true nearest neighbor) for a large reduction in latency. They do not produce higher-quality similarity scores — the numerical cosine similarity value between a query and a returned vector is independent of whether the search was exact or approximate. Believing ANN improves quality is a dangerous misconception because it inverts the actual tradeoff and leads developers to choose ANN when recall guarantees are needed.

**Why B is wrong:** The RAM constraint applies equally to ANN indexes — an HNSW index for millions of vectors requires substantial RAM for the graph structure and vector data. Exact search libraries (like FAISS flat index) can be memory-mapped or streamed from disk; the RAM concern does not cleanly distinguish exact from approximate search. Choosing ANN specifically to address RAM constraints is the wrong reason and does not represent the actual engineering tradeoff.

**Why D is wrong:** Exact nearest neighbor search is available in open-source libraries (FAISS supports exact flat search, scikit-learn has BallTree and KDTree for exact k-NN). The commercial vs. open-source distinction has no bearing on whether exact or approximate algorithms are available. This option tests whether the learner has a real model of the technology landscape or is guessing.

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

**Why A is wrong:** An inverted index maps terms to document lists — it is the data structure behind BM25 sparse retrieval and full-text search engines like Elasticsearch. It has no relationship to dense ANN search over continuous vector spaces. A developer who confuses HNSW with an inverted index has conflated two entirely different retrieval paradigms (sparse keyword-based vs. dense embedding-based), which will cause systematic errors in system design choices.

**Why C is wrong:** Product quantization (PQ) is a vector compression technique — it subdivides high-dimensional vectors into sub-vectors and quantizes each sub-vector to a codebook entry, reducing memory footprint at the cost of some accuracy. It is a complementary technique that can be applied on top of IVF (creating IVF-PQ) but is not the definition of HNSW. Conflating compression techniques with index structure types is a common error among practitioners who have read about these methods without using them.

**Why D is wrong:** KD-trees and ball-trees are tree-based exact nearest neighbor structures that partition the vector space recursively. They work well in low dimensions (up to ~20) but suffer from the curse of dimensionality at the 768+ dimensions typical of text embeddings. HNSW is a graph-based structure specifically designed for high-dimensional spaces. Describing HNSW as tree-based indicates unfamiliarity with why graph-based ANN algorithms exist.

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

**Why A is wrong:** Post-filtering (retrieve then filter) is the naive implementation that developers often reach for first because it requires no vector-database-specific knowledge — just retrieve top-K and filter in application code. The problem surfaces at scale: if a strict filter passes only 5% of documents, you must retrieve top-200 to get 10 valid results after filtering. The upstream system cannot know in advance how many to retrieve, and the extra vectors waste compute and latency. Native pre-filter support exists specifically because this pattern breaks down in production.

**Why C is wrong:** Creating separate indexes per department-per-date-range would produce an exponential number of indexes as metadata combinations grow. This approach also makes cross-department queries impossible without merging results from multiple indexes, which reintroduces the ranking problem. It is an early-stage workaround that experienced teams abandon when they discover native metadata filtering.

**Why D is wrong:** Encoding structured fields (department ID, date) as extra embedding dimensions corrupts the semantic geometry of the embedding space. The embedding model was trained to encode semantic meaning in its dimensions — injecting structured integer or categorical values into those dimensions produces vectors that are neither semantically coherent nor reliably filterable. This approach reflects a misunderstanding of what embedding dimensions represent.

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

**Why B is wrong:** Embedding model vocabulary does not drift as documents are added — the vocabulary is fixed at model training time and does not change based on what documents are indexed. The embedding model converts text to vectors using the same learned function regardless of corpus growth. What changes with corpus growth is the index structure quality, not the embedding model's representational capability. Confusing index quality degradation with embedding model drift leads to the wrong remediation (model swap instead of index rebuild).

**Why C is wrong:** HNSW supports soft deletion using tombstone markers that flag deleted nodes without physically removing them from the graph. Hard deletions are possible via rebuild but are not required for routine document removal. The claim that "HNSW indexes do not support deletion" overstates the limitation and would lead a developer to unnecessarily schedule nightly rebuilds to handle deletions, when tombstones are sufficient for most use cases.

**Why D is wrong:** Vector dimensions are fixed by the embedding model at model initialization and do not change based on document content or token sequence length. A 768-dimensional model produces a 768-dimensional vector for every input, regardless of whether the input is 10 tokens or 512 tokens. Associating dimension count with token sequence length indicates a fundamental confusion between tokenization (variable-length sequences) and embedding (fixed-length output vectors).

---

## MCQ-6 — ef_search too low and silent recall degradation

**Difficulty:** intermediate
**Topic:** vector_databases

**Question:**
A production RAG system shows context recall dropping from 0.95 to 0.71 at p99 query latency over two weeks. No errors are logged. The HNSW index was not rebuilt. What is the most likely cause, and what is the correct parameter to adjust?

**Options:**
A. The recall drop indicates index corruption — the HNSW graph structure has become invalid. The fix is to delete and recreate the index from scratch
B. p99 latency increasing alongside recall drop indicates that the corpus has grown and the query-time `ef` (beam search width) is now too low relative to the larger index. The same `ef` value that produced good recall at smaller scale explores proportionally fewer candidates as the index grows. Increasing `ef_search` will restore recall at the cost of higher per-query latency
C. The recall drop is caused by the LLM generating longer answers, which increases the number of tokens it attends to and reduces per-chunk attention quality. The fix is to reduce chunk size at re-indexing time
D. A recall drop from 0.95 to 0.71 without errors means the embedding model has started returning zero vectors for some queries. The fix is to add a null-vector check at the retrieval layer

**Correct answer:** B

**Explanation:**
HNSW query-time recall is controlled by `ef` (also called `ef_search` or `hnsw_ef` depending on the implementation) — the width of the greedy beam search. A fixed `ef` value explores an absolute number of candidate nodes; as the index grows from, say, 500K vectors to 5M vectors, the same `ef` covers a proportionally smaller fraction of the neighborhood, reducing the chance of finding the true nearest neighbors. The symptom (recall drop, no errors, no index change) is the canonical signature of this failure mode. Option A describes structural corruption, which would manifest as errors or complete retrieval failure, not gradual recall degradation. Option C conflates LLM generation behavior with retrieval recall, which are independent pipeline stages. Option D (null vectors) would cause complete retrieval failure for affected queries, not a gradual recall drop across all p99 queries.

**Why A is wrong:** HNSW graph corruption is a rare event that would typically manifest as assertion errors, retrieval exceptions, or complete query failure — not a gradual, silent recall decrease. The symptom profile described (gradual degradation, no errors, p99 latency increase) is inconsistent with corruption. A developer who jumps to "recreate the index" without first checking `ef_search` will take an expensive corrective action when a one-parameter change would have resolved the issue.

**Why C is wrong:** LLM generation behavior and retrieval recall are completely decoupled in a RAG pipeline. The retrieval layer runs first and returns a fixed set of chunks; the LLM then generates from whatever was retrieved. The LLM's answer length or attention distribution has no feedback path into the retrieval stage. This option tests whether the learner understands the architectural separation between retrieval and generation.

**Why D is wrong:** An embedding model returning null (zero) vectors would produce retrieval results where all similarity scores are identical (zero dot product with everything), causing the returned chunks to be random rather than gradually less recalled. This would manifest as completely wrong results for specific queries, not a smooth p99 recall degradation across the fleet. Null-vector bugs are real but have a distinct signature from `ef`-related degradation.

---

## MCQ-7 — Pre-filter recall collapse with high selectivity

**Difficulty:** advanced
**Topic:** vector_databases

**Question:**
A multi-tenant RAG system uses pre-filtering: the ANN search is restricted to vectors matching `tenant_id = X` before traversal begins. Tenant X has 500 documents out of 500,000 total — a filter selectivity of 0.1%. Engineers observe that recall for Tenant X's queries drops from 0.93 to 0.51, despite the 500 documents all being present and correctly indexed. What causes this, and what is the correct architectural response?

**Options:**
A. Tenant X's documents have lower-quality embeddings because they were indexed in a different batch. Re-embedding Tenant X's documents using a higher-temperature embedding call will improve recall
B. Pre-filtering with high selectivity collapses recall because the HNSW graph was built across all 500,000 vectors. When the search is restricted to the 500-vector subset, the inter-node edges that would navigate through the relevant region of the graph mostly point to non-tenant vectors that are then excluded. The graph cannot navigate effectively within such a small filtered subgraph. The correct response is to use post-filtering (search the full graph, then filter results) or to use a dedicated per-tenant HNSW index
C. Recall drops because 500 documents is below the minimum corpus size for HNSW to function. The correct response is to pad Tenant X's index with synthetic vectors to reach the minimum threshold
D. The recall drop is caused by L2 normalization discrepancies between Tenant X's document batches and the rest of the corpus. Adding a normalization pass before indexing will restore recall

**Correct answer:** B

**Explanation:**
HNSW's graph edges are built during indexing based on proximity across the full corpus. The navigable small world property depends on having well-connected paths through the graph at every scale — from coarse long-range edges in the top layers to fine-grained local edges at the bottom. When a pre-filter restricts the search to 0.1% of vectors, the traversal algorithm must navigate through a subgraph where almost every edge leads to a node that will be filtered out, making the greedy search effectively blind. The phenomenon is well-documented: pre-filter recall degrades sharply as filter selectivity increases past roughly 10–20% of the index. The two correct architectural responses are (1) post-filter (search the full graph, apply the filter after collecting candidates) or (2) maintain separate per-tenant indexes sized appropriately. Option A invents a non-existent "embedding temperature" parameter. Option C invents a minimum corpus size for HNSW. Option D conflates normalization with graph navigation quality.

**Why A is wrong:** Embedding model calls do not have a "temperature" parameter — temperature is a sampling parameter for generative LLMs, not for embedding models. Embedding models are deterministic at inference time. This option introduces a fabricated concept. A developer misled by this answer would attempt a non-existent intervention and waste debugging time without addressing the actual structural graph navigation problem.

**Why C is wrong:** HNSW has no minimum corpus size threshold below which it stops functioning. It works on any number of vectors. The recall problem is not caused by corpus smallness per se — it is caused by the mismatch between the global graph structure and the highly selective filter. Padding with synthetic vectors would corrupt the embedding space with artificial data and still not solve the navigation problem, since the synthetic vectors would mostly also be excluded by the tenant filter.

**Why D is wrong:** L2 normalization affects similarity score scales and magnitude bias, not graph navigation quality within a pre-filtered subset. Normalization problems manifest as ranking anomalies where magnitude-heavy vectors score artificially high — a different symptom than the recall collapse observed here. Attributing a pre-filter recall collapse to normalization issues reflects a pattern-matching error (both are "vector quality" problems) rather than understanding the specific mechanism causing the failure.

---

## MCQ-8 — Replication lag and retrieval consistency window

**Difficulty:** advanced
**Topic:** vector_databases

**Question:**
A RAG system ingests documents via an async pipeline. A document is indexed at T=0ms. A query arrives at T=180ms. The query is routed to a read replica that has not yet received the replication event. The document is not retrieved. No errors are raised. What consistency model does this represent, and under what RAG use case does this failure mode become critical?

**Options:**
A. This represents strong consistency failure — the system is misconfigured and should be using synchronous replication. Any properly deployed vector database uses strong consistency by default
B. This represents eventual consistency — writes are propagated to replicas asynchronously after being applied to the primary. A replication lag window (here, >180ms) exists during which the primary and replicas diverge. This failure mode becomes critical when the RAG system is used for time-sensitive content where users expect to retrieve a document they just uploaded (e.g., a customer uploading a support case and immediately querying for it)
C. This represents a network partition — the replica has lost connectivity with the primary. The fix is to configure automatic failover to the primary for all reads during partition events
D. This is not a consistency problem — the 180ms window is within the normal HNSW build time for a new vector. The document is present in the index but takes 200–500ms to become searchable after insertion due to graph connection computation

**Correct answer:** B

**Explanation:**
Most production vector databases optimized for write throughput use asynchronous replication: writes commit to the primary immediately and propagate to read replicas with a lag. This is eventual consistency — given enough time, all replicas converge to the same state. A 180ms replication window is a normal operational characteristic, not a bug. The failure mode becomes critical in same-session retrieval scenarios: a user uploads a document, the UI returns a success message (the primary received the write), but the user's next query (routed to a replica still lagging) cannot find the document. For asynchronous workflows (batch ingestion, background knowledge base updates) the lag is typically irrelevant. For synchronous workflows (user-facing upload-then-query flows), the system must either route the user's session to the primary for a bounded window, implement read-your-writes consistency, or set user expectations about indexing latency.

**Why A is wrong:** Strong consistency by default is not a characteristic of most production-grade vector databases designed for high-throughput RAG. Enforcing strong consistency requires synchronous replication acknowledgment before returning a successful write — this increases write latency significantly and reduces write availability during network delays. Most vector databases chose eventual consistency deliberately as a tradeoff. Claiming strong consistency is the default reflects an expectation borrowed from ACID relational databases, which operates under a fundamentally different consistency model.

**Why C is wrong:** A network partition is a complete loss of connectivity between primary and replica, causing replicas to stop receiving any updates at all. The scenario described is not a partition — it is normal asynchronous lag where the replica is receiving updates but behind by less than 180ms. Treating routine replication lag as a partition would lead to unnecessary failover operations and primary overload for every query. These are distinct operational conditions that require different responses.

**Why D is wrong:** HNSW graph connection computation happens synchronously at insert time on the node receiving the write — the vector is fully searchable on the primary immediately after insertion (within single-digit milliseconds for most implementations). There is no post-insert "warm-up" period during which a vector is present but unsearchable on the same node. The 180ms gap is replication lag to a different node, not local index build time.

---

## MCQ-9 — Payload indexing strategy for filtered throughput

**Difficulty:** expert
**Topic:** vector_databases

**Question:**
A vector database stores 10 million vectors. Each vector has a string metadata field `category` with 200 distinct values. A filtered query uses `WHERE category = 'X'` pre-filter before ANN search. Without payload indexing, the system scans all 10M metadata records to evaluate the filter on every query. With payload indexing enabled on `category`, filter evaluation takes microseconds instead of seconds — but index time increases by 40% and the payload index consumes 2GB of additional RAM. A product manager proposes enabling payload indexing only for the top-10 most queried categories, leaving the other 190 categories to use full-scan filtering. What is the flaw in this proposal?

**Options:**
A. There is no flaw — partial payload indexing is the optimal strategy and is explicitly supported by all major vector databases as a tiered indexing feature
B. The flaw is that query patterns are non-stationary: the top-10 categories today may not be the top-10 next quarter as user behavior shifts or new content is added. A query that falls outside the indexed set hits the full scan path silently — no error is raised, just a 100–1000x latency increase. This is an operational surprise that is difficult to detect without latency percentile monitoring per category value. The operationally safer approach is to index all 200 values (the 2GB cost is fixed) or to accept full-scan filtering with a query timeout guardrail
C. The flaw is that payload indexing only functions if all values in a field are indexed simultaneously — partial indexing of a string field causes the database to return incorrect results for both indexed and unindexed values
D. The flaw is that the 2GB RAM cost applies per replica, and with partial indexing covering only 10 categories, the RAM savings are minimal while the management complexity triples

**Correct answer:** B

**Explanation:**
Partial payload indexing creates a two-tier query performance profile that is difficult to observe and maintain. The indexed categories get microsecond filtering; the unindexed categories trigger full-scan filtering with 40–100x higher latency per query. If user behavior or content distribution shifts — a common occurrence in live systems — a previously low-traffic category becomes high-traffic and silently hits the slow path. The failure mode is insidious: the system returns correct results but with degraded latency, and without explicit per-category latency tracking, the degradation is invisible until users complain or SLOs are breached. The correct approach is either to index all values (accepting the fixed 2GB cost) or to use a different architectural pattern (post-filtering, or a dedicated index for high-selectivity use cases). Option A overstates the universality of "tiered indexing" as an explicitly supported feature and does not identify the operational risk. Option C is factually incorrect — partial payload indexing does not corrupt result correctness, only query performance for unindexed values. Option D correctly identifies RAM-per-replica amplification but misses the core operational risk, which is non-stationary query patterns.

**Why A is wrong:** "Tiered payload indexing" as an explicitly designed feature is not a standard offering in most vector databases. What exists is the ability to choose which fields to index — but the decision is treated as a system-configuration choice, not a dynamic query-time optimization. More critically, Option A presents partial indexing as problem-free, which misses the core operational hazard: non-stationary query distributions silently degrading performance. A practitioner who accepts this framing will implement partial indexing without the latency monitoring guardrails that make it survivable.

**Why C is wrong:** Payload indexing in vector databases is an acceleration structure — it speeds up filter evaluation but does not affect result correctness. Unindexed fields fall back to sequential scan, which is slower but correct. This option invents a data correctness problem that does not exist, which would lead developers to avoid partial indexing for incorrect safety reasons and miss the actual risk (latency surprises) in their operational planning.

**Why D is wrong:** RAM-per-replica cost amplification is a real consideration, but it is not the primary flaw in the PM's proposal. The RAM cost for 10 vs. 200 indexed categories is proportional (roughly 10/200 × 2GB = 100MB savings per replica) — not a trivial savings, but also not "minimal" as stated. More importantly, the RAM framing focuses on a cost concern rather than the operational correctness concern: an unindexed high-traffic category silently degrading to full-scan latency is a reliability failure that RAM calculations do not prevent.

---

## MCQ-10 — Write-visible-but-unqueryable: concurrent write consistency failure

**Difficulty:** expert
**Topic:** vector_databases

**Question:**
A developer writes an automated test that: (1) indexes a single document, (2) waits for the index call to return a success response, (3) immediately queries the index for that document. The query returns zero results. The test is run on a single-node vector database instance with no replication configured. No errors are raised. The test fails consistently, not intermittently. What is the most likely cause, and how do you verify it?

**Options:**
A. The document was written to a write-ahead log but not yet flushed to the HNSW graph — the index call returned success when the WAL acknowledged the write, but the vector is not yet connected into the graph structure and is therefore not traversable by ANN search. Verify by checking whether the document appears in a full sequential scan (exact search or metadata-only query) but not in ANN search
B. The ANN index requires a minimum of 100 vectors before it can return results — the test corpus with a single vector falls below the operational threshold. Verify by adding 99 padding vectors before the target document and re-running the test
C. The embedding vector for the document is outside the valid range for the configured distance metric — cosine similarity is undefined for zero-norm vectors. Verify by checking whether the embedding returned by the embedding model has magnitude zero
D. The index is using eventual consistency internally even on a single node — the write was acknowledged by the frontend but has not yet propagated to the search backend. Verify by adding a 500ms sleep between indexing and querying

**Correct answer:** A

**Explanation:**
Many vector databases, particularly those optimized for write throughput, decouple the write acknowledgment from the point at which the vector becomes traversable via ANN search. The write path may involve: (1) accepting the vector and metadata into an in-memory buffer or write-ahead log, (2) returning a success response to the caller, and (3) asynchronously integrating the vector into the HNSW graph structure. Steps 1 and 2 happen synchronously; step 3 happens asynchronously. A document that is acknowledged but not yet graph-integrated will appear in sequential scan (full table scan of the payload store) but not in ANN search, because HNSW traversal only visits nodes that have been connected into the graph. This is the distinguishing diagnostic: exact/sequential search finds the document, ANN search does not. Once the graph integration completes (typically within milliseconds for a single document, but blocking under high write concurrency), the document becomes queryable via ANN. The fix in a test context is to use the vector database's synchronous flush or segment commit API call, if available, or to use exact search for validation in write-latency-sensitive contexts. This failure mode is consistent (not intermittent) because the document is always added to the WAL first and graph-integrated second — the test always runs faster than the graph integration step.

**Why B is wrong:** HNSW and most production vector database index implementations have no minimum vector count threshold below which search is disabled. A single-vector index is fully searchable — the nearest neighbor of any query in a 1-vector index is that one vector, with whatever its true similarity score is. A developer who reaches for "minimum threshold" is confusing vector database behavior with statistical minimum sample size concepts from machine learning, which do not apply here.

**Why C is wrong:** A zero-norm vector would cause a division-by-zero in cosine similarity computation, typically producing either an error at embedding time, a NaN similarity score at query time, or a silent zero-score result that falls below any threshold. But the scenario specifies that no errors are raised and the result is zero results — not a score of 0 for the correct document. Additionally, embedding APIs do not return zero-norm vectors for valid text inputs; this would require a degenerate input or a severe model bug. The diagnostic for a zero-norm vector (check embedding magnitude) would be the wrong first step for a write-ordering problem.

**Why D is wrong:** Single-node vector databases do not use eventual consistency internally in the same way distributed systems do — there is no network hop between a "write frontend" and a "search backend" that introduces propagation delay on a single node. The failure mode described is a write buffer / graph integration ordering issue, not a distributed consistency window. Adding a 500ms sleep would likely mask the symptom in a test environment but would not identify or fix the root cause, and would leave the production system exposed to the same condition under any write workload that outpaces graph integration.

