# Question Bank: `retrieval_methods`
# Phase: 2 — Core Components
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-11 (Commit 22)

---

## Q1 — BM25 sparse retrieval fundamentals

**Difficulty:** beginner

**Question:**
Explain how BM25 retrieval works. What does it score, and give one concrete scenario
where BM25 outperforms dense vector retrieval.

**Correct answer criteria:**
- BM25 scores documents based on keyword frequency and inverse document frequency (IDF) —
  words that appear frequently in a specific document but rarely across the whole corpus
  receive high weight
- It is sparse retrieval: it operates on exact keyword matches, not on semantic meaning
- BM25 parameters include term frequency saturation (k1) and length normalization (b)
  to prevent long documents from dominating simply due to length
- Scenario where BM25 wins: exact-match queries where specific terms matter — product
  codes, legal citations, chemical formula names, rare technical identifiers, or
  queries that use vocabulary not well-represented in the embedding model's training data

**Partial credit criteria:**
- Describes BM25 as "keyword-based" without explaining term frequency or IDF weighting
- Identifies a scenario where BM25 wins but cannot explain why BM25's mechanism
  advantages that scenario

**Incorrect / no-credit criteria:**
- Describes BM25 as a semantic or neural retrieval method
- Claims BM25 always underperforms dense retrieval
- Cannot provide any scenario where BM25 outperforms dense retrieval

---

## Q2 — Dense retrieval and its failure modes

**Difficulty:** beginner

**Question:**
Dense retrieval uses embedding vectors for search. Describe two scenarios where dense
retrieval fails while BM25 would succeed, and explain what structural property of BM25
makes it better in each case.

**Correct answer criteria:**
- Scenario 1: rare technical terms / product codes — dense models are trained on general
  text and produce poor embeddings for vocabulary that appeared rarely or not at all in
  training data. BM25's exact-match weighting handles these terms regardless of training
- Scenario 2: queries requiring precise keyword match — e.g., searching for a specific
  error code "ERR_CONN_4521". Dense retrieval may return semantically related documents
  about connection errors generally; BM25 returns exactly the documents containing
  that specific string
- The structural property: BM25 does not depend on learned representations — it operates
  on token frequency statistics which are computed directly from the corpus, not from
  a model's training data

**Partial credit criteria:**
- Identifies two failure scenarios but cannot connect them to BM25's structural advantage
- Describes the structural advantage correctly but only gives one concrete failure scenario

**Incorrect / no-credit criteria:**
- Cannot identify any scenario where dense retrieval fails
- Attributes dense failure to embedding dimension size rather than training data coverage
- Claims BM25 requires a neural model

---

## Q3 — Hybrid search and RRF fusion

**Difficulty:** intermediate

**Question:**
Describe hybrid search. What is Reciprocal Rank Fusion (RRF), and why is it preferred
over weighted score combination for fusing sparse and dense retrieval results?

**Correct answer criteria:**
- Hybrid search combines sparse retrieval (BM25) and dense retrieval results for the same
  query, merging them into a single ranked list
- RRF: given two ranked lists (one from BM25, one from dense retrieval), RRF assigns each
  document a score of 1/(k + rank) for each list where k is a constant (typically 60),
  then sums the scores across lists. The constant k prevents documents at the very top
  of one list from dominating overwhelmingly
- Why RRF over weighted scores: BM25 scores and cosine similarity scores are on
  completely different numerical scales — BM25 may produce scores of 12.7 while cosine
  produces 0.83. A weighted sum of incompatible scales is arbitrary and fragile;
  RRF sidesteps the scale problem entirely by operating on ranks, not raw scores

**Partial credit criteria:**
- Correctly describes hybrid search and RRF mechanics but cannot explain why score
  fusion (weighted sum) is problematic
- Identifies the score scale incompatibility problem but cannot describe the RRF formula
  or mechanism

**Incorrect / no-credit criteria:**
- Describes hybrid search as simply running two queries and concatenating results without
  any fusion step
- Claims RRF and weighted score fusion produce identical results
- Cannot explain what "Reciprocal" refers to in the formula

