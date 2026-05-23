# MCQ Bank — embeddings_and_similarity
# Topic: embeddings_and_similarity
# Phase: 1 (Foundations)
# Questions: 15 (5 novice, 5 intermediate, 3 advanced, 2 expert)
# Last updated: 2026-05-23 (Commit 51)

---

## MCQ-1 — What an embedding represents

**Difficulty:** novice
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

**Why A is wrong:** An embedding is a lossy, fixed-length projection — the original text cannot be reconstructed from it. Developers coming from compression backgrounds (zip, base64) sometimes expect embeddings to be reversible. They are not; they are a transformation into a semantic space, not a compressed copy.

**Why C is wrong:** A keyword/positional index (like those used in BM25 or inverted indexes) is a fundamentally different data structure: it maps terms to document positions. Embeddings are dense floating-point vectors with no per-token positional accounting. Confusing the two leads to incorrect assumptions about what retrieval failure modes look like.

**Why D is wrong:** Hashes are deterministic, fixed-length outputs designed for collision resistance and equality checks, not semantic comparison. Similar texts produce wildly different hashes. Embeddings of similar texts produce geometrically close vectors. The two serve completely different purposes.

---

## MCQ-2 — Cosine similarity meaning

**Difficulty:** novice
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

**Why A is wrong:** Cosine similarity is magnitude-invariant — it measures direction only. A ten-word text and a thousand-word text can have cosine similarity of 1.0 if they embed to the same direction. Length is not encoded in the similarity score. Developers who are unfamiliar with vector geometry sometimes assume similarity must correlate with structural properties like length.

**Why B is wrong:** Word overlap is what lexical metrics (like Jaccard similarity or BM25) measure. Cosine similarity operates on the resulting embedding vector, not on the raw tokens. Two texts with no shared words can have high cosine similarity if they convey the same meaning. Confusing semantic similarity with lexical overlap is one of the most common foundational errors.

**Why D is wrong:** Cosine similarity is not a percentage-of-new-content metric. A score of 0.95 does not mean 5% of the content is different — it means the embeddings are geometrically close. The relationship between score magnitude and semantic difference is non-linear and model-dependent.

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

**Why A is wrong:** Dot product and cosine similarity are only equivalent when vectors are unit-normalized. For unnormalized vectors, longer vectors have higher dot products regardless of direction — a very long vector can dominate dot product rankings even if it is not semantically the closest. This causes retrieval ranking to favor long documents over genuinely relevant short passages.

**Why B is wrong:** Zero-mean centering (subtracting the mean of the vector space) is an isotropy correction technique, not a normalization step. Centering does not fix magnitude differences — two centered vectors can still have different magnitudes, so dot product and cosine will diverge. Engineers who apply centering to improve embedding isotropy sometimes incorrectly assume it implies normalization.

**Why D is wrong:** The activation function in the model's final layer affects the distribution of values in each vector, but it does not ensure unit magnitude. ReLU outputs can vary widely in norm depending on the input. Model architecture choices do not replace explicit L2 normalization when using a dot-product index.

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

**Why A is wrong:** Embedding models learn distributional representations from large corpora and generalize across vocabulary. A model trained without the word "password" will still embed "reset my password" into the same semantic region as "account recovery" because the surrounding context conveys the meaning. Vocabulary gaps are a concern for sparse retrieval methods (BM25), not for dense embeddings.

**Why C is wrong:** A threshold set too high would return zero results or too few results — not wrong results. Returning a document about firewall configuration indicates the similarity scores are positive and the retriever found a best match, just the wrong one. Threshold tuning affects coverage, not correctness of matches.

**Why D is wrong:** Index corruption is possible but exceedingly rare and would typically manifest as errors, missing results, or random garbage returns — not as systematic wrong retrievals. Systematic wrong retrievals point to a model mismatch, embedding space incompatibility, or domain mismatch in training data. Blaming corruption without evidence is premature.

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

