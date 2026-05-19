# MCQ Bank — retrieval_methods
# Topic: retrieval_methods
# Phase: 2 (Core Components)
# Questions: 5 (2 beginner, 2 intermediate, 1 advanced)
# Last updated: 2026-05-19 (Commit 33)

---

## MCQ-1 — Dense vs. sparse retrieval

**Difficulty:** beginner
**Topic:** retrieval_methods

**Question:**
What is the key difference between dense retrieval and sparse retrieval (such as BM25)?

**Options:**
A. Dense retrieval uses full document text; sparse retrieval uses only document titles and headings
B. Dense retrieval uses embedding vectors to match semantic meaning; sparse retrieval uses term frequency statistics to match exact or near-exact keywords
C. Dense retrieval is faster because it uses compressed vectors; sparse retrieval is slower because it scans full documents
D. Sparse retrieval requires a GPU; dense retrieval can run on CPU only

**Correct answer:** B

**Explanation:**
Dense retrieval embeds both queries and documents into continuous vector spaces and retrieves by vector similarity — it can match semantically related text even with no keyword overlap. Sparse retrieval (BM25 and similar) scores documents by term frequency and inverse document frequency, excelling when queries contain the same specific keywords as the target document. Neither method is universally faster (C is incorrect), and hardware requirements (D) are reversed and incorrect.

---

## MCQ-2 — When BM25 outperforms dense retrieval

**Difficulty:** beginner
**Topic:** retrieval_methods

**Question:**
For which type of query would BM25 most likely outperform a dense embedding retrieval system?

**Options:**
A. "Explain the difference between supervised and unsupervised learning"
B. "What is the capital of France?"
C. "Error code E4521 in version 3.2.1 release notes"
D. "What are some strategies for managing stress at work?"

**Correct answer:** C

**Explanation:**
BM25 excels at exact keyword matching. A query containing a specific error code and version number is best served by a retrieval method that can find the exact string "E4521" and "3.2.1" in the document. Dense embeddings may not reliably encode rare alphanumeric identifiers — they are unlikely to appear in training data with sufficient frequency to produce a distinctive embedding. Options A and D are conceptual questions well-suited to semantic retrieval. Option B is factual but short — either method would likely retrieve it if the fact is present.

---

## MCQ-3 — Hybrid retrieval fusion

**Difficulty:** intermediate
**Topic:** retrieval_methods

**Question:**
A hybrid retrieval system returns candidate lists from both a dense retrieval model and BM25. Before passing results to the LLM, the system must merge these two ranked lists into a single ranked list. Which approach correctly describes Reciprocal Rank Fusion (RRF)?

**Options:**
A. Each document's final score is the product of its dense similarity score and its BM25 score
B. Each document receives a score based on the sum of `1 / (k + rank)` across all retrieval systems that returned it, where k is a smoothing constant and rank is its position in each list
C. The dense retrieval list is used as the primary ranking; BM25 results are appended after any unique documents not already retrieved by dense retrieval
D. Both lists are normalized to the same scale, then averaged by weighted combination of the two scores

**Correct answer:** B

**Explanation:**
Reciprocal Rank Fusion assigns each document a score of `1 / (k + rank)` from each retrieval system that included it, then sums those scores across systems. Documents appearing highly ranked in multiple lists score highest. The constant k (commonly 60) prevents the formula from over-weighting the top-ranked document. Option A (score product) would penalize documents absent from one system. Option C is a simple concatenation, not fusion. Option D describes score normalization and weighted average, which is a valid alternative but not RRF.

---

## MCQ-4 — Reranking in a RAG pipeline

**Difficulty:** intermediate
**Topic:** retrieval_methods

**Question:**
Why is a reranking step often added between vector retrieval and LLM generation in a production RAG pipeline?

**Options:**
A. The reranker trains the embedding model in real time based on user feedback from each query
B. Vector similarity search optimizes for geometric proximity, which does not always correlate with relevance to the specific query intent — a reranker scores retrieved candidates against the query more precisely, improving the final top-k set
C. The reranker reduces the number of tokens sent to the LLM by compressing retrieved chunks into a single summary
D. Reranking re-indexes the vector database after each query to reflect the latest document updates

**Correct answer:** B

**Explanation:**
Vector retrieval returns documents that are geometrically close in embedding space, which is a proxy for relevance but not a direct measure of it. A reranker (typically a cross-encoder that jointly processes query and document) scores each candidate with direct attention to the query, producing a relevance ranking that is more discriminative than cosine similarity alone. This two-stage approach (fast ANN retrieval followed by precise reranking) balances latency and accuracy. Option A describes a training loop — rerankers do not retrain in real time. Option C describes summarization, not reranking. Option D describes re-indexing.

---

## MCQ-5 — Query expansion and its failure mode

**Difficulty:** advanced
**Topic:** retrieval_methods

**Question:**
A RAG developer implements query expansion: before retrieval, the system uses an LLM to generate 3 alternative phrasings of the user's query, then retrieves results for all 4 queries and deduplicates. In testing, recall improves but precision degrades significantly. What is the most precise explanation for the precision degradation?

**Options:**
A. The embedding model cannot distinguish between the original query and the expanded variants because they are semantically identical
B. LLM-generated query expansions may introduce semantic drift — the expanded queries may match documents related to the expansion terms rather than the user's original intent, adding off-topic chunks to the retrieved set
C. Query expansion increases retrieval latency beyond acceptable thresholds, causing the system to time out and return partial results
D. Deduplication removes the highest-scoring chunks because they appear in multiple result sets, leaving only lower-scoring unique results

**Correct answer:** B

**Explanation:**
Query expansion improves recall by casting a wider net — more phrasings means more chance of matching how the answer is phrased in the corpus. However, LLM-generated expansions can drift semantically: an expansion of "battery life" might include "energy density," which retrieves chemistry papers not relevant to the user's question about laptops. This semantic drift is the mechanism behind precision degradation. Option A is incorrect — semantically similar queries produce similar but not identical embedding neighbors. Option C is a latency concern, not a precision concern. Option D inverts the effect of deduplication — duplicate chunks are merged, not removed; high-frequency results score higher, not lower.

