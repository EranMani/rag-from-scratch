# MCQ Bank — production_patterns
# Topic: production_patterns
# Phase: 3 (Production)
# Questions: 11 (2 novice, 4 intermediate, 3 advanced, 2 expert)
# Last updated: 2026-05-21 (Commit 45)

---

## MCQ-1 — Caching in RAG pipelines

**Difficulty:** novice
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

**Why A is wrong:** Document file caching speeds up the indexing pipeline — reducing I/O when re-indexing or refreshing the index. At query serving time, the raw document files are not read; only the pre-embedded vectors and chunk text are accessed. A practitioner who conflates the indexing pipeline with the query pipeline makes this error.

**Why C is wrong:** Embedding caching is a real optimization — if the same query text is submitted twice, the embedding model call can be skipped on the second request. But embedding calls are typically 10–50x cheaper than LLM generation calls. A practitioner who focuses on embedding cost because it is the most frequent API call may choose C without comparing the per-call cost differential.

**Why D is wrong:** Keeping the vector index in RAM eliminates disk I/O during ANN search, reducing retrieval latency. This is a performance optimization, not a cost reduction strategy — managed vector databases typically charge per query regardless of whether the index is memory-resident. A practitioner conflating latency improvement with cost reduction chooses D.

---

## MCQ-2 — Index staleness

**Difficulty:** novice
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

**Why A is wrong:** The embedding model version is fixed at deployment and does not change when new documents are ingested. A practitioner who confuses model fine-tuning (retraining a model on new data) with RAG indexing (embedding existing text with a fixed model) chooses A. The model does not learn from new documents; it only produces embeddings for them.

**Why C is wrong:** Adding new document vectors to a vector index is an append operation — the embedding store adds new entries without touching existing ones. An HNSW or IVF index rebuilds its graph/cluster structure incrementally on inserts but does not corrupt existing vectors. A practitioner who misunderstands how vector database inserts work may fear corruption, but this is not the relevant risk.

**Why D is wrong:** Cache invalidation after a full index rebuild is a real concern in systems that cache query/answer pairs — if the index now contains different results for the same query, cached answers may be stale. However, this is an independent issue from document staleness, and the question specifically asks about the risk of the weekly rebuild cadence given daily document additions. A practitioner who focuses on caching infrastructure without considering document freshness chooses D.

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

**Why A is wrong:** Pre-fetching documents at indexing time describes a different architectural pattern (eager retrieval or pre-retrieval caching) that reduces retrieval latency, not the async job model. Async processing does not eliminate retrieval latency — it merely hides that latency from the client by accepting the request immediately and deferring processing. A practitioner who conflates the latency-hiding effect of async with eliminating retrieval altogether chooses A.

**Why C is wrong:** LLM generation quality is determined by the model, prompt, and retrieved context — not by how much time elapses between request and response. Async processing gives the server more scheduling flexibility but does not change what the LLM receives or how it generates. A practitioner who believes "more processing time = better output" makes this error, which would be true for iterative search processes but not for a single LLM generation pass.

**Why D is wrong:** Parallelizing retrieval and generation within a single request is not possible in a standard RAG pipeline — generation requires the retrieved documents as input. They are not independent operations that can run concurrently. A practitioner who knows about parallel processing but does not understand the data dependency between retrieval and generation chooses D.

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

**Why A is wrong:** Token usage and cost are necessary for budget management but are lagging indicators of quality — they can hold steady while the system produces confidently wrong answers. A practitioner who comes from a cost-optimization background may default to billing metrics without recognizing that a RAG system can be on-budget and completely broken from a quality standpoint.

**Why C is wrong:** LLM generation is instrumentable in several ways: response latency (time-to-first-token, total completion time), output token count, error rate on API calls, and sampled output quality via LLM-as-judge. "Black box" is a common misconception about hosted LLM APIs — the inference is opaque internally, but inputs, outputs, latency, and error rates are all observable at the API boundary. A practitioner who has never added LLM instrumentation may assume it is impossible.

**Why D is wrong:** Error rates and uptime are the minimum viable operations metrics, but they are binary indicators — the system is up and not throwing exceptions while silently degrading in quality. A RAG system can have 99.9% uptime while faithfulness has drifted from 0.85 to 0.40 over three months. A practitioner with a pure SRE background who equates "running" with "working correctly" chooses D.

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

**Why A is wrong:** Assuming the LLM will self-diagnose retrieval failure is wishful thinking and empirically false. When given irrelevant context, LLMs frequently generate confident-sounding answers grounded in that irrelevant content rather than declaring uncertainty. This failure mode — the LLM treating noise as signal — is precisely what the similarity threshold is designed to prevent. A practitioner who over-trusts LLM self-awareness makes this error.