**Why A is wrong:** Fine-tuning changes how the model represents tokens in the embedding space. But the failure here is not that the model lacks the term — both "heart" and "cardiovascular pump" are common English terms that any general embedding model knows. The model simply may not have learned that they are near-synonyms in clinical context. Fine-tuning on a medical corpus would help, but the correct architectural answer is hybrid retrieval, which is faster to deploy, more maintainable, and does not require labeled training data.

**Why B is wrong:** Option B correctly describes the mechanism (the terms are distant in the embedding space) but stops there. It does not identify the architectural remedy, which is what the question asks for. Identifying the cause without prescribing the fix is an incomplete diagnostic — and in production, an incomplete diagnosis leads to prolonged outages.

---

## MCQ-6 — Embedding model drift without re-indexing

**Difficulty:** advanced
**Topic:** embeddings_and_similarity

**Question:**
A team upgrades their embedding model from `text-embedding-ada-002` to `text-embedding-3-large` to improve retrieval quality. They update the query embedding call but forget to re-embed the document corpus. What is the observable production symptom and the precise mechanism behind it?

**Options:**
A. The system throws a dimension mismatch error at query time because the two models produce vectors of different lengths
B. Retrieval accuracy silently degrades — queries are embedded in model B's vector space while documents remain in model A's vector space; cosine similarity scores become meaningless across the two spaces, causing the system to return apparently random results with high confidence scores
C. The vector database rejects the new query vectors because they fail the checksum validation used to verify index integrity
D. Retrieval recall drops to zero because the new model uses a different tokenizer that produces out-of-vocabulary tokens for all stored documents

**Correct answer:** B

**Explanation:**
Each embedding model defines its own high-dimensional vector space with its own geometry. When you embed a query with model B, you get a vector that means something in model B's space. The stored document vectors were computed by model A and mean something in model A's space. Cosine similarity between the two is nonsense — it measures the angle between a point in one coordinate system and a point in a different coordinate system. The failure is silent: the system does not error, returns results with high scores, and appears to work. This is one of the most dangerous failure modes because it passes integration tests that only check for response shape, not semantic correctness. The fix is always to re-index when changing embedding models.

**Why A is wrong:** Dimension mismatch would produce an explicit error, which would be caught immediately. Real production failures are silent, not noisy. `text-embedding-ada-002` outputs 1536 dimensions and `text-embedding-3-large` outputs 3072 dimensions by default — so this error is possible, but it is a loud failure that gets caught at deployment, not a silent degradation. The question describes the more dangerous silent variant.

**Why C is wrong:** Vector databases do not perform checksum validation on stored vectors. They are numerical arrays — there is no integrity check that distinguishes a valid model-A vector from a valid model-B vector. The database stores and retrieves both identically. This is precisely why the failure is silent.

**Why D is wrong:** Tokenization happens at embedding time to produce the vector; the tokens themselves are not stored in the vector database. Once a document is embedded, it is stored as a float array. A different tokenizer at query time affects how the query text is converted to a vector, but stored document vectors are unaffected because they were already computed and stored. Recall does not drop to zero — it degrades silently.

---

## MCQ-7 — Fine-tuned embedding and domain overfitting

**Difficulty:** advanced
**Topic:** embeddings_and_similarity

**Question:**
A team fine-tunes a general-purpose embedding model on their internal support ticket corpus to improve retrieval for customer support queries. After deployment, RAGAS recall@5 improves on support queries but drops significantly on queries about product documentation, which was also in the corpus. What is the most likely cause?

**Options:**
A. The fine-tuned model's embedding dimension is smaller than the original, reducing its capacity to represent product documentation semantics
B. Fine-tuning on support ticket pairs biased the model toward support-language patterns; the resulting embedding space compresses regions relevant to documentation style, making documentation chunks harder to distinguish from each other at query time
C. The vector database needs to be re-indexed after fine-tuning because the stored vectors are stale — re-indexing will restore documentation recall
D. Fine-tuning causes catastrophic forgetting of the base model's vocabulary, making product terminology out-of-vocabulary

