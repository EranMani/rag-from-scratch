# MCQ Bank — evaluation_and_metrics
# Topic: evaluation_and_metrics
# Phase: 3 (Production)
# Questions: 5 (2 beginner, 2 intermediate, 1 advanced)
# Last updated: 2026-05-19 (Commit 33)

---

## MCQ-1 — RAGAS faithfulness definition

**Difficulty:** beginner
**Topic:** evaluation_and_metrics

**Question:**
What does the RAGAS metric "faithfulness" measure in a RAG system?

**Options:**
A. How well the retrieved chunks match the user's question
B. The fraction of claims in the generated answer that are supported by the retrieved context
C. How closely the generated answer matches a human-written reference answer
D. The proportion of relevant documents in the corpus that were successfully retrieved

**Correct answer:** B

**Explanation:**
Faithfulness measures whether the claims the LLM makes in its answer are attributable to the retrieved passages. A faithful answer contains no information the LLM invented beyond what the context supports. Option A describes context precision/recall — a retrieval quality metric. Option C describes answer similarity to a reference (closer to RAGAS answer correctness). Option D describes retrieval recall.

---

## MCQ-2 — Context precision definition

**Difficulty:** beginner
**Topic:** evaluation_and_metrics

**Question:**
What does "context precision" measure in RAG evaluation?

**Options:**
A. The fraction of retrieved chunks that are actually relevant to answering the query
B. The fraction of information needed to answer the query that is present in the retrieved chunks
C. The accuracy of the embedding model at ranking the top-1 result above all others
D. The percentage of the retrieved context that the LLM uses in its final answer

**Correct answer:** A

**Explanation:**
Context precision measures retrieval quality from the perspective of signal-to-noise: of all the chunks returned, how many were relevant? A high-precision retrieval returns mostly useful chunks. Option B describes context recall — the coverage metric. Option C describes ranking accuracy, which is a retrieval evaluation but not RAGAS context precision. Option D measures LLM utilization of context, not retrieval precision.

---

## MCQ-3 — Low faithfulness vs. low context recall

**Difficulty:** intermediate
**Topic:** evaluation_and_metrics

**Question:**
A RAG system scores 0.45 on faithfulness and 0.90 on context recall. What is the most likely diagnosis?

**Options:**
A. The retrieval step is poor — it is not returning the documents the LLM needs to answer accurately
B. The LLM is generating content beyond what the retrieved context supports, rather than staying grounded — retrieval quality is good but the LLM is hallucinating
C. The chunking strategy is too coarse — large chunks contain irrelevant information that confuses the LLM
D. The embedding model is mismatched between indexing and query time, producing semantically incorrect retrievals

**Correct answer:** B

**Explanation:**
High context recall (0.90) means the retrieval step is returning the information needed to answer the question — the right content is in the retrieved set. Low faithfulness (0.45) means the LLM's generated answer contains claims not supported by that context. The fault is in the generation stage: the LLM is confabulating details beyond the grounding provided. Option A describes a retrieval problem, which would show as low context recall. Option C (chunking) would affect retrieval precision/recall. Option D (model mismatch) would cause low context recall.

---

## MCQ-4 — Offline vs. online evaluation

**Difficulty:** intermediate
**Topic:** evaluation_and_metrics

**Question:**
A team has a labeled evaluation dataset of 200 query/expected-answer pairs. They use this to measure RAGAS scores before each production deployment. A colleague argues this is insufficient and suggests adding online evaluation via user feedback signals. Which statement correctly describes the complementary roles of offline and online evaluation?

**Options:**
A. Offline evaluation is more accurate; online evaluation should only be used when a labeled dataset is unavailable
B. Offline evaluation measures quality on a fixed benchmark — good for catching regressions before deployment; online evaluation captures real user query distributions and failure patterns that may not appear in the benchmark
C. Online evaluation is superior because it measures real behavior; offline evaluation only confirms the system performs well on training data
D. Offline evaluation requires human annotators; online evaluation is fully automated and therefore preferred for continuous monitoring

**Correct answer:** B

**Explanation:**
Offline evaluation (benchmark datasets) is essential for reproducible regression testing — you can compare system versions on the same queries before deploying. Online evaluation captures the actual query distribution, user satisfaction, and failure modes that only emerge in production (e.g., queries your benchmark never anticipated). Neither replaces the other: offline evaluation gates deployments; online evaluation surfaces systemic issues after deployment. Option A incorrectly ranks offline as superior. Option C incorrectly conflates benchmark data with training data — evaluation sets should be held out, not trained on. Option D is incorrect — online evaluation may require human review of sampled interactions.

---

## MCQ-5 — Answer correctness vs. faithfulness tradeoff

**Difficulty:** advanced
**Topic:** evaluation_and_metrics

**Question:**
A RAG system achieves faithfulness = 0.92 and answer correctness = 0.61. A second system achieves faithfulness = 0.71 and answer correctness = 0.84. Which statement most precisely characterizes the tradeoff and the appropriate production decision?

**Options:**
A. System 1 is better — faithfulness is more important than correctness because hallucination is a safety risk
B. System 2 is better — answer correctness directly measures whether users get right answers, which is the ultimate goal
C. The two systems represent different failure modes: System 1 is constrained but retrieval-limited (faithful but often incomplete or wrong because it only uses what it retrieved); System 2 is more capable but less grounded (often correct but sometimes fabricates). The right choice depends on the use case's tolerance for hallucination vs. incomplete answers
D. System 1 should be used for regulated industries; System 2 for consumer products — there is no universally correct choice

**Correct answer:** C

**Explanation:**
Faithfulness and answer correctness measure different failure modes. A system with high faithfulness but low correctness is grounded in retrieved context but may be providing incomplete or wrong answers because the retrieved context was insufficient — it will not make things up, but it will fail to fully answer. A system with high correctness but lower faithfulness may be drawing on parametric knowledge to supplement weak retrieval — getting the right answer more often, but with a higher hallucination risk when it does confabulate. The production decision requires understanding the use case: a medical information system may prefer System 1 (never fabricate, even at the cost of incomplete answers), while a general knowledge assistant may prefer System 2. Option D partially captures this but reduces it to an oversimplified industry rule rather than the underlying tradeoff logic.