**Why C is wrong:** Retrieving top-20 when similarity is low returns the 20 most similar chunks among a set where even the best match is poor. The additional 15 chunks add noise and token cost without improving signal quality. The fundamental problem is not coverage (a top-K problem) but relevance (a corpus gap or query mismatch problem). More irrelevant chunks do not average out to a relevant answer. A practitioner who diagnoses low similarity as "not enough chunks" rather than "no relevant content" chooses C.

**Why D is wrong:** Falling back to parametric knowledge when retrieval fails defeats the entire purpose of RAG: grounded, verifiable answers. The system would silently switch from retrieval-augmented generation to ungrounded generation without the user knowing. Hallucination risk is highest precisely in the domains where a user is consulting a specialized knowledge base — because the parametric knowledge of a general-purpose LLM is least reliable there. A practitioner who sees the LLM's parametric knowledge as a reliable fallback has not internalized the domain-specificity assumption behind RAG systems.

---

## MCQ-6 — Silent cascade failure from upstream latency

**Difficulty:** intermediate
**Topic:** production_patterns

**Question:**
A production RAG system has three external dependencies: an embedding API, a managed vector database, and an LLM API. During an incident, the embedding API responds slowly (3–5s per call instead of 50ms). No errors are returned. What is the most likely observed production failure mode?

**Options:**
A. The retrieval stage begins returning random results because slow embeddings are numerically corrupted
B. The system appears to work — queries complete successfully — but p99 latency balloons from 2s to 8–10s, thread pools exhaust under concurrent load, and the system degrades to effectively zero throughput without throwing any exceptions
C. The LLM begins hallucinating at higher rates because it receives the embeddings out of order
D. The vector database triggers its health check timeout and marks itself as unavailable, surfacing a clear 503 error to users

**Correct answer:** B

**Explanation:**
Latency degradation in an upstream dependency is one of the most dangerous production failure modes because it is silent at the error level. The embedding API is returning results — just slowly. Each individual request eventually completes. But at any non-trivial concurrency level, threads (or async tasks) accumulate while waiting for the slow embedding API. Eventually the thread pool or queue fills, new requests start timing out, and the system collapses under its own backlog. This manifests as cascading latency increase and eventually request failures — with no upstream error code triggering an alert. Option A is incorrect — slow responses are not numerically corrupted. Option C is incorrect — LLM hallucination is not caused by embedding latency. Option D is incorrect — the embedding API is responding (just slowly), so it will not trigger a typical health check timeout.

**Why A is wrong:** Embedding computation correctness does not depend on response time. A slower response is simply the same vector delivered later — the embedding model's computation is deterministic given the input text. A practitioner who confuses "slow API" with "degraded API output quality" makes this error.

**Why C is wrong:** LLM hallucination is caused by absent or low-quality context in the prompt, not by the timing of upstream dependencies. The LLM receives the embedded query results and generates based on their content, not their latency. A practitioner who models the LLM as a component that degrades when the upstream pipeline is stressed chooses C.

**Why D is wrong:** Health checks typically detect complete failures (timeout + no response) or explicit error responses. A dependency that is responding slowly — even if very slowly — often passes health checks because it is technically alive and returning 200s. This is the essence of the silent cascade: the system is "healthy" by every check that a standard monitoring setup would run, while silently becoming unusable.

---

## MCQ-7 — Cold-start latency at system boot

**Difficulty:** intermediate
**Topic:** production_patterns

**Question:**
A newly deployed RAG service starts taking queries immediately after boot. During the first 30 seconds, response latency is 10–15x higher than steady-state. There are no errors. What is the most likely explanation?

**Options:**
A. The LLM API applies rate limiting to new API keys for the first 30 seconds
B. The JVM or Python runtime is running garbage collection on startup, stalling every request during collection cycles
C. The vector database index, embedding model, and LLM connection pool all undergo lazy initialization on first use — the first several requests each trigger a cold-start cost that amortizes across later requests after warmup
D. The load balancer is routing traffic to the new instance before its health check has completed, causing requests to queue at the network layer

**Correct answer:** C

**Explanation:**
Cold-start latency in RAG systems typically compounds multiple lazy initialization costs: the vector database client establishes its connection pool on the first query; the embedding model (if locally hosted) loads its weights into memory (or GPU) on the first call; the LLM API client initializes its HTTP connection pool; internal caches are empty. Each of these adds latency to the first requests. After warmup, subsequent requests amortize these costs. The correct mitigation is an explicit warmup step at deployment: issue synthetic queries against each component before the instance receives production traffic. Option A (LLM API rate limiting on new keys) is not standard behavior for major providers. Option B (GC) is a real JVM concern but would cause periodic stalls throughout the instance's life, not just the first 30 seconds. Option D describes a load balancer misconfiguration, not a latency characteristic of the application itself.

