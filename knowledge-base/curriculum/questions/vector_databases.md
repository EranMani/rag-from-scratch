# Question Bank: `vector_databases`
# Phase: 2 — Core Components
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-11 (Commit 22)

---

## Q1 — Why ANN instead of exact nearest neighbor?

**Difficulty:** beginner

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
