# Question Bank: `vector_databases`
# Phase: 2 — Core Components
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-11 (Commit 22)

---

## Q1 — Why ANN instead of exact nearest neighbor?

**Difficulty:** novice

**Question:**
Vector databases use approximate nearest neighbor (ANN) search rather than exact nearest
neighbor search. Explain the tradeoff this represents: what is gained and what is
potentially lost?

**Correct answer criteria:**
- Exact nearest neighbor search guarantees the true closest vectors are returned but
  requires comparing the query vector against every vector in the index — O(N) per query
- At scale (millions of vectors), exact search is too slow for real-time retrieval
- ANN search uses index structures that allow the search to skip most of the vector space,
  dramatically reducing query time
- What is potentially lost: the true nearest neighbor may occasionally not be in the result
  set — ANN may return the 2nd or 3rd nearest neighbor as the top result (recall loss)
- The recall-latency tradeoff is tunable via index parameters

**Partial credit criteria:**
- Correctly states that ANN trades accuracy for speed but cannot explain how or why
  exact search is too slow
- Describes the tradeoff qualitatively but cannot identify what O(N) complexity means
  at scale

**Incorrect / no-credit criteria:**
- Claims ANN always returns the same results as exact search
- Cannot identify that ANN may miss the true nearest neighbor
- Describes ANN as simply "using less memory"

---

## Q2 — HNSW: conceptual mechanics

**Difficulty:** intermediate

**Question:**
Explain how HNSW (Hierarchical Navigable Small World) search works at a conceptual level.
What data structure does it build during indexing, and how does it traverse that structure
during query time?

**Correct answer criteria:**
- HNSW builds a multi-layer graph during indexing. Each vector is a node. Edges connect
  nearby vectors (neighbors in the embedding space). Higher layers are sparse (long-range
  connections); lower layers are dense (short-range, high precision)
- During query time: the search starts at the top layer (sparse), navigates greedily
  toward the query vector (following the edge that minimizes distance to the query at
  each step), then descends to the next layer for finer navigation, continuing until
  reaching the bottom layer where candidate results are collected
- This hierarchical navigation allows the search to skip large portions of the vector
  space by first approximating the target region at high levels before precision-searching
  locally at the bottom layer

**Partial credit criteria:**
- Describes HNSW as a graph-based approach without explaining the hierarchical layer
  structure or traversal strategy
- Correctly describes the layered structure but cannot explain how query traversal
  descends through layers

**Incorrect / no-credit criteria:**
- Describes HNSW as a tree structure (it is a graph)
- Claims HNSW is a clustering approach (that describes IVF)
- Cannot explain what "navigable small world" refers to

---

## Q3 — IVF: index by clustering

**Difficulty:** intermediate

**Question:**
Explain how IVF (Inverted File Index) organizes vectors for search. Contrast it with HNSW
on: build time, memory usage, and recall at equal query time.

**Correct answer criteria:**
- IVF: during indexing, vectors are clustered into N clusters (using k-means). Each
  cluster has a centroid. At query time, the query vector is compared to all centroids,
  the nearest M cluster(s) are selected (nprobe parameter), and only the vectors within
  those clusters are compared against the query
- Build time: IVF requires a training step (k-means clustering) which can be slow for
  large datasets; HNSW builds incrementally and does not require a separate training step
- Memory: IVF stores flat vectors grouped by cluster — generally lower memory usage than
  HNSW, which stores vectors plus a graph structure with many pointers per node
- Recall: for equal query time, HNSW typically achieves higher recall because its
  navigable small world structure provides a more efficient search path; IVF recall
  depends heavily on nprobe — if relevant vectors fall in a non-selected cluster, they
  are missed entirely

**Partial credit criteria:**
- Correctly describes IVF clustering but cannot compare it to HNSW on any dimension
- Compares on one or two dimensions but not all three

**Incorrect / no-credit criteria:**
- Describes IVF as a graph structure (it is cluster-based)
- Claims IVF and HNSW have identical recall characteristics
- Cannot explain the nprobe parameter's role

---