---

## Q4 — Cross-encoder reranking

**Difficulty:** intermediate

**Question:**
Explain the difference between a bi-encoder (used in first-stage dense retrieval) and
a cross-encoder (used in reranking). What does a reranker do that first-stage retrieval
cannot, and what is the cost it adds to the pipeline?

**Correct answer criteria:**
- Bi-encoder: encodes query and document separately into independent vectors; similarity
  is measured post-hoc by comparing vectors. This allows pre-computation of document
  embeddings (fast retrieval) but the encoding of query and document do not influence
  each other — the model has no joint attention over both texts
- Cross-encoder: takes (query, document) as a single input, allowing the model to attend
  over both texts simultaneously. This produces a joint relevance score that captures
  fine-grained query-document interactions that bi-encoders miss
- What reranking adds: it re-scores the top-K bi-encoder results with a cross-encoder,
  often dramatically improving the ordering of results. Small changes (e.g., moving the
  most relevant document from position 3 to position 1) have significant downstream impact
  on generation quality
- The cost: cross-encoders are expensive per inference because they score each (query, doc)
  pair independently — scoring 100 documents requires 100 forward passes. This limits
  reranking to a small candidate set (typically the top 20–100 from first-stage retrieval)

**Partial credit criteria:**
- Correctly describes what a cross-encoder does but conflates it with a bi-encoder
- Identifies the cost (latency) but cannot explain the quality benefit

**Incorrect / no-credit criteria:**
- Describes reranking as "running the retrieval step twice"
- Claims bi-encoders and cross-encoders use the same inference pattern
- Cannot identify the latency cost of cross-encoder reranking

---

## Q5 — MMR for diversity

**Difficulty:** intermediate

**Question:**
Explain Maximal Marginal Relevance (MMR). What problem does it address that relevance-only
retrieval does not, and describe a concrete use case where MMR would improve generation
quality over top-K retrieval.

**Correct answer criteria:**
- MMR balances relevance to the query with diversity among retrieved results. It iteratively
  selects the next document that maximizes (lambda × relevance_to_query − (1−lambda) ×
  max_similarity_to_already_selected_documents)
- Problem it addresses: top-K retrieval by relevance alone often returns near-duplicate
  chunks — the 5 most relevant chunks may all say essentially the same thing, wasting
  context window tokens and giving the LLM redundant information
- Lambda controls the relevance-diversity balance: lambda=1 is pure relevance (top-K);
  lambda=0 is pure diversity
- Concrete use case: a user asks "What are the key risks of this product?" A top-K
  retrieval returns 5 chunks that all describe the same primary risk from different
  documents. MMR would instead return 5 chunks covering 5 different risk categories,
  giving the LLM (and thus the user) a more complete picture

**Partial credit criteria:**
- Correctly explains the diversity goal but cannot describe the MMR formula or iteration
  mechanism
- Correctly describes the formula but cannot give a concrete use case where it helps

**Incorrect / no-credit criteria:**
- Describes MMR as a reranking method (it is a diversity selection method — conceptually
  different from a reranker)
- Claims MMR is useful for precision tasks (it sacrifices some relevance for diversity —
  it is most useful for breadth tasks)
- Cannot identify the redundancy problem that MMR addresses

---

## Q6 — Multi-query expansion

**Difficulty:** intermediate

**Question:**
Describe multi-query retrieval. What problem does it solve, and what risk does it introduce
that single-query retrieval does not have?

**Correct answer criteria:**
- Multi-query retrieval: an LLM generates multiple alternative phrasings or sub-questions
  from the original user query (e.g., 3–5 variants), runs a separate retrieval for each,
  and merges the results (deduplicating) before passing them to generation
- Problem it solves: a single query embedding represents only one interpretation of the
  user's intent. If the user's phrasing is unusual, ambiguous, or uses vocabulary that
  misses the relevant documents, expanding to multiple queries increases the chance that
  at least one query hits the relevant chunks
- Particularly useful for complex, multi-part questions where different sub-questions
  retrieve different relevant passages
