# Question Bank: `production_patterns`
# Phase: 3 — Production
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-11 (Commit 22)

---

## Q1 — Semantic caching fundamentals

**Difficulty:** beginner

**Question:**
Explain semantic caching in the context of a RAG system. How does it differ from
exact-match caching, and what is the primary risk of using it?

**Correct answer criteria:**
- Exact-match caching: stores responses keyed by the exact query string. A cache hit
  requires the new query to match letter-for-letter. Misses on paraphrasing.
- Semantic caching: stores responses keyed by the query embedding vector. A cache hit
  occurs when the new query's embedding is within a similarity threshold of a cached
  query embedding — meaning queries that ask the same thing differently can hit the cache.
- Primary risk: stale cache hits. If the documents in the knowledge base are updated
  after a query is cached, a semantically similar query may return the old, now-incorrect
  cached answer. Unlike exact-match caches, semantic caches cannot be invalidated by
  document change events without maintaining query-to-document mappings.

**Partial credit criteria:**
- Correctly explains semantic vs. exact-match caching but cannot identify the staleness
  risk
- Identifies the staleness risk but describes semantic caching imprecisely (e.g.,
  confuses it with response memoization)

**Incorrect / no-credit criteria:**
- Describes semantic caching as caching the retrieved chunks rather than the final response
- Cannot distinguish semantic from exact-match caching
- Claims caching is always safe for RAG systems

---

## Q2 — Async pipeline design

**Difficulty:** intermediate

**Question:**
Identify two operations in a RAG pipeline that should be non-blocking (async), and
explain what happens if they are implemented as blocking synchronous calls in a
high-traffic production system.

**Correct answer criteria:**
- Operation 1: Vector store query — the similarity search against a remote vector
  database involves network I/O. As a blocking call, each request occupies a thread
  waiting for the response. Under high concurrency, threads are exhausted, new requests
  queue or fail, and throughput collapses.
- Operation 2: LLM API call — LLM inference is high-latency (seconds). As a blocking
  call, the serving thread waits idle for the entire generation time. Async allows the
  thread to handle other requests while waiting for the LLM response.
- What happens with blocking calls at scale: thread pool exhaustion, cascading queue
  buildup, increased tail latency, and eventually dropped requests or timeouts. The
  system cannot serve concurrent users efficiently.
- Acceptable alternative operations: embedding model API call, document loader I/O
  (reading files), any network-bound external service call.

**Partial credit criteria:**
- Identifies two async candidates but can only explain the failure mode for one
- Correctly describes the failure mode but identifies only one operation

**Incorrect / no-credit criteria:**
- Cannot identify any operation that should be async
- Describes async as "running in a separate process" rather than "non-blocking I/O"
- Claims blocking calls are fine if the server has enough threads

---

## Q3 — Minimum observability instrumentation

**Difficulty:** intermediate

**Question:**
You are adding observability to a RAG system that currently has no tracing or logging.
List the minimum set of measurements you would instrument, organized by pipeline stage,
and explain what each tells you about system health.

**Correct answer criteria:**
The answer should cover all three stages:

**Retrieval stage:**
- Query embedding latency — how long the embedding model takes per query
- Vector store query latency — time for the similarity search
- Number of chunks retrieved (K) and their similarity scores — signal for retrieval
  relevance quality

**Generation stage:**
- Prompt token count — cost and context window pressure signal
- LLM response latency (time-to-first-token and total completion time)
- Output token count — cost signal

**Overall pipeline:**
- End-to-end request latency — user-facing performance
- Fallback rate (how often "I don't know" is returned) — proxy for retrieval quality
- Error rate (failed embedding calls, vector store timeouts, LLM errors)

Each measurement should be linked to what it indicates: latency spikes indicate
infrastructure degradation; similarity score drops indicate embedding quality issues
or index staleness; token count increases indicate prompt bloat or corpus growth.

**Partial credit criteria:**
- Lists measurements for two of three pipeline stages
- Lists the right measurements but cannot connect them to what they indicate about health

**Incorrect / no-credit criteria:**
- Only lists the final output (user-facing response quality) as the metric
- Cannot organize measurements by pipeline stage
- Lists fewer than five distinct measurements

---

## Q4 — The three cost drivers and their mitigations

**Difficulty:** intermediate

**Question:**
Identify the three primary cost drivers in a production RAG system and describe one
concrete mitigation for each.