**Correct answer:** B

**Explanation:**
Fine-tuning on domain-specific data adjusts the model's embedding space to prioritize the patterns in that data. If the fine-tuning corpus is predominantly support tickets, the model learns to geometrically separate support-language concepts while compressing other regions of the space. Documentation-style text, which uses different sentence structures and terminology, may collapse into a smaller region of the fine-tuned space — documentation chunks that were previously distinguishable become neighbors of each other, making precision difficult. This is domain overfitting: the model trades general retrieval quality for specialized performance on the fine-tuning distribution.

**Why A is wrong:** Fine-tuning does not change the model's output dimension — that is determined by the model architecture and is fixed. A fine-tuned version of `text-embedding-3-large` still outputs 3072-dimensional vectors. Dimension reduction would require a different architectural choice (e.g., MRL or PCA compression).

**Why C is wrong:** Re-indexing (re-embedding documents with the fine-tuned model) is required when the model changes — but the question asks why recall dropped on documentation after re-indexing was presumably done. If re-indexing had not been done, the failure mode would be cross-space incoherence (wrong results everywhere), not selective degradation on one content type. Re-indexing is necessary but not sufficient when the model has overfitted.

**Why D is wrong:** Fine-tuning on a contrastive objective adjusts the representation space geometry, not the vocabulary. The underlying tokenizer and vocabulary are unchanged. Catastrophic forgetting of vocabulary does not occur in embedding fine-tuning — it is a concern for generative model fine-tuning where the output distribution can shift dramatically.

---

## MCQ-8 — Cosine similarity score inflation past threshold

**Difficulty:** advanced
**Topic:** embeddings_and_similarity

**Question:**
A developer adds a similarity threshold filter: only retrieve chunks with cosine similarity >= 0.75. In early testing this eliminates irrelevant results. After six months with a 500,000-document corpus, users report that queries return confidently-scored results that are semantically unrelated to the query. Cosine scores are consistently in the 0.75–0.82 range. What is the most precise diagnosis?

**Options:**
A. The HNSW index degrades over time and returns approximate neighbors with inflated similarity scores
B. In high-dimensional embedding spaces, cosine similarity scores concentrate near a narrow range as corpus size grows — many unrelated documents end up with similar scores to any query because the curse of dimensionality causes pairwise distances to converge. The fixed threshold no longer discriminates signal from noise
C. The embedding model has drifted because the documents added over six months shifted the centroid of the embedding space, making the threshold calibration stale
D. The similarity threshold filter has an off-by-one bug that accepts scores >= 0.74 instead of >= 0.75, allowing near-threshold irrelevant results through

**Correct answer:** B

**Explanation:**
In high-dimensional spaces (typical embedding dimensions are 768–3072), the "curse of dimensionality" causes pairwise cosine distances between random vectors to concentrate around a mean value. As the corpus grows from 10,000 to 500,000 documents, the density of the high-dimensional space increases, and more unrelated documents fall within any fixed similarity band. A threshold of 0.75 that was discriminative at small scale becomes uninformative at large scale because the distribution of scores shifts — the bulk of the corpus, including unrelated documents, starts scoring in the 0.73–0.82 range. The fix is relative thresholding (e.g., return top-k with a minimum margin over the k+1 score) rather than absolute thresholding, or recalibrate the threshold against the full-scale corpus distribution.

**Why A is wrong:** HNSW approximate recall degradation manifests as failing to return the true nearest neighbors — missed results, not inflated scores for wrong results. The scenario describes consistent high scores for unrelated documents, which is a distributional problem, not an index accuracy problem.