**Why A is wrong:** LLM API providers do not impose a "new key warmup" latency window. Rate limiting applies to request rate, not to first-use latency. A practitioner who has experienced rate limit issues may guess A, but rate limiting manifests as 429 errors or request queuing at the provider — not as elevated latency on successful requests.

**Why B is wrong:** JVM garbage collection pressure is a real latency concern, but it applies throughout an instance's lifetime — not specifically to the first 30 seconds. Additionally, the question describes a Python service. Python's garbage collector can cause latency, but the characteristic pattern of GC-induced latency is periodic spikes at any point in the lifecycle, not a one-time startup effect.

**Why D is wrong:** A load balancer health check timeout would cause traffic to reach the instance before it is ready, but this would manifest as connection errors or 503 responses — not as successful queries with elevated latency. Load balancer misconfigurations typically produce explicit failures, not slow-but-successful requests.

---

## MCQ-8 — Embedding model version drift in production

**Difficulty:** advanced
**Topic:** production_patterns

**Question:**
A RAG system has been running in production for 8 months. The team upgrades the embedding model used at query time to a new version that performs better on benchmarks, while the vector index was built with the original model. Retrieval quality collapses to near-random. What is the precise mechanism, and what is the correct rollout procedure?

**Options:**
A. The new embedding model produces longer vectors that the vector database cannot store without truncation, corrupting similarity computations
B. The new model's vectors occupy a completely different learned coordinate space from the index — cosine similarity between a new-model query vector and an old-model document vector is numerically meaningless. The correct procedure is: build and validate a shadow index with the new model, atomically switch query traffic to the new index, then retire the old index
C. The embedding model upgrade triggered a vector database schema migration that failed silently, leaving some index partitions with the old schema
D. Modern embedding models are trained with different normalization conventions, so the new model's vectors have a different magnitude range that makes cosine similarity inaccurate

**Correct answer:** B

**Explanation:**
Embedding models map text into a high-dimensional vector space where each dimension corresponds to a learned latent feature. Two different model versions learn different features — different axes of variation in the training data. There is no mathematical correspondence between dimension 47 in model v1 and dimension 47 in model v2. Cosine similarity measures the angle between vectors in the same space; across spaces, the number produced is numerically valid but semantically meaningless. The shadow-index rollout procedure eliminates downtime: the new index is built in parallel while the old index serves production traffic; after validation, traffic is switched atomically; the old index is retained for a rollback window. Option A is incorrect — embedding dimensions are fixed by model architecture; a newer model does not produce vectors of variable length. Option C is incorrect — vector database schema migrations are a separate operational concern unrelated to the semantic incompatibility. Option D identifies a real concern (normalization conventions) but this is a secondary factor; the primary issue is incompatible vector spaces, not magnitude differences.

**Why A is wrong:** Embedding model architectures produce fixed-dimension vectors determined by model design (e.g., 768 or 1536 dimensions). A model upgrade within the same family (e.g., text-embedding-ada-002 to text-embedding-3-small) may change dimension count, but this would cause an immediate schema error on insertion — not silent near-random retrieval. A practitioner who has seen dimension mismatch errors in other ML pipelines may guess A.

**Why C is wrong:** Vector database schema migrations are explicit operations triggered by administrators — they do not happen automatically on embedding model upgrades. The vector store has no knowledge of which embedding model was used to produce its contents. This distractor catches practitioners who are familiar with database migration risks but do not understand that the embedding model and the vector store are decoupled components.

**Why D is wrong:** Normalization conventions do affect whether dot product equals cosine similarity (as covered in embedding fundamentals), but most modern embedding models either produce unit-normalized vectors or the vector database normalizes them. Even if magnitude differences existed, they would reduce ranking quality modestly — they would not collapse retrieval to near-random. The near-random behavior described in the question is the signature of fully incompatible vector spaces, not of magnitude scaling differences.

---

## MCQ-9 — Latency budget allocation across pipeline stages

**Difficulty:** advanced
**Topic:** production_patterns

**Question:**
A RAG API has a 3-second end-to-end SLA. A performance audit reveals: embedding inference takes 80ms, vector search takes 120ms, reranking takes 400ms, and LLM generation takes 1800ms (p50). At p99, LLM generation spikes to 4200ms, blowing the SLA. Which of the following is the most operationally correct response?