**Correct answer criteria:**
1. Embedding API calls:
   - Cost driver: every document chunk requires an embedding call at indexing time;
     every query requires an embedding call at query time
   - Mitigation: cache query embeddings (the same query asked twice doesn't need
     re-embedding); batch embedding calls during indexing to reduce per-call overhead;
     use a smaller/cheaper embedding model for queries while reserving a higher-quality
     model for document indexing

2. LLM inference tokens:
   - Cost driver: every query consumes prompt tokens (template + retrieved chunks) and
     output tokens (the generated answer). Long context windows and high top-K multiply
     prompt token cost.
   - Mitigation: reduce top-K to decrease prompt tokens per query; summarize or compress
     retrieved chunks before injection (trading compute for token cost); implement
     semantic caching to serve cached responses for frequently repeated queries

3. Vector store queries:
   - Cost driver: managed vector databases charge per query (or per vector). High-traffic
     systems issue millions of vector queries daily.
   - Mitigation: semantic caching to reduce the vector store query rate; query batching
     for bulk retrieval operations; for read-heavy workloads, use a self-hosted vector
     store to convert per-query charges to fixed infrastructure cost

**Partial credit criteria:**
- Identifies all three cost drivers but provides mitigation for only one or two
- Provides mitigations for all three but misidentifies one of the cost drivers

**Incorrect / no-credit criteria:**
- Cannot identify three distinct cost drivers (names the same driver twice)
- Describes mitigation strategies that address the wrong cost driver
- Cannot identify LLM tokens as a primary cost driver

---

## Q5 — Index staleness as a failure mode

**Difficulty:** intermediate

**Question:**
Describe index staleness as a production failure mode in a RAG system. What are its
symptoms, how would you detect it in production, and what architecture change prevents it?

**Correct answer criteria:**
- What it is: the vector index contains outdated document versions. Documents were
  updated or deleted in the source system but the changes were not propagated to the
  index. Users receive answers grounded in old information.
- Symptoms: answers that contradict current product documentation, dates or version
  numbers that are clearly outdated, "I don't know" responses to questions that should
  now be answerable (new content not indexed)
- Detection in production:
  1. Track the maximum document ingestion timestamp in the index and alert if it
     falls more than N hours behind the source system's modification timestamp
  2. Monitor user negative feedback or override signals for "outdated information"
     query categories
  3. Periodic re-retrieval test with a sentinel query whose correct answer is in
     a recently updated document
- Architecture prevention: event-driven indexing — source system emits an event
  (webhook, database change data capture, message queue) on document create/update/delete;
  the indexing service consumes the event and updates only the affected chunks in the
  index without full re-indexing

**Partial credit criteria:**
- Correctly describes what staleness is and its symptoms but cannot describe detection
  or prevention
- Describes event-driven indexing as the fix but cannot explain why scheduled polling
  is insufficient in high-change-rate environments

**Incorrect / no-credit criteria:**
- Cannot distinguish index staleness from vector store downtime
- Recommends disabling caching as the staleness fix (staleness is an indexing problem,
  not a caching problem)
- Cannot describe any production monitoring approach for staleness detection

---

## Q6 — Embedding model version drift

**Difficulty:** advanced

**Question:**
Your team upgrades the embedding model from v1 to v2. The new model has better benchmark
scores. You update the query embedding but forget to re-index the document corpus.
Describe the failure that occurs, why it happens, and what the operational procedure
should be for any embedding model update.

**Correct answer criteria:**
- The failure: query vectors (v2 space) are being compared against document vectors
  (v1 space). These two vector spaces are independent — their dimensions carry different
  learned semantics. Cosine similarity between a v2 query vector and a v1 document vector
  is meaningless. Retrieval results will be near-random, not semantic.
- Why it happens: embedding model versions produce incompatible vector spaces. Unlike a
  software library update (which should be backward-compatible), an embedding model
  update produces a fundamentally different coordinate system. There is no valid
  transformation between the spaces.
- Operational procedure:
  1. Never update the query embedding model without simultaneously re-indexing the entire
     document corpus with the same model version
  2. For zero-downtime: build the new index in parallel (shadow index) while the old
     index continues serving; switch traffic atomically when the new index is complete
     and validated
  3. Record the embedding model version in the index metadata and enforce a version
     check at query time — reject or warn if query and document embedding versions differ
  4. After rollout, deprecate old index; keep it available for rollback window