**Why C is wrong:** Embedding models do not drift — the weights are frozen after training. The centroid of the embedded corpus shifts as new documents are added, but this affects the overall density of the vector space, not the model's output for any given input. This is precisely the curse-of-dimensionality effect described in B, but the mechanism is corpus density, not model drift.

**Why D is wrong:** An off-by-one on the threshold comparison would create a small, consistent boundary leak, not a systematic shift across the entire score distribution. The symptom is scores in the 0.75–0.82 range being returned for unrelated content — this is a distributional issue affecting many documents, not a boundary condition affecting a few.

---

## MCQ-9 — Cross-encoder vs. bi-encoder operational tradeoff

**Difficulty:** expert
**Topic:** embeddings_and_similarity

**Question:**
A RAG system uses a bi-encoder to retrieve top-100 candidates and a cross-encoder to rerank to top-5. Query latency is 180ms. A product request requires reducing latency to under 80ms while maintaining answer quality. Which change is most operationally sound?

**Options:**
A. Replace the bi-encoder with a cross-encoder for all 100 candidates — cross-encoders produce better similarity scores, so fewer candidates are needed
B. Reduce the bi-encoder candidate pool from 100 to 10 and eliminate the cross-encoder reranker — the bi-encoder score is sufficient for final ranking when the pool is small enough
C. Keep the bi-encoder retrieval step and eliminate the cross-encoder; compensate by improving bi-encoder recall through a larger candidate pool (200) and tighter chunk quality
D. Replace the cross-encoder with a lighter reranker (e.g., a smaller cross-encoder variant or a learned sparse reranker) that operates on the top-100 but at lower inference cost — maintain the two-stage architecture

**Correct answer:** D

**Explanation:**
The two-stage retrieval architecture (bi-encoder for recall, cross-encoder for precision) exists because bi-encoders are fast but less precise (they independently encode query and document) while cross-encoders are precise but slow (they jointly encode query-document pairs and cannot be precomputed). The latency bottleneck is the cross-encoder running over 100 candidates at query time. The operationally sound fix is to replace the cross-encoder with a lighter reranker — not to remove the reranking stage entirely. Option B eliminates reranking and accepts lower precision. Option C increases bi-encoder pool size (raising retrieval latency) while removing the precision stage — the opposite direction. Option A replaces a fast precomputed step (bi-encoder) with the slow step (cross-encoder) at full scale, which would make latency far worse than 180ms.

**Why A is wrong:** Running a cross-encoder over 100 candidates is the current bottleneck. Replacing the fast bi-encoder with a cross-encoder for the initial retrieval stage would require running a joint query-document forward pass for every document in the index — which is exactly what makes cross-encoders impractical as primary retrievers. This change would increase latency by orders of magnitude.

**Why B is wrong:** Reducing the candidate pool from 100 to 10 and removing reranking accepts the bi-encoder's lower precision as final. For many queries, the true best answer is in positions 6–20 of the bi-encoder ranking — a pool of 10 with no reranking means those results are permanently missed. This trades quality for latency in a way that will surface in evaluation metrics.

**Why C is wrong:** Increasing the bi-encoder pool from 100 to 200 increases bi-encoder retrieval time (more ANN comparisons) and more importantly increases the number of chunks returned to the LLM if no reranking is done. Chunk quality improvement is an indexing-time concern that does not address query-time latency. This option moves in the wrong direction on both dimensions.

---

## MCQ-10 — Batch vs. single-query embedding inconsistency

**Difficulty:** expert
**Topic:** embeddings_and_similarity

**Question:**
A team notices that the same document, when embedded via batch API call (alongside 511 other documents), produces a slightly different vector than when embedded in a single-call request. The L2 distance between the two vectors is small (0.003) but non-zero. Six months after launch, RAGAS context_recall drops from 0.91 to 0.82 with no code changes or corpus updates. The only operational event was a migration that re-indexed documents using single-call embedding for each chunk instead of the original batch embedding. What is the most precise diagnosis and the correct operational response?

