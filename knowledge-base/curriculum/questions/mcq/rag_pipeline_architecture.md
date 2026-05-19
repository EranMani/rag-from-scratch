# MCQ Bank — rag_pipeline_architecture
# Topic: rag_pipeline_architecture
# Phase: 1 (Foundations)
# Questions: 5 (2 beginner, 2 intermediate, 1 advanced)
# Last updated: 2026-05-19 (Commit 33)

---

## MCQ-1 — RAG pipeline stages

**Difficulty:** beginner
**Topic:** rag_pipeline_architecture

**Question:**
What are the two main phases of a RAG pipeline?

**Options:**
A. Training and inference
B. Indexing and querying
C. Embedding and decoding
D. Retrieval and fine-tuning

**Correct answer:** B

**Explanation:**
A RAG pipeline has an indexing phase (documents are chunked, embedded, and stored in a vector database) and a querying phase (the user's question is embedded, similar chunks are retrieved, and the LLM generates an answer with retrieved context). Training (A) is not part of RAG — the LLM is used as-is. Fine-tuning (D) is an alternative approach to RAG, not a phase of it.

---

## MCQ-2 — Role of the vector database

**Difficulty:** beginner
**Topic:** rag_pipeline_architecture

**Question:**
What is the primary role of the vector database in a RAG pipeline?

**Options:**
A. To store the full text of documents and serve them to the LLM
B. To train the embedding model on domain-specific documents
C. To store document embeddings and enable fast similarity search at query time
D. To cache LLM responses and reduce inference cost

**Correct answer:** C

**Explanation:**
The vector database stores the embedding vectors produced during indexing and provides approximate nearest-neighbor search to find the most similar chunks to a query embedding. It does not store full text as its primary function (A) — the vector index is separate from the document store. It has no role in training the embedding model (B), and response caching (D) is a separate infrastructure concern.

---

## MCQ-3 — Why RAG reduces hallucination

**Difficulty:** intermediate
**Topic:** rag_pipeline_architecture

**Question:**
Why does grounding an LLM's response in retrieved chunks reduce hallucination, compared to relying solely on the LLM's parametric knowledge?

**Options:**
A. Retrieved chunks constrain the LLM to generate text that is statistically similar to the source documents
B. The LLM is prompted with specific source passages, giving it factual anchors that override its tendency to confabulate plausible-sounding content
C. The retrieval step filters out questions the LLM does not know the answer to, preventing it from attempting them
D. The vector similarity score acts as a confidence threshold — only high-confidence answers are returned to the user

**Correct answer:** B

**Explanation:**
RAG provides factual anchors in the prompt: the LLM is shown specific retrieved passages and instructed to base its answer on them. This does not prevent hallucination entirely, but it gives the model ground-truth text to reference rather than relying on learned associations from training. Option A describes statistical similarity, not factual grounding — LLMs are not constrained to statistically copy source text. Option C is incorrect: retrieval does not screen out questions; it retrieves the best available context regardless of the LLM's knowledge state. Option D conflates retrieval scores with answer confidence.

---

## MCQ-4 — Indexing pipeline ordering

**Difficulty:** intermediate
**Topic:** rag_pipeline_architecture

**Question:**
In the indexing phase of a RAG pipeline, what is the correct sequence of operations?

**Options:**
A. Embed documents → chunk documents → store in vector database
B. Chunk documents → embed chunks → store in vector database
C. Store documents in vector database → chunk → embed
D. Embed documents → store in vector database → chunk at query time

**Correct answer:** B

**Explanation:**
Chunking must happen before embedding because embedding models have a maximum token input length — full documents often exceed it. The correct sequence is: (1) split documents into chunks that fit the embedding model's context window, (2) embed each chunk into a vector, (3) store the vectors (and chunk text) in the vector database. Option A reverses chunking and embedding. Options C and D delay chunking incorrectly; you cannot embed a full document and then chunk it afterward while preserving chunk-level retrieval.

---

## MCQ-5 — Failure mode: context window overflow

**Difficulty:** advanced
**Topic:** rag_pipeline_architecture

**Question:**
A RAG pipeline retrieves the top-20 chunks for every query and concatenates them all into the LLM prompt. The system works correctly during development with a small test corpus but produces degraded responses in production with a large corpus. What is the most precise diagnosis?

**Options:**
A. The embedding model overfits to the development corpus and fails to generalize to production documents
B. The LLM's attention mechanism degrades for long contexts — retrieving 20 chunks likely exceeds the effective context window, causing the model to ignore or misweigh distant retrieved passages
C. The vector database similarity scores are less accurate for larger corpora because the index becomes statistically saturated
D. The development corpus did not include adversarial queries, so the retrieval step was not stress-tested

**Correct answer:** B

**Explanation:**
LLMs have a maximum context window, and even within that window, research shows attention quality degrades for content positioned far from the beginning or end of the context ("lost in the middle" effect). Concatenating 20 chunks can easily exceed practical attention span, causing the model to ignore or misattribute retrieved content. Option A describes an embedding generalization failure — plausible but not the primary failure mode when the corpus grows. Option C is incorrect: ANN index accuracy does not degrade with corpus size in the way described. Option D is a testing methodology concern, not the production failure cause.