## Q4 — Metadata filtering semantics

**Difficulty:** intermediate

**Question:**
Your vector database stores document chunks with a metadata field `department` (values:
"legal", "engineering", "finance"). A user query arrives and you want to restrict results
to the "legal" department. Explain the difference between pre-filtering and post-filtering,
and describe the recall tradeoff each approach makes.

**Correct answer criteria:**
- Pre-filtering: the department filter is applied before ANN search — only vectors from
  "legal" documents are candidates for the ANN search. This ensures the returned results
  are all from the legal department, but the ANN search now operates on a smaller subset,
  which can degrade recall because the index was built for the full dataset
- Post-filtering: ANN search runs over the full index and returns top-K results; the
  department filter is then applied to the results. This gives the ANN search full-index
  coverage (better recall), but the filtered result set may contain fewer than K items
  if many top results are from other departments
- Recall tradeoff:
  - Pre-filter: better department precision, potentially fewer true relevant results
    (the relevant legal vectors may not be the ANN's top picks within the legal subset)
  - Post-filter: better retrieval recall but non-deterministic result count after filtering

**Partial credit criteria:**
- Describes one approach correctly but not both
- Correctly distinguishes the two but cannot identify the recall implication of each

**Incorrect / no-credit criteria:**
- Claims pre- and post-filtering produce identical results
- Describes metadata filtering as a full-text search (keyword matching), not vector search
- Cannot identify any tradeoff between the two approaches

---

## Q5 — Designing a collection schema

**Difficulty:** intermediate

**Question:**
You are building a RAG system for a multi-tenant SaaS application where each tenant has
its own document corpus and must never see another tenant's data. Design a collection
schema for the vector database. What fields do you include, how do you handle tenant
isolation, and what index type would you choose?

**Correct answer criteria:**
- Schema fields:
  - `id` — unique chunk identifier
  - `vector` — the embedding vector
  - `text` — the raw chunk text (for return to the LLM)
  - `tenant_id` — the tenant identifier (used for isolation)
  - `document_id` — source document identifier
  - `metadata` — additional document metadata (title, URL, timestamp, etc.)
- Tenant isolation approach: either (a) a separate collection per tenant (hard isolation,
  simpler filtering, higher overhead for many tenants) or (b) a shared collection with
  mandatory pre-filtering on `tenant_id` (lower overhead, but a misconfigured filter
  would expose cross-tenant data — audit risk)
- Index type: HNSW is generally preferred for low-latency retrieval in a serving system;
  IVF may be appropriate if memory is a binding constraint and nprobe can be tuned for
  acceptable recall
- Should mention the need for `tenant_id` to be a non-nullable, indexed metadata field
  so filtering is efficient

**Partial credit criteria:**
- Includes most schema fields but misses tenant isolation as a first-class design concern
- Addresses tenant isolation correctly but cannot justify the index type choice

**Incorrect / no-credit criteria:**
- Does not address tenant isolation at all
- Recommends a single un-partitioned index with no filtering strategy
- Cannot describe what fields belong in the collection

---

## Q6 — Distance metrics and their effects

**Difficulty:** intermediate

**Question:**
Your vector database offers three distance metrics: cosine similarity, dot product, and
Euclidean (L2) distance. Your embedding model produces unit-normalized vectors. Which
metric would you choose, and what changes if the vectors were not normalized?

**Correct answer criteria:**
- For unit-normalized vectors, cosine similarity and dot product produce identical rankings
  (dot product of unit vectors equals the cosine of the angle). Euclidean distance also
  produces a monotone ranking equivalent to cosine for unit vectors, because
  |a-b|^2 = 2 - 2*cos(theta) for unit vectors
- In practice, for unit-normalized vectors, all three metrics produce the same ranking —
  the choice affects only the numerical scale, not which vectors are returned
- If vectors are not normalized: dot product favors vectors with larger magnitude
  (length bias); Euclidean distance measures absolute spatial distance which can be
  dominated by magnitude differences; cosine similarity remains invariant to magnitude
  because it normalizes internally
- Recommendation: use cosine similarity as the default to ensure magnitude-invariance;
  if performance is critical and vectors are guaranteed normalized by the embedding model,
  dot product (inner product) is faster to compute

**Partial credit criteria:**
- Recommends cosine similarity without explaining why, or without addressing the
  normalized vs. non-normalized difference
- Correctly explains the normalized equivalence but cannot describe the failure mode
  when vectors are not normalized

**Incorrect / no-credit criteria:**
- Claims the three metrics always produce different rankings regardless of normalization
- Recommends Euclidean as the default for semantic search without qualification
- Cannot identify magnitude bias as the failure mode of dot product on unnormalized vectors

---

## Q7 — Index scalability and recall degradation

**Difficulty:** advanced

**Question:**
An HNSW index that worked well at 100K vectors begins showing decreased recall as the
corpus grows to 10 million vectors. The index parameters (`ef_construction` and `M`)
were not changed. Explain what causes this degradation and describe two approaches
to address it.

**Correct answer criteria:**
- HNSW recall is controlled by `ef_construction` (graph connectivity quality during build)
  and `M` (number of bidirectional edges per node). At 100K vectors, the default
  parameters may have produced a well-connected graph relative to corpus size; at 10M,
  the same parameters produce a sparser graph relative to the larger neighborhood space
- Additionally, query-time `ef` (search beam width) controls how many candidates are
  explored during traversal — a fixed `ef` covers proportionally less of the graph at
  larger scale
- Approach 1: increase query-time `ef` parameter — this expands the search beam,
  exploring more candidates per query at the cost of higher query latency
- Approach 2: rebuild the index with higher `M` and `ef_construction` — more edges per
  node improves graph connectivity and recall, at the cost of higher memory usage and
  longer build time
- (Acceptable alternative approach): use HNSW with product quantization (PQ compression)
  to reduce per-vector memory, which allows `M` to be increased within the same
  memory budget

**Partial credit criteria:**
- Identifies that index parameters need adjustment but cannot explain why the same
  parameters produce lower recall at larger scale
- Correctly identifies `ef` or `M` as the relevant parameters but explains only one
  approach, not two

**Incorrect / no-credit criteria:**
- Attributes the recall degradation to the embedding model rather than the index
- Recommends switching to IVF without explaining why IVF would be better at this scale
- Cannot identify `ef` or `M` as relevant parameters

---

## Q8 — Replication and consistency in production

**Difficulty:** advanced

**Question:**
Your RAG system indexes new documents in near-real-time. Multiple query replicas serve
traffic simultaneously. Describe the consistency problem that arises and explain how
vector databases typically handle the tradeoff between write availability and read
consistency.

**Correct answer criteria:**
- The problem: if a new document is indexed and only written to one replica before a
  query arrives, some replicas will return results that include the new document and
  others will not — users see inconsistent results for the same query depending on which
  replica handles their request
- This is the classic eventual consistency vs. strong consistency tradeoff
- Most vector databases designed for RAG choose eventual consistency: writes are applied
  to a primary first and propagated to replicas asynchronously. This maximizes write
  throughput and query availability but introduces a window during which replicas lag
- Strong consistency (synchronous replication) would ensure all replicas see the new
  document before queries return, but adds write latency and reduces availability during
  network partitions
- For RAG use cases, eventual consistency is typically acceptable: a document not
  appearing for a few seconds after indexing is tolerable; strict transactional consistency
  (as in financial systems) is not required
- The staleness window should be monitored and bounded (e.g., max replica lag alert)

**Partial credit criteria:**
- Identifies the consistency problem but cannot describe how vector databases typically
  handle the tradeoff
- Correctly describes eventual vs. strong consistency but cannot apply it to the RAG
  use case

**Incorrect / no-credit criteria:**
- Claims vector databases provide strong consistency by default
- Cannot identify that multiple replicas create a consistency problem
- Recommends serializing all writes to prevent any inconsistency (does not recognize
  the availability cost)

---

## Q9 — Pre-filter vs. post-filter in a multi-tenant system at scale

**Difficulty:** advanced

**Question:**
You are operating a multi-tenant RAG system where each query must be isolated to the
requesting tenant's documents using a `tenant_id` metadata filter. Your system has 5,000
tenants, each with an average of 10,000 document chunks. You are evaluating whether to
use pre-filtering or post-filtering for tenant isolation. Describe the tradeoffs of each
approach at this tenant count, and identify the specific condition under which each
approach breaks down.

**Correct answer criteria:**
- Pre-filtering: the ANN search operates only on the subset of vectors belonging to the
  tenant (10,000 chunks out of 50 million total). This guarantees isolation without
  post-hoc filtering. However, HNSW graphs are built on the full index — the graph
  structure is optimized for navigating the full 50M-vector space, not individual
  10K-chunk subsets. When pre-filtering restricts the search to a small subset, the graph
  traversal becomes inefficient: the greedy navigation was designed for a dense space and
  becomes sparse within the tenant's subset, degrading recall. Many vector databases
  fall back to brute-force search when the pre-filtered subset is small, losing the
  ANN index advantage entirely
- Pre-filter breaks down when: the per-tenant chunk count is small relative to the total
  index size (high ratio of total-to-tenant vectors). At 10K/50M, pre-filtering is likely
  to trigger brute-force fallback. The threshold varies by database but is typically when
  the filtered subset is below 5–10% of the total index
- Post-filtering: ANN search runs over the full 50M-vector space with full index coverage,
  then filters to the tenant's documents. This preserves ANN recall quality but may return
  fewer than top-K results after filtering if many top candidates belong to other tenants.
  At 5,000 tenants (average 10K chunks each), roughly 1 in 5,000 random vectors belongs
  to the querying tenant — post-filtering after retrieving top-20 ANN results would often
  return zero matches, requiring an impractically large initial retrieval count
- Post-filter breaks down when: tenant data is a small fraction of the total index and
  most top-K ANN results belong to other tenants, requiring retrieving hundreds of
  candidates to guarantee even a handful survive the filter
- Recommended approach for this scenario: separate collection per tenant (hard isolation),
  which sidesteps the pre/post-filter dilemma entirely by ensuring the ANN index only
  contains one tenant's vectors. The overhead of 5,000 collections must be evaluated
  against the database's collection limit and management complexity

**Partial credit criteria:**
- Correctly describes the pre-filter recall degradation problem but does not identify the
  specific condition (small subset / total ratio) that causes brute-force fallback
- Correctly describes both tradeoffs but does not identify the recommended alternative
  (separate collections) for the specific scenario parameters given

**Incorrect / no-credit criteria:**
- Claims pre-filtering and post-filtering produce the same recall quality at all scales
- Cannot identify any condition under which either approach breaks down
- Recommends post-filtering without acknowledging that at 1/5000 density it would require
  retrieving hundreds of candidates

---

## Q10 — Diagnosing HNSW recall degradation without ground truth

**Difficulty:** advanced

**Question:**
Your production HNSW index is showing signs of recall degradation — users are reporting
that relevant documents are not appearing in results, but you have no labeled ground truth
for the affected queries. Describe what operational proxy metrics would reveal the recall
problem, and what the corrective actions are.

**Correct answer criteria:**
- Proxy metric 1: top-1 similarity score distribution. Track the distribution of the
  maximum cosine similarity score returned per query over time. If the median top-1
  similarity is drifting downward (i.e., even the best-matching document is scoring
  lower), one of three things is happening: the queries are drifting from the indexed
  content (corpus staleness), the embedding model is misaligned with the corpus (drift),
  or the HNSW graph is returning increasingly suboptimal nearest neighbors (recall
  degradation). To distinguish HNSW recall from the other two: run exact brute-force
  search on a small random sample of queries and compare the top-1 score to what HNSW
  returns. A persistent gap between exact and HNSW results confirms recall degradation
  in the index itself
- Proxy metric 2: query result diversity drop. If all queries are returning overlapping
  documents (the same chunks appearing in results for many different queries), the HNSW
  graph traversal is converging on a small, well-connected subgraph rather than exploring
  diverse neighborhoods. This is a symptom of low ef (search beam width) relative to
  corpus size
- Proxy metric 3: fallback rate trend. If your system generates "I don't know" responses
  (or low-confidence answers) more frequently without a corresponding increase in query
  volume or corpus change, retrieval quality is degrading
- Corrective actions:
  1. Increase query-time ef parameter: expands the search beam, exploring more candidate
     nodes before returning results. This is a live configuration change requiring no
     re-indexing but increases query latency
  2. Rebuild the index with higher ef_construction and M: improves graph connectivity
     at build time. Requires a full re-index — use the shadow index pattern to avoid
     downtime
  3. If the corpus has grown significantly since the last build: the original ef_construction
     was calibrated for a smaller dataset. Rebuild with parameters appropriate to current scale

**Partial credit criteria:**
- Identifies the exact vs. ANN comparison as a diagnostic method but cannot describe the
  operational proxy metrics that would flag the problem without running exact search on
  every query
- Correctly describes the corrective actions but cannot describe any proxy metric that
  would alert you to the problem in the first place

**Incorrect / no-credit criteria:**
- Recommends switching from HNSW to IVF as the primary corrective action without
  explaining why HNSW recall degraded or how IVF addresses it
- Cannot identify any operational signal that indicates HNSW recall degradation
  without labeled ground truth
- Confuses HNSW recall degradation with embedding model drift (different root causes
  and different corrective actions)

---

## Q11 — Zero-downtime migration between vector databases

**Difficulty:** advanced

**Question:**
You need to migrate your production RAG system from vector database A to vector database
B. The system serves 200 queries per minute continuously — you cannot take retrieval
offline. Your corpus has 8 million document chunks. Describe the dual-write migration
strategy: what the dual-write period looks like, how you maintain consistency during it,
and what the cutover condition is.

**Correct answer criteria:**
- Dual-write period:
  1. Before migrating any traffic, build the full index in database B from the existing
     corpus (offline bulk load). This is the initial sync — database B now contains all
     8M vectors as of the start of the migration
  2. Begin dual-write: every new document ingestion event writes to both database A
     (production) and database B (shadow). Deletes and updates are also applied to both.
     This ensures database B stays current with new content while traffic continues to
     be served from database A
  3. Do not route any query traffic to database B yet. Database B is receiving writes
     but not reads
- Consistency check approach:
  1. After the initial bulk load completes and dual-write is active, verify that vector
     counts in both databases match within a small delta (expected difference: documents
     ingested during the bulk load window that dual-write may have missed). Replay any
     missed events from the ingestion queue
  2. Run shadow query evaluation: sample 500 queries from production traffic and run them
     against both databases. Compare the top-5 retrieved chunks from each. A high
     agreement rate (>90% overlap in top-3) confirms database B's index is functionally
     equivalent. A low agreement rate indicates an index configuration issue in database B
     that must be resolved before cutover
- Cutover condition: shadow query evaluation shows >90% result agreement, vector counts
  are within acceptable delta, and database B query latency is within acceptable bounds
  (p99 < production SLA). When all three conditions are met, perform atomic traffic
  cutover: update the retriever configuration to point to database B. Database A remains
  in read-only mode for 48–72 hours as a rollback target, then is decommissioned
- Throughout the dual-write period, monitor both databases for write lag — if database B's
  write queue backs up, the consistency guarantee degrades

**Partial credit criteria:**
- Correctly describes the dual-write mechanism but does not include the shadow query
  evaluation step (cutting over without validating result equivalence is a blind migration)
- Correctly describes the shadow query evaluation and cutover condition but does not
  specify keeping database A in read-only mode as a rollback target post-cutover

**Incorrect / no-credit criteria:**
- Proposes a scheduled maintenance window to take retrieval offline during migration
  (the question specifies zero downtime)
- Describes building the new index and switching traffic immediately without a dual-write
  period (results in serving stale data from database B for all documents ingested
  during the build window)
- Cannot identify what the cutover condition should be — proposes switching based on
  time elapsed rather than validated query equivalence