**Options:**
A. This is expected floating-point non-determinism and is operationally irrelevant — an L2 distance of 0.003 is below any meaningful similarity threshold and cannot affect retrieval ranking at scale
B. Batch embedding and single-query embedding in some embedding APIs apply different internal padding and normalization passes depending on input count and sequence length distribution. The re-indexed vectors are in a subtly shifted position relative to the original query-time vectors (which were generated via single calls). If query embeddings were not re-generated using the same call mode as the re-indexed documents, the query and document vector spaces are now misaligned. Recall drops because the angular relationships that retrieval depends on have shifted. The fix is to ensure query embedding and document embedding always use identical call modes, and to re-generate query benchmarks after any re-indexing
C. The recall drop is caused by the re-indexing operation replacing HNSW graph structure, which requires a 48-hour warm-up period before the graph connectivity stabilizes to full recall quality
D. Single-call embedding is always higher quality than batch embedding — the recall drop happened because the migration exposed pre-existing poor-quality batch embeddings. The correct response is to leave the single-call embeddings in place and wait for recall to recover as the HNSW graph self-optimizes

**Correct answer:** B

**Explanation:**
Several embedding APIs — including some versions of OpenAI's embedding endpoint — exhibit input-count-dependent behavior: when a batch of sequences is processed together, the internal padding to the maximum sequence length in the batch, combined with layer normalization passes that are sensitive to the batch distribution, can produce vectors that differ slightly from vectors produced by embedding the same text in isolation. These differences are small per-vector but systematic — they shift the entire re-indexed document space relative to the original. If query embeddings continue to be generated via single calls (matching the original mode), the query vector space and the re-indexed document vector space are now misaligned by the batch-mode offset. The recall drop is not random noise — it is a consistent angular shift that makes previously near neighbors slightly farther away. The fix is call-mode consistency: queries and documents must always be embedded using the same API call pattern and model version. After re-indexing, the evaluation benchmark queries should also be re-embedded in the new mode to validate alignment before declaring the migration complete.

**Why A is wrong:** An L2 distance of 0.003 sounds negligible in isolation, but its impact depends on the geometry of the embedding space near the retrieval boundary. In high-dimensional spaces, small systematic shifts can move borderline-relevant documents from just inside the top-k retrieval radius to just outside it — consistently, across thousands of queries. The 0.09 recall drop (from 0.91 to 0.82) is not noise; it is a consistent degradation that cannot result from truly random floating-point error, which would be symmetric and average out. A practitioner who dismisses systematic vector offset as "below threshold" without checking for call-mode inconsistency is missing the mechanism.

**Why C is wrong:** HNSW indexes do not have a warm-up period during which recall gradually improves after a build. The graph is fully constructed and queryable immediately after the build completes. Recall quality at time-of-completion is the recall quality the index will have until the next incremental insert degrades it. There is no self-healing or stabilization process. This option invents a non-existent HNSW operational characteristic and would cause a team to wait 48 hours before investigating the real cause.

**Why D is wrong:** Neither batch nor single-call embedding is universally higher quality — the two modes produce consistent but slightly different vectors for API-specific reasons that are implementation details, not quality hierarchies. The premise that single-call embeddings are "better" is not established; they are just different. More critically, the claim that the HNSW graph will "self-optimize" over time is false — HNSW graphs do not self-modify after construction. The recall drop will persist indefinitely until the call-mode mismatch is resolved.

---

## MCQ-11 — What an embedding model outputs

**Difficulty:** novice
**Topic:** embeddings_and_similarity

**Question:**
You call an embedding API and pass in the sentence "The patient has a fever." What does the API return?

**Options:**
A. A summary of the sentence in fewer words
B. A list of keywords extracted from the sentence
C. A fixed-length array of floating-point numbers
D. A probability score indicating how common the sentence is in English

**Correct answer:** C