- Risk introduced: LLM-generated query variants may drift from the original intent —
  a hallucinated or misleading query variant can retrieve irrelevant context that
  contaminates the generation step. More queries also increase retrieval latency and
  cost proportionally

**Partial credit criteria:**
- Correctly describes the mechanism but cannot identify the hallucination/drift risk
- Identifies the risk but describes the mechanism imprecisely

**Incorrect / no-credit criteria:**
- Describes multi-query as "running the same query multiple times for consistency"
- Believes multi-query always improves results with no tradeoff
- Cannot explain what problem a single query representation fails to address

---

## Q7 — HyDE: Hypothetical Document Embeddings

**Difficulty:** advanced

**Question:**
Explain HyDE (Hypothetical Document Embeddings). What is the insight behind the
approach, when does it improve retrieval, and when does it make retrieval worse?

**Correct answer criteria:**
- HyDE: instead of embedding the user's question directly as the query vector, HyDE
  uses an LLM to generate a hypothetical answer to the question (a document that would
  answer the query, written as if it were real), then embeds the hypothetical answer
  as the query vector
- The insight: a hypothetical answer document lives in the same embedding space as
  real answer documents (both are answer-style text), whereas a question may live in
  a different region of the embedding space from its answers. Querying with an answer-
  shaped embedding retrieves answer-shaped documents more reliably
- When it improves retrieval: queries phrased as questions where the question and
  answer have very different vocabulary or structure (e.g., "What causes X?" returns
  documents written as "X is caused by..."); technical domains where questions are
  short but relevant documents are dense and detailed
- When it makes retrieval worse: if the LLM generates a hallucinated or confidently
  wrong hypothetical answer, the query embedding drifts toward the wrong region of the
  embedding space, retrieving documents that match the hallucination rather than the
  user's true intent

**Partial credit criteria:**
- Describes the mechanism correctly but only addresses when HyDE helps (not when it hurts)
- Correctly identifies the failure mode (hallucinated hypothetical) but cannot explain
  the core insight behind why answer-embeddings are closer to answer-documents

**Incorrect / no-credit criteria:**
- Describes HyDE as a prompt engineering technique (it is a query transformation technique
  operating on the embedding, not the prompt)
- Claims HyDE is always better than direct query embedding
- Cannot explain why embedding a hypothetical answer instead of the question helps

---

## Q8 — Choosing a retrieval strategy for a given use case

**Difficulty:** advanced

**Question:**
You are building a customer support RAG system over a product knowledge base. User
queries include: highly specific product model numbers ("How do I reset the XR-2000?"),
broad conceptual questions ("What are all the warranty options?"), and multi-part
questions ("Which models support feature X and what are the limitations for each?").
Design a retrieval strategy that addresses all three query types. Justify each design choice.

**Correct answer criteria:**
- For specific product model numbers: BM25 or hybrid retrieval with BM25 weighted
  heavily — exact model number matching requires sparse retrieval precision
- For broad conceptual questions: dense retrieval with MMR to surface diverse coverage
  of warranty options across multiple documents without returning near-duplicate chunks
- For multi-part questions: multi-query expansion — decompose the question into
  sub-questions ("Which models support feature X?" and "What are the limitations of
  feature X per model?"), run retrieval for each, merge results
- Overall recommendation: a hybrid retrieval system (BM25 + dense with RRF fusion) as
  the base, with an MMR pass for diversity-sensitive queries and optional multi-query
  expansion for complex queries. Reranking with a cross-encoder over the top 20 results
  would improve precision for all three types
- The learner should demonstrate that no single retrieval method handles all three types
  well, and justify each choice with the mechanism that addresses each query type's
  specific failure mode

**Partial credit criteria:**
- Correctly addresses two of three query types with appropriate strategies
- Recommends hybrid retrieval for all cases without tailoring the strategy to query type

**Incorrect / no-credit criteria:**
- Recommends only dense retrieval for all query types
- Cannot explain why a single retrieval method is insufficient for all three query types
- Does not address the multi-part query challenge
