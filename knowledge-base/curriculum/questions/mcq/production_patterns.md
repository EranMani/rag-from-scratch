# MCQ Bank — production_patterns
# Topic: production_patterns
# Phase: 3 (Production)
# Questions: 5 (2 beginner, 2 intermediate, 1 advanced)
# Last updated: 2026-05-19 (Commit 33)

---

## MCQ-1 — Caching in RAG pipelines

**Difficulty:** beginner
**Topic:** production_patterns

**Question:**
What type of caching most directly reduces LLM inference cost in a high-traffic RAG system?

**Options:**
A. Caching the raw document files so they do not need to be re-read from disk during indexing
B. Caching complete query/answer pairs so identical user queries bypass both retrieval and LLM generation
C. Caching embedding vectors for frequently queried text so the embedding model is not called repeatedly
D. Caching the vector database index in RAM so disk reads are eliminated during ANN search

**Correct answer:** B

**Explanation:**
LLM inference is the most expensive step in a RAG pipeline. Caching complete query/answer pairs means a repeated identical query can be served from cache without invoking the LLM at all. Option C (embedding caching) reduces embedding model cost, which is smaller than LLM cost. Option D (index in RAM) is an ANN performance optimization, not a cost reduction measure. Option A (document caching) applies to indexing, not query serving. Most production systems implement several of these, but B has the largest per-query cost impact.

---

## MCQ-2 — Index staleness

**Difficulty:** beginner
**Topic:** production_patterns

**Question:**
A production RAG system's document corpus is updated daily with new reports. The vector index is rebuilt weekly. What is the risk?

**Options:**
A. The embedding model may become outdated if it was not trained on the newest documents
B. Users querying between index rebuilds may receive answers based on retrieved context that does not include documents added since the last rebuild
C. Daily document additions will corrupt the existing vector index entries for older documents
D. The weekly rebuild will erase all cached query/answer pairs, causing a cold cache after each rebuild

**Correct answer:** B

**Explanation:**
When the vector index is rebuilt weekly but new documents are added daily, documents added after the last rebuild are invisible to the retrieval system until the next rebuild. Users querying about recent events or newly published reports will not have those documents in their retrieved context. This is the classic index staleness problem. Option A is incorrect — the embedding model is fixed; it is not "trained" on new documents. Option C is incorrect — new documents are appended; they do not affect existing index entries. Option D may be true as an operational concern but is a separate issue from the staleness risk.

---

## MCQ-3 — Async vs. synchronous retrieval

**Difficulty:** intermediate
**Topic:** production_patterns

**Question:**
A RAG API endpoint currently performs retrieval and LLM generation synchronously in a single request/response cycle, resulting in high tail latency. A developer proposes switching to async processing: the endpoint immediately returns a job ID, and the client polls for the result. What is the primary benefit and the primary cost of this change?

**Options:**
A. Benefit: eliminates retrieval latency entirely by pre-fetching documents at indexing time. Cost: increased storage for pre-fetched context
B. Benefit: the server can handle more concurrent requests because threads are not blocked waiting for LLM responses. Cost: increased system complexity (job queue, polling, result storage) and degraded user experience for real-time use cases
C. Benefit: LLM generation quality improves because the model has more time to process the query. Cost: the client must implement retry logic
D. Benefit: retrieval and generation can be parallelized within a single request, reducing total latency. Cost: requires a more powerful server

**Correct answer:** B

**Explanation:**
Async processing decouples request acceptance from result generation. The server accepts the request immediately (low latency for the initial response), queues the work, and processes it without holding a thread open. This dramatically increases throughput for concurrent workloads — 100 simultaneous synchronous requests each blocking for 5 seconds would exhaust a thread pool, while async processing queues them. The cost is real: a job queue (e.g., Redis, Celery), result storage, and polling logic add significant infrastructure and UX complexity. Option A describes a prefetching strategy, not async processing. Option C incorrectly claims generation quality improves with time. Option D describes parallelizing within a request — a different optimization from async.

---

## MCQ-4 — Observability in production RAG

**Difficulty:** intermediate
**Topic:** production_patterns

**Question:**
Which set of metrics provides the most complete observability picture for a production RAG pipeline?

**Options:**
A. LLM token usage and API cost per query only — these are the only billable variables that matter in production
B. Retrieval latency, LLM generation latency, context precision (sampled), faithfulness (sampled), and user satisfaction signals
C. Vector database query time and embedding model inference time only — the LLM is a black box and cannot be instrumented
D. Error rates and uptime only — RAG quality metrics are too expensive to compute in production

**Correct answer:** B

**Explanation:**
Complete RAG observability requires visibility into all three stages: retrieval (latency + quality), generation (latency + faithfulness), and user impact (satisfaction). Retrieval and LLM latency metrics identify performance bottlenecks. Sampled context precision and faithfulness catch quality degradation before users notice. User satisfaction signals (thumbs up/down, follow-up questions) surface issues that automated metrics miss. Option A captures cost but ignores quality. Option C incorrectly claims LLMs cannot be instrumented — generation time, token counts, and sampled outputs are all measurable. Option D abandons quality monitoring entirely.

---

## MCQ-5 — Handling retrieval failures gracefully

**Difficulty:** advanced
**Topic:** production_patterns

**Question:**
A production RAG system detects that for a given query, all retrieved chunks have cosine similarity below 0.40 — well below the system's typical similarity range for answerable queries. The system currently passes these low-quality chunks to the LLM regardless. What is the correct production handling strategy and why?

**Options:**
A. Pass the low-similarity chunks to the LLM anyway — the LLM will recognize they are irrelevant and indicate it cannot answer
B. Implement a similarity threshold: if no retrieved chunk exceeds the threshold, return a "I cannot find relevant information" response without invoking the LLM, and log the query for corpus gap analysis
C. Increase the number of retrieved chunks from top-5 to top-20 when similarity is low — more chunks increases the chance of finding a relevant one
D. Fall back to the LLM's parametric knowledge without any retrieved context when similarity is low, since retrieval has failed

**Correct answer:** B

**Explanation:**
When retrieved chunks are low-quality, passing them to the LLM creates two problems: (1) the LLM may confabulate an answer using irrelevant context as scaffolding, producing a confident but wrong response; (2) LLM inference is invoked at full cost with no quality benefit. The correct strategy is a similarity threshold gate: detect the low-quality retrieval, return a transparent "cannot find information" response (honest to the user), and log the query for corpus gap analysis (the query reveals a knowledge gap in the corpus that should be addressed). Option A relies on the LLM's judgment — unreliable, and costly. Option C increases noise without improving signal. Option D removes grounding entirely, which is exactly the hallucination-prone behavior RAG is designed to prevent.