**Explanation:**
An embedding API converts input text into a dense vector — a fixed-length array of floating-point numbers. The length is determined by the model (e.g., 768 or 1536 dimensions). The numbers encode the text's semantic position in a high-dimensional space. They are not human-readable and do not map to words, summaries, or frequency statistics.

**Why A is wrong:** Summarization produces shorter text, not a numerical representation. An embedding does not reduce the text to fewer words — it transforms the text into a completely different format (a vector) that is not readable as natural language. Developers who conflate embeddings with summarization will not understand why embedding similarity search works.

**Why B is wrong:** Keyword extraction produces a list of tokens or phrases from the original text. Embeddings produce a dense numerical vector that encodes meaning holistically — individual tokens are not separately extractable from the output. This confusion often comes from familiarity with earlier NLP tools like TF-IDF that do produce keyword representations.

**Why D is wrong:** A probability score of sentence frequency would be a scalar, not a vector, and would measure corpus frequency rather than meaning. Embeddings are not statistics about how common text is — they represent semantic position in a learned space where meaning similarity corresponds to geometric closeness.

---

## MCQ-12 — Comparing two embeddings from different models

**Difficulty:** novice
**Topic:** embeddings_and_similarity

**Question:**
Document A was embedded using Model X. Document B was embedded using Model Y (a different model). A developer computes cosine similarity between Document A's vector and Document B's vector and gets 0.82. What does this score mean?

**Options:**
A. The two documents are 82% semantically similar
B. The score is meaningless — vectors from different embedding models are in different coordinate spaces and cannot be compared
C. The score is slightly less accurate than comparing vectors from the same model, but still useful
D. A score of 0.82 indicates that Model X and Model Y learned similar representations for this document pair

**Correct answer:** B

**Explanation:**
Each embedding model learns its own high-dimensional vector space during training. The axes (dimensions) in Model X's space represent different learned patterns than the axes in Model Y's space. Cosine similarity measures the angle between vectors in the same space; applied across spaces, the resulting number has no geometric meaning. A score of 0.82 across models tells you nothing about document similarity. Both documents must be embedded with the same model to produce comparable vectors.

**Why A is wrong:** The 0.82 score cannot be interpreted as a similarity percentage when vectors are from different models. Cosine similarity is only interpretable when both vectors inhabit the same learned coordinate system. A developer who treats cross-model similarity as meaningful will make incorrect retrieval decisions — and this failure is silent, because the number looks plausible.

**Why C is wrong:** Cross-model comparison is not "slightly less accurate" — it is architecturally invalid. There is no graceful degradation: the geometry of two separate vector spaces bears no relationship to each other. A vector's position in Model X's space says nothing about where a similar concept sits in Model Y's space. This option understates a hard constraint as a soft tradeoff.

**Why D is wrong:** Cosine similarity between two vectors does not measure whether the models that produced them learned similar representations. Evaluating whether two models agree requires comparing them on the same input with a calibrated method, not measuring cross-model vector similarity. The models' representations may be completely orthogonal while still producing a numerically high cosine score by chance.

---

## MCQ-13 — The purpose of vector space geometry

**Difficulty:** novice
**Topic:** embeddings_and_similarity

**Question:**
In a text embedding space, the embedding for "cat" is closer to "kitten" than to "automobile." What property of the embedding space produces this relationship?

**Options:**
A. The embedding model looked up "cat" and "kitten" in a synonym dictionary during training
B. "Cat" and "kitten" share more letters than "cat" and "automobile"
C. The model learned that "cat" and "kitten" appear in similar contexts across training data, placing their representations close together in the vector space
D. Shorter words are always embedded closer together than shorter words are to longer words

**Correct answer:** C

**Explanation:**
Embedding models are trained on large text corpora using distributional learning — the insight that words appearing in similar contexts (surrounded by similar words and sentences) develop similar vector representations. "Cat" and "kitten" both appear in contexts about pets, fur, meowing, and veterinary care. "Automobile" appears in contexts about roads, engines, and driving. The context similarity pushes "cat" and "kitten" together in the embedding space and apart from "automobile."

