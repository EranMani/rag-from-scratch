# Question Bank: `production_patterns`
# Phase: 3 — Production
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-21 (Commit 45)

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

---

## Q9 — Faithfulness regression with stable retrieval metrics

**Difficulty:** advanced

**Question:**
Your production RAG system shows a faithfulness regression: the rolling 7-day faithfulness
average dropped from 0.84 to 0.67 over 5 days. Context precision and context recall are
stable (within 2% of baseline). You have not changed the embedding model, the vector
database, or the retrieval configuration. What are the three most likely root causes, and
how would you isolate which one is responsible?

**Correct answer criteria:**
The learner must demonstrate understanding that faithfulness is a generation-stage metric —
retrieval stability rules out the retrieval layer and focuses the investigation on what
changed between retrieved context and generated answer.

- Root cause 1 — LLM API behavior change: the LLM provider silently updated the model
  (version rollover within the same API endpoint), changed sampling behavior, or
  experienced a capability regression. Isolation: pull a fixed set of 20–30 prompt +
  context pairs from before and after the regression and run them against the current LLM
  endpoint. If outputs are systematically less grounded, compare with the prior LLM version
  or a pinned snapshot if available.

- Root cause 2 — Prompt template change: a deployment changed the system prompt, context
  delimiter format, or grounding instruction (e.g., the "answer only from context" rule
  was removed or weakened). Isolation: diff the live prompt template against the last known-
  good version. Run the same query with both templates against the same retrieved context
  and compare faithfulness scores.

- Root cause 3 — Query distribution shift: the query population changed (new user segment,
  new query types) such that the LLM is now generating answers for queries that require
  synthesis from multiple sparse chunks, or for queries where the retrieved context is
  technically present but doesn't directly state the answer. Faithfulness drops when the
  LLM must infer or synthesize rather than quote. Isolation: segment faithfulness by query
  type or query length. If newer queries cluster at lower faithfulness, the issue is
  distribution shift, not a system change.

**Partial credit criteria:**
- Identifies two root causes but only one isolation method
- Correctly identifies the distinction (generation vs. retrieval failure) but cannot
  propose concrete diagnostic steps for each hypothesis

**Incorrect / no-credit criteria:**
- Recommends changing the embedding model or retrieval top_k (stable retrieval metrics
  already rule out the retrieval layer)
- Cannot identify any generation-stage failure mode
- Describes "run more tests" without specifying what to test or what signal to look for

---

## Q10 — Graceful degradation when the vector database is unavailable

**Difficulty:** advanced

**Question:**
Your vector database becomes unavailable (network partition, database outage). Your RAG
system is still receiving user queries. Design a graceful degradation strategy that
maintains some useful service rather than returning hard errors, and identify what you
must pre-position to make each degradation tier possible.

**Correct answer criteria:**
- Tier 1 — In-memory fallback: maintain a small in-memory index of the N most-queried
  chunks (e.g., the top-200 chunks by historical query frequency). Serve these for queries
  that match, returning a degraded-quality answer with a "limited context" notice. What
  to pre-position: a cache warm-up process that populates the in-memory index on startup
  from a pre-built snapshot; a query frequency counter to determine which chunks to cache.

- Tier 2 — Cache-only serving: return semantically cached responses for queries that
  match an existing cache entry (from the semantic cache layer). No retrieval required.
  What to pre-position: a semantic cache must already be warmed before the outage. For new
  queries that miss the cache, escalate to Tier 3.

- Tier 3 — LLM without context: for queries with no cached response and no in-memory
  match, invoke the LLM without retrieved context. Return the answer with an explicit
  notice: "Our knowledge base is currently unavailable. This answer is based on general
  knowledge and may not reflect your specific documentation." What to pre-position:
  a fallback prompt template that removes the context block and adds the caveat notice.

- Circuit breaker pattern: the degradation tiers should be managed by a circuit breaker
  that detects vector DB unavailability and routes traffic to the fallback path without
  each request timing out individually. What to pre-position: health check endpoint for
  the vector DB; circuit breaker threshold configuration.

**Partial credit criteria:**
- Describes one or two degradation tiers but cannot explain what must be pre-positioned
  to make each tier operational at the time of the outage
- Describes the pre-positioning requirements correctly for one tier but does not address
  multiple tiers

**Incorrect / no-credit criteria:**
- Recommends only returning a hard error message ("service unavailable")
- Cannot identify any fallback tier that preserves some useful service
- Does not address the circuit breaker pattern or the need to detect the outage quickly

---

## Q11 — LLM output drift without model changes

**Difficulty:** advanced

**Question:**
Over three months, user satisfaction scores on your RAG system decline steadily. RAGAS
faithfulness and answer relevancy scores are stable. No model changes were deployed.
What are the mechanisms by which LLM output quality can drift over time without any
model update, and how would you detect each in production?

**Correct answer criteria:**
- Mechanism 1 — Corpus drift: the knowledge base content has changed (new documents added,
  old documents updated or deleted). The retrieval stage still returns chunks at the same
  precision/recall level, but the chunks now contain different information than users expect.
  If user expectations are based on the old content, answers may be technically faithful
  to new context but wrong relative to user intent. Detection: track user negative feedback
  rate segmented by document recency. Monitor knowledge base content change velocity and
  correlate with quality drops.

- Mechanism 2 — Query distribution shift: the user population shifted. New users ask
  different questions — questions that the knowledge base was not designed to answer, or
  questions that require reasoning patterns the prompt does not support. The LLM faithfully
  generates from poor context; faithfulness is stable but the answers are less useful.
  Detection: analyze query embedding distribution over time. A shift in the query centroid
  or an increase in query-context cosine distance signals distribution shift.

- Mechanism 3 — Implicit LLM provider change: the LLM API provider rolled the underlying
  model version (common with "gpt-4" endpoints that serve updated model weights without
  changing the API name). Output style, verbosity, or instruction-following behavior may
  have changed. Detection: pin a test suite of 50 fixed prompts with expected outputs.
  Run this suite weekly. Deviations in output format, length distribution, or refusal rate
  signal an implicit model change.

- Mechanism 4 — Seasonal or topical context shift: documents or queries reference time-
  sensitive content (regulatory changes, product launches, market conditions). The LLM
  faithfully reports what the retrieved documents say, but the documents are now outdated
  relative to reality. RAGAS scores stay high (faithful to stale context) but user
  satisfaction drops. Detection: include freshness metadata in monitoring; alert when
  median document age in retrieved contexts exceeds a threshold.

**Partial credit criteria:**
- Identifies two mechanisms with correct detection strategies
- Identifies three or four mechanisms but cannot propose a detection approach for each

**Incorrect / no-credit criteria:**
- Describes only model changes as causes of drift (misses corpus, query distribution,
  and provider-side changes)
- Cannot distinguish faithfulness-stable drift (the system works as designed but the
  design is no longer correct for the environment) from faithfulness-unstable drift
  (the system is generating ungrounded content)