**Options:**
A. Disable reranking — it contributes 400ms and the LLM is already providing quality; removing it reclaims the budget
B. Move LLM generation to an async response model for all queries, accepting that the product UX changes from synchronous to poll-based
C. Set a per-stage timeout budget and configure a circuit breaker on LLM generation with a 2500ms limit — requests exceeding the budget return a graceful degradation response; investigate LLM provider tail latency patterns and switch to streaming responses with partial delivery for queries that approach the budget
D. Increase the SLA to 5 seconds to accommodate p99 LLM behavior without requiring infrastructure changes

**Correct answer:** C

**Explanation:**
The correct response to LLM tail latency has multiple components working together. A per-stage timeout budget makes the SLA a hard contract rather than a best-effort goal. A circuit breaker on LLM generation with a timeout limit prevents p99 outliers from blocking the system indefinitely — queries that would exceed the budget return a graceful response ("unable to generate a complete answer") rather than timing out silently. Streaming responses with partial delivery (streaming tokens to the client as they are generated) allow users to start reading before the full response is ready, effectively hiding generation latency. The investigation into LLM provider tail latency patterns is also essential — p99 spikes often correlate with provider-side cold starts, instance recycling, or specific query types. Option A improves latency modestly (400ms) but does not address the root cause (LLM p99 spikes) and sacrifices retrieval quality. Option B is a valid architectural change for appropriate use cases but represents a major UX regression and should not be the first response to a p99 issue. Option D defers the problem and accepts SLA degradation without addressing the underlying cause.

**Why A is wrong:** Removing the reranker saves 400ms at p50 but does nothing about the LLM p99 spike (4200ms) — the system would still blow the SLA at p99. Additionally, the reranker is doing real work: improving the ranking of retrieved chunks before they reach the LLM. Removing it degrades generation quality in exchange for marginal latency improvement that does not solve the actual problem. A practitioner who optimizes greedily (remove the next biggest contributor) without looking at the tail distribution makes this error.

**Why B is wrong:** Async/polling is a valid architectural pattern for very long-running queries, but it is a significant product change that affects all users — not a surgical fix for p99 tail latency. It trades synchronous SLA compliance for asynchronous delivery, which may be unacceptable for a conversational interface. The question asks for the "most operationally correct response" — a targeted fix is preferable to a wholesale UX architecture change for a p99 latency problem.

**Why D is wrong:** Changing the SLA to accommodate observed behavior is a common anti-pattern that makes the problem invisible without solving it. The LLM p99 spike is a real infrastructure risk — it will worsen under load, not stabilize. Accepting 5s as the new SLA defers the problem and accepts user experience degradation as a permanent outcome. A practitioner who defaults to adjusting targets instead of addressing root causes chooses D.

---

## MCQ-10 — Silent failure from prompt template regression

**Difficulty:** expert
**Topic:** production_patterns

**Question:**
After a routine deployment, a production RAG system's faithfulness scores drop from 0.88 to 0.52 within an hour. No infrastructure alerts fire. No errors appear in logs. Retrieval metrics (context precision and recall) are unchanged. What is the most likely root cause and how would you verify it in under 5 minutes?

**Options:**
A. The vector database experienced a split-brain event during the deployment, causing half of queries to retrieve from a stale replica
B. The LLM API provider silently released a model update that changed generation behavior
C. A prompt template change in the deployment altered the system instruction or context delimiters — the LLM is now generating from its parametric knowledge rather than the retrieved context. Verify by diffing the live prompt template against the last known-good version from the deployment that preceded the incident
D. The deployment introduced a memory leak that is causing the LLM context to be partially overwritten with previous query contents

**Correct answer:** C

**Explanation:**
When faithfulness drops sharply immediately after a deployment while retrieval metrics hold steady, the fault is almost certainly in the generation stage and introduced by the deployment. A prompt template regression is the most common culprit: a removed or altered "answer only from context" instruction, a changed context block delimiter that the LLM no longer recognizes as context, or a modified system instruction that invites the LLM to use its general knowledge. The 5-minute verification is a diff of the current live prompt template against the last-committed version in version control. If the diff shows a change to the system instruction or context formatting, that is the confirmed root cause — roll back the deployment. Option A (split-brain) would manifest as inconsistent retrieval results across replicas, detectable in context precision/recall metrics. Option B (LLM provider update) is possible but cannot be the answer here because the timing is the deployment, not an LLM API event; and LLM providers do not silently update model behavior without any announcement. Option D describes a memory corruption failure mode that does not exist in standard LLM API serving — each request is stateless.