**Why A is wrong:** Embedding models do not use external dictionaries. They learn relationships from statistical patterns in text. Two words could be synonyms but appear in very different contexts — in that case, their embeddings may not be close. The geometry is learned from usage, not from lexical definitions.

**Why B is wrong:** Character overlap has no role in how embedding vectors are positioned. "Cat" and "catch" share more letters than "cat" and "kitten," but "kitten" is semantically closer. Embeddings encode meaning, not surface-level orthographic similarity. A developer who conflates spelling similarity with semantic similarity will misunderstand retrieval failures.

**Why D is wrong:** Word length has no systematic effect on embedding distance. Long and short words can be very close in embedding space if they appear in similar contexts (e.g., "use" and "utilize"). Embedding geometry is determined by meaning patterns, not by word length properties.

---

## MCQ-14 — High cosine similarity score interpretation

**Difficulty:** intermediate
**Topic:** embeddings_and_similarity

**Question:**
A RAG system returns a document with cosine similarity 0.91 to the query. The LLM's generated answer is still wrong. Which explanation is most architecturally precise?

**Options:**
A. A cosine similarity of 0.91 guarantees the retrieved document is the most relevant — the failure must be in the LLM generation stage
B. Cosine similarity measures angular proximity in the embedding space, which is a proxy for semantic similarity. A high score means the document and query are geometrically close, but "geometrically close" does not guarantee the document contains the specific answer the query needs — the document may discuss the same general topic without addressing the precise question
C. The cosine similarity computation contains floating-point rounding that degrades accuracy above 0.90, so 0.91 scores should be treated as unreliable
D. A 0.91 score indicates the document was retrieved from a stale index — fresh re-indexing would return a different top result

**Correct answer:** B

**Explanation:**
Cosine similarity measures directional proximity in an embedding space. Two texts can be geometrically close — discussing the same topic, using the same vocabulary — without one containing a specific answer to the other. A question about "how to reset a router password" and a document about "router security best practices" may embed near each other (both are about routers and security), but the document may never address the password reset procedure. High cosine similarity is a necessary but not sufficient condition for answering a query.

**Why A is wrong:** Cosine similarity being high does not guarantee the document contains the answer. The score reflects topical proximity in embedding space, not content completeness. This option conflates "the retriever did its job well" with "the retrieved document answers the question" — two distinct conditions. A high retrieval score followed by a wrong answer can indicate a retrieval granularity mismatch or a coverage gap in the corpus.

**Why C is wrong:** Floating-point rounding in cosine similarity does not degrade accuracy above any threshold. The calculation is numerically stable for values in [0, 1]. There is no known threshold above which cosine similarity scores become unreliable due to floating-point precision. This option invents a non-existent technical limitation.

**Why D is wrong:** Index staleness would cause the retriever to miss recently added documents or return outdated ones, but it does not manifest as a high similarity score for the wrong document. A 0.91 score for a returned document means that document is genuinely close to the query in the current index's embedding space — freshness does not change the geometric relationship between query and document vectors.

---

## MCQ-15 — Magnitude and cosine similarity

**Difficulty:** intermediate
**Topic:** embeddings_and_similarity

**Question:**
An embedding model produces vectors where longer input texts tend to have higher L2 norms (larger magnitudes). A developer uses dot product (not cosine similarity) as the similarity metric in the vector database. What retrieval bias will this introduce?

**Options:**
A. No bias — dot product and cosine similarity always produce the same ranking for any set of vectors
B. Long document chunks will score higher than short chunks for any query, even when the short chunks are more semantically relevant, because the dot product is sensitive to vector magnitude
C. Short document chunks will score higher because the model normalizes output magnitude inversely to input length
D. The bias will only appear when querying with very long queries; short queries are unaffected