**Partial credit criteria:**
- Correctly identifies that retrieval becomes meaningless but cannot explain why
  (cannot explain the incompatible vector spaces concept)
- Describes the correct operational procedure but cannot identify the failure mechanism

**Incorrect / no-credit criteria:**
- Believes the model upgrade only affects precision, not correctness
- Recommends normalizing vectors to make them compatible across model versions
- Does not identify re-indexing as a required step in any model upgrade procedure

---

## Q7 — Context length overflow under load

**Difficulty:** advanced

**Question:**
In normal traffic, your RAG system comfortably fits prompts within the LLM's context
window. Under high query complexity (multi-part questions, users pasting long texts),
prompts begin exceeding the context limit and the system silently truncates context or
errors. Describe how you would detect this failure mode before it affects users, and
design a graceful degradation strategy.

**Correct answer criteria:**
- Detection before it affects users:
  1. Track prompt token count as a metric (p95 and p99 percentiles). Alert when p95
     exceeds 80% of the context window limit — this gives headroom before overflow occurs.
  2. Log the token count distribution over time. Gradual increase may indicate corpus
     growth or prompt template changes pushing toward the limit.
  3. Test with synthetic edge-case queries (maximum-length user inputs, maximum-complexity
     queries) as part of load testing.
- Graceful degradation strategy:
  1. Pre-injection token budget check: before injecting all retrieved chunks, compute
     total token count. If it would exceed the limit, apply a ranked truncation:
     drop lowest-scored chunks first (not arbitrary truncation which loses the most
     relevant context last).
  2. User-visible degradation: when context must be reduced, append a notice
     ("Based on the most relevant passages from your knowledge base...") to signal
     to the user that the answer may be partial.
  3. Query decomposition fallback: for very long queries, decompose into sub-queries
     and synthesize results rather than failing on the original complex query.

**Partial credit criteria:**
- Describes detection (metric monitoring) but no graceful degradation strategy
- Describes ranked truncation correctly but cannot describe how to detect the failure
  mode before it affects users

**Incorrect / no-credit criteria:**
- Recommends only upgrading to a larger context window (does not address immediate
  detection or graceful handling)
- Describes random truncation as acceptable (does not account for the impact on
  answer quality when the most relevant context is cut)
- Cannot identify token count monitoring as a pre-failure detection mechanism

---

## Q8 — Designing a failure mode playbook

**Difficulty:** advanced

**Question:**
You are the on-call engineer for a production RAG system. At 2 AM, an alert fires
indicating answer quality has degraded significantly (faithfulness dropped from 0.85
to 0.40 in the past hour). Describe your diagnostic process step-by-step to identify
the root cause, covering at least three distinct hypotheses you would investigate.

**Correct answer criteria:**
The learner should demonstrate a systematic, stage-by-stage diagnostic approach:

- Step 1: Check what changed in the past hour (deployments, index updates, upstream API
  changes). Look at the deployment log.
- Hypothesis 1 — LLM API degradation: the LLM provider experienced an incident. Check
  the LLM response latency metrics and error rate. Faithfulness drops if the LLM is
  returning truncated or malformed responses due to provider-side errors.
- Hypothesis 2 — Index staleness / corruption: a bulk document update or failed indexing
  job caused the vector index to return garbage or stale results. Check the last
  successful indexing timestamp and whether context precision also dropped (low precision
  + low faithfulness together point to retrieval feeding the LLM bad context).
- Hypothesis 3 — Prompt template regression: a code deployment changed the prompt
  template (removed the "answer only from context" instruction or changed context
  delimiters). Check the deployment history and diff the live prompt template against
  the last known-good version.
- Step N: for each confirmed hypothesis, describe the rollback or mitigation action:
  - LLM degradation: fail over to a backup LLM or degrade to a "service degraded" notice
  - Index corruption: roll back to last known-good index snapshot
  - Prompt regression: roll back the deployment

**Partial credit criteria:**
- Names three hypotheses but the diagnostic procedure is not step-by-step (no ordering
  or prioritization logic)
- Correct step-by-step procedure but only two distinct hypotheses

**Incorrect / no-credit criteria:**
- Cannot name more than one hypothesis
- Recommends restarting the service without any diagnostic step
- Conflates all three hypotheses as the same root cause (e.g., "the LLM is broken")
