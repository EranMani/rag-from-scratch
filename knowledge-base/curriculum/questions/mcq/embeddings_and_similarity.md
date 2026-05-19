# MCQ Bank — embeddings_and_similarity
# Topic: embeddings_and_similarity
# Phase: 1 (Foundations)
# Questions: 5 (2 beginner, 2 intermediate, 1 advanced)
# Last updated: 2026-05-19 (Commit 33)

---

## MCQ-1 — What an embedding represents

**Difficulty:** beginner
**Topic:** embeddings_and_similarity

**Question:**
What does a text embedding represent?

**Options:**
A. A compressed version of the original text that can be decompressed later
B. A fixed-length vector of numbers that encodes the semantic meaning of the text
C. A keyword index mapping each word to its position in the document
D. A hash of the text used to detect duplicate documents

**Correct answer:** B

**Explanation:**
An embedding is a dense vector of floating-point numbers in a high-dimensional space where texts with similar meanings are geometrically close. It encodes semantic meaning, not surface form — unlike A (which implies lossless reconstruction), C (which describes a positional index), or D (which describes a hash for deduplication rather than meaning representation).

---

## MCQ-2 — Cosine similarity meaning

**Difficulty:** beginner
**Topic:** embeddings_and_similarity

**Question:**
Two text embeddings have a cosine similarity of 0.95. What does this indicate?

**Options:**
A. The two texts are nearly identical in length
B. The two texts share approximately 95% of the same words
C. The two texts are semantically very similar
D. One text is a paraphrase of the other with 5% new content

**Correct answer:** C

**Explanation:**
Cosine similarity measures the angle between two vectors in embedding space — a score near 1.0 indicates the vectors point in nearly the same direction, meaning the texts are semantically very similar. It says nothing about word overlap (B), text length (A), or percentage of new content (D). Semantically equivalent sentences that use entirely different words can still have high cosine similarity.

---

## MCQ-3 — Dot product vs. cosine similarity

**Difficulty:** intermediate
**Topic:** embeddings_and_similarity

**Question:**
When are dot product similarity and cosine similarity equivalent for comparing embeddings?

**Options:**
A. Always — dot product and cosine similarity produce the same ranking for any vectors
B. When both vectors have zero mean (are centered around the origin)
C. When both vectors are unit-normalized (have magnitude 1.0)
D. When the embedding model uses ReLU activations in its final layer

**Correct answer:** C

**Explanation:**
Cosine similarity normalizes by the product of the two magnitudes: `cos(a, b) = dot(a, b) / (|a| × |b|)`. When both vectors are already unit-normalized (|a| = |b| = 1), the denominator is 1 and the dot product equals the cosine similarity. This matters in practice because many vector databases index dot product similarity, and unit-normalized embeddings must be stored for the results to match cosine ranking. Zero-mean centering (B) does not cause equivalence.

---

## MCQ-4 — Embedding space and retrieval failure

**Difficulty:** intermediate
**Topic:** embeddings_and_similarity

**Question:**
A RAG system retrieves the wrong document for the query "how do I reset my password?" — it returns a document about network firewall configuration. Which is the most likely cause?

**Options:**
A. The embedding model was not trained on text containing the word "password"
B. The query embedding and document embedding are in different vector spaces because different embedding models were used at index time and query time
C. The cosine similarity threshold was set too high, filtering out the correct document
D. The vector database index became corrupted during ingestion

**Correct answer:** B

**Explanation:**
Embeddings are only comparable when produced by the same model — two different models map text into different vector spaces, and similarity scores across spaces are meaningless. Using model A at index time and model B at query time is a common production failure mode. Option A is incorrect because embedding models encode semantic patterns, not specific vocabulary. Option C would cause no results, not wrong results. Option D is possible but far less likely than a model mismatch for this symptom pattern.

---

## MCQ-5 — Semantic vs. lexical gap

**Difficulty:** advanced
**Topic:** embeddings_and_similarity

**Question:**
A knowledge base contains a document stating "the cardiovascular pump circulates blood." A user queries "how does the heart work?" The document is not retrieved. Assuming the embedding model is high quality, which explanation is most architecturally precise?

**Options:**
A. The embedding model cannot handle medical terminology and should be fine-tuned on a medical corpus
B. The query and document occupy distant regions of the embedding space because the model was not exposed to the specific paraphrase mapping "cardiovascular pump" to "heart" during training
C. Dense retrieval inherently cannot bridge terminology gaps between formal and colloquial language; a hybrid retrieval system adding BM25 would resolve this
D. The chunking strategy split the document at a sentence boundary, discarding the semantic context needed for retrieval

**Correct answer:** C

**Explanation:**
This is the classic semantic-lexical gap problem. Dense embeddings capture distributional similarity, but when one text uses formal clinical language ("cardiovascular pump") and another uses colloquial language ("heart"), even a strong general-purpose embedding model may not bridge the gap. Hybrid retrieval (dense + BM25) is the architectural solution: BM25 would match "heart" if it appears anywhere in the document, while dense retrieval covers paraphrase cases. Option A assumes fine-tuning is required — but the issue is not vocabulary unfamiliarity, it is term-level distance in the embedding space. Option B is partially correct but does not name the architectural remedy.