**Correct answer:** B

**Explanation:**
Dot product equals the product of the two vectors' magnitudes times the cosine of the angle between them: `dot(a, b) = |a| × |b| × cos(θ)`. When document vectors have varying magnitudes (larger for longer texts), the magnitude term inflates the dot product for longer documents regardless of their directional alignment with the query. A long, tangentially relevant chunk may out-score a short, precisely relevant chunk simply because its magnitude is larger. Cosine similarity removes this bias by normalizing by both magnitudes.

**Why A is wrong:** Dot product and cosine similarity are only equivalent when all vectors are unit-normalized (L2 norm = 1). Without normalization, dot product rankings are affected by magnitude differences. This is one of the most commonly misunderstood properties of similarity metrics in vector search. A practitioner who assumes equivalence will introduce length bias without realizing it.

**Why C is wrong:** The model does not inversely normalize output magnitude relative to input length. If the embedding model's training corpus contains longer texts embedded with higher norms on average, that pattern will persist in its outputs unless the model is explicitly trained or configured for unit-norm outputs. There is no automatic inverse normalization.

**Why D is wrong:** The magnitude bias applies to any query, regardless of its length. The query vector's magnitude is also affected by its input length, but the bias is primarily driven by the document vectors' magnitudes, which systematically favor longer chunks in the retrieval ranking. This is not a query-length-dependent effect.

---

## MCQ-16 — Cross-model cosine similarity is not meaningful

**Difficulty:** intermediate
**Topic:** embeddings_and_similarity

**Question:**
A team builds a product catalog index using embedding model A. Six months later they migrate their query pipeline to embedding model B (higher benchmark scores). They forget to re-embed the catalog. A developer notices that cosine similarity scores for all queries are now in the 0.30–0.50 range rather than the previous 0.70–0.90 range, yet the system still returns results. What is the most precise explanation for this score range collapse?

**Options:**
A. Embedding model B produces shorter vectors than model A, reducing the maximum possible cosine similarity to 0.5 for any query
B. Query vectors from model B and document vectors from model A occupy different learned coordinate spaces — the cosine similarity scores are geometrically meaningless across those spaces, and the observed score range is coincidental noise rather than a measure of semantic similarity
C. The vector database applies a normalization correction when it detects dimension mismatches, compressing scores toward the 0.5 midpoint to avoid false positives
D. Cosine similarity scores naturally compress over time as the index grows larger — more vectors means more competition per query, which mathematically reduces all scores toward the population mean

**Correct answer:** B — Each embedding model learns its own coordinate system during training. Dimension N in model A encodes a different latent feature than dimension N in model B. Cosine similarity across the two spaces measures the angle between a point in one coordinate system and a point in a fundamentally different coordinate system. The resulting number is not a semantic signal — it is geometric noise. The narrower score range (0.30–0.50 vs. 0.70–0.90) is a symptom of the cross-space incoherence, not a measure of reduced relevance. The fix is always to re-embed the document corpus with model B before routing live queries through it.

**Why each wrong answer is wrong:**
- **A:** Cosine similarity is bounded between -1 and 1 regardless of vector length. The vector dimension (number of components) does not set an upper bound on cosine similarity — a model that produces 256-dimensional vectors can still return a cosine score of 1.0 for identical inputs. Dimension and cosine range are unrelated properties.
- **B:** This is the correct answer.
- **C:** Vector databases have no cross-model detection mechanism and apply no automatic score normalization. They store and compare float arrays; they have no knowledge of which model produced those arrays. This option invents a non-existent safeguard that practitioners sometimes wish existed.
- **D:** Cosine similarity does not compress as index size grows. The score between a query vector and a specific document vector is a fixed geometric property of those two vectors — adding more vectors to the index does not change pairwise scores. ANN approximate search may return slightly different candidates at scale, but cosine similarity values do not drift toward a population mean by any mathematical property.

