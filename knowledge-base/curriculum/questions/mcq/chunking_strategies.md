# MCQ Bank — chunking_strategies
# Topic: chunking_strategies
# Phase: 2 (Core Components)
# Questions: 5 (2 beginner, 2 intermediate, 1 advanced)
# Last updated: 2026-05-19 (Commit 33)

---

## MCQ-1 — Why chunking is necessary

**Difficulty:** beginner
**Topic:** chunking_strategies

**Question:**
Why must documents be split into chunks before embedding in a RAG pipeline?

**Options:**
A. To reduce storage costs in the vector database
B. Because embedding models have a maximum token input length that many documents exceed
C. To improve the quality of cosine similarity scores between documents
D. Because LLMs cannot process text that was embedded as a single unit

**Correct answer:** B

**Explanation:**
Embedding models have a fixed maximum context window (often 512 or 8192 tokens depending on the model). Documents that exceed this limit cannot be embedded in a single pass. Chunking splits documents into pieces that fit within this limit. Storage costs (A) are a secondary consideration. Embedding quality per chunk (C) is a chunking strategy concern, not the reason chunking is necessary. LLM processing (D) is about the generation step, not the embedding step.

---

## MCQ-2 — Chunk overlap purpose

**Difficulty:** beginner
**Topic:** chunking_strategies

**Question:**
What is the primary purpose of adding overlap between consecutive chunks?

**Options:**
A. To reduce the total number of chunks needed to cover a document
B. To ensure that sentences or ideas spanning a chunk boundary are represented in at least one retrievable chunk
C. To improve embedding model performance by providing more context per chunk
D. To prevent duplicate document detection from flagging overlapping chunks as copies

**Correct answer:** B

**Explanation:**
When a document is split at a fixed boundary, a sentence or concept that straddles two chunks may be incomplete in both. Overlap (repeating some text at the start of the next chunk) ensures that content near chunk boundaries appears fully in at least one chunk and can be retrieved. Option A is incorrect — overlap increases total chunk count. Option C is a secondary benefit, not the primary purpose. Option D describes a deduplication system concern that is unrelated to why overlap is used.

---

## MCQ-3 — Fixed-size vs. semantic chunking tradeoff

**Difficulty:** intermediate
**Topic:** chunking_strategies

**Question:**
A team is chunking a corpus of technical API documentation. They compare fixed-size chunking (500 tokens, 50-token overlap) against semantic chunking (split at paragraph and section boundaries). Which statement correctly describes the key tradeoff?

**Options:**
A. Fixed-size chunking produces higher retrieval precision because equal-length chunks produce more comparable embedding vectors
B. Semantic chunking preserves conceptual boundaries but produces variable-length chunks that may require more complex downstream handling; fixed-size chunking is predictable but may cut mid-sentence or mid-concept
C. Semantic chunking is always superior — fixed-size chunking is only used when no other option is available
D. Fixed-size chunking is superior for technical documentation because API docs have uniform structure

**Correct answer:** B

**Explanation:**
Semantic chunking (splitting at natural boundaries like paragraphs, sections, or sentences) preserves conceptual integrity — retrieved chunks are more likely to contain complete, coherent information. However, variable chunk lengths complicate downstream processing (e.g., fitting into LLM context windows, batching embeddings). Fixed-size chunking is simple and predictable but may cut mid-sentence, splitting a concept across two chunks. Neither is universally superior (eliminating C and D) — the right choice depends on document structure and downstream requirements.

---

## MCQ-4 — Chunk size effect on retrieval

**Difficulty:** intermediate
**Topic:** chunking_strategies

**Question:**
A RAG developer increases chunk size from 256 tokens to 1024 tokens. What is the most likely effect on retrieval quality?

**Options:**
A. Retrieval precision improves because larger chunks contain more context, making them more informative
B. Retrieval precision may decrease because a larger chunk contains multiple topics, diluting the embedding signal and matching queries that are only partially relevant
C. Retrieval recall decreases because fewer total chunks exist in the index
D. Embedding quality improves because the model receives more tokens and produces richer representations

**Correct answer:** B

**Explanation:**
A larger chunk covers more content, which can dilute the embedding — the resulting vector represents an average of multiple topics rather than a focused concept. This means the chunk may score high similarity to a broader range of queries, reducing precision (returning chunks that are only partially relevant). Option A is the intuitive but incorrect response — more context does not improve embedding focus. Option C is technically true (fewer chunks exist) but conflates chunk count with recall. Option D incorrectly assumes more tokens always improve embedding quality; beyond a model's effective attention range, additional tokens add noise.

---

## MCQ-5 — Hierarchical chunking strategy

**Difficulty:** advanced
**Topic:** chunking_strategies

**Question:**
A legal document corpus contains long contracts. Small chunks (128 tokens) produce poor retrieval because individual clauses lack context; large chunks (1024 tokens) dilute the embedding signal. A developer proposes a hierarchical chunking strategy. Which description correctly captures how hierarchical chunking addresses this tradeoff?

**Options:**
A. Documents are chunked at two levels: small chunks for embedding/retrieval and large parent chunks for LLM context — the system retrieves small chunks by similarity, then returns the parent chunk as the LLM's context
B. Each document is embedded at full length for retrieval, then split into small chunks for the LLM prompt
C. The document is split into overlapping small chunks and non-overlapping large chunks, and both sets are indexed; the system retrieves from whichever index returns higher similarity scores
D. Small chunks are clustered into groups by topic, and each cluster is re-embedded as a single synthetic chunk for the final index

**Correct answer:** A

**Explanation:**
Hierarchical (parent-document) chunking separates retrieval granularity from context granularity: small chunks produce focused, discriminative embeddings for high-precision retrieval, while the parent chunk (containing the clause and its surrounding sections) provides the LLM with the broader context it needs to answer accurately. Option B embeds at full document length, which defeats the purpose of chunking for discriminative retrieval. Option C maintains two separate indexes with independent retrieval — this is a different architecture (dual-index retrieval) that does not solve the parent context problem. Option D describes clustering-based re-embedding, which is a topic modeling approach rather than hierarchical chunking.