**Why A is wrong:** A vector database split-brain event would cause retrieval inconsistencies — some queries would return poor results from the stale replica, and context precision or recall would degrade in aggregate. The question specifies that retrieval metrics are unchanged, which eliminates retrieval-layer explanations. A practitioner who jumps to infrastructure explanations before reading the metric pattern chooses A.

**Why B is wrong:** LLM provider silent updates happen, but this failure is correlated with the deployment window, not with a provider event. The correct diagnostic priority is to check what changed in the most recent deployment before assuming an external provider change. Furthermore, LLM provider model updates are typically announced via release notes and version identifiers — not truly silent. A practitioner who over-attributes production failures to external dependencies rather than internal changes chooses B.

**Why D is wrong:** LLM API calls are stateless — each API request receives an independent response with no shared memory across requests. "Context overwriting from previous queries" describes a session-level memory bug in application code (such as incorrectly reusing a mutable prompt object), not a general LLM serving property. If this were the bug, it would also cause unusual content in responses, not just faithfulness degradation. This distractor catches practitioners who attribute LLM behavior to hardware-level memory concepts they understand from lower-level systems.

---

## MCQ-11 — Circuit breaker pattern for downstream dependency failures

**Difficulty:** expert
**Topic:** production_patterns

**Question:**
A production RAG system uses a managed LLM API that occasionally experiences brief outages (2–5 minutes). During these windows, the current system retries each failed request 3 times with exponential backoff, then returns an error. Under moderate load (50 concurrent users), this retry behavior amplifies the outage. Why does retry amplify the problem and what pattern resolves it?

**Options:**
A. Retries consume more tokens per query, causing the LLM provider to throttle the account more aggressively. Resolve by caching all retry attempts
B. Each retry extends the time a connection and thread are held open, causing the thread pool to fill with waiting-and-retrying requests. Under load, new incoming requests cannot be handled — a small provider outage becomes a full service outage. Resolve with a circuit breaker: after N consecutive failures, stop forwarding requests to the LLM API immediately, return a cached or degraded response, and probe recovery at intervals
C. Retry logic introduces duplicate responses — the LLM returns two different answers for the same query, causing inconsistency. Resolve with idempotency keys on all LLM API calls
D. Exponential backoff is incompatible with async event loops and causes the Python event loop to block. Resolve by replacing backoff with fixed-interval retries

**Correct answer:** B

**Explanation:**
Retry amplification is a well-documented distributed systems failure mode. When a dependency fails, retrying keeps connections and resources tied up. With 50 concurrent users and 3 retries each at exponential backoff (say, 1s, 2s, 4s), each request occupies a connection for up to 7 seconds. At moderate load, this fills the connection and thread pool with waiting requests, preventing new requests from being handled — even requests that do not need the LLM (e.g., health checks, cached responses). A circuit breaker stops forwarding requests to the failing dependency after a failure threshold, allowing the system to fail fast instead of accumulating blocked resources. During the open (tripped) state, the circuit breaker returns a pre-defined degraded response immediately, keeping the thread free. It probes recovery by allowing a single probe request at intervals, closes when recovery is confirmed. Option A conflates retry count with token usage. Option C is a real concern for idempotency (duplicate LLM calls may return different responses), but it is not the amplification mechanism described. Option D is incorrect — exponential backoff implemented with asyncio.sleep does not block the event loop; blocking would only occur with synchronous time.sleep in an async context.

**Why A is wrong:** LLM tokens are consumed per request, and retries do multiply token usage, but the mechanism of amplification described in the question is thread/connection exhaustion, not token quota exhaustion. Token throttling from the LLM provider would manifest as 429 rate-limit responses on the retried calls, not as a full service outage from the RAG system's perspective. A practitioner focused on cost management may guess A.

**Why C is wrong:** Idempotency ensures that multiple identical requests produce the same outcome at the server side — relevant for preventing duplicate side effects (like charging a credit card twice). For LLM generation, the concern is output variance (non-deterministic generation), not idempotency in the distributed systems sense. This distractor catches practitioners familiar with idempotency from payment systems who apply it outside its domain.

**Why D is wrong:** Exponential backoff with asyncio.sleep is non-blocking in an async event loop — the coroutine suspends while the event loop continues processing other requests. The statement that "exponential backoff is incompatible with async event loops" is false for correct async implementations. The actual danger is synchronous time.sleep called from within an async context, but this is a code correctness issue, not an inherent incompatibility. A practitioner who has debugged async Python code may have seen blocking-sleep bugs and overgeneralized.

