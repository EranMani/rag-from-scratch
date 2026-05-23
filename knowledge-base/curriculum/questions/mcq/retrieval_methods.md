# MCQ Bank — retrieval_methods
# Topic: retrieval_methods
# Phase: 2 (Core Components)
# Questions: 15 (5 novice, 5 intermediate, 3 advanced, 2 expert)
# Last updated: 2026-05-23 (Commit 51)

---

## MCQ-1 — Dense vs. sparse retrieval

**Difficulty:** novice
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

**Why A is wrong:** Both dense and sparse retrieval methods index document content, not just titles and headings. This option conflates sparse retrieval with a headline-based indexing scheme (like early web search). A developer who has used only full-text search over metadata might carry this model.

**Why C is wrong:** Dense retrieval is not uniformly faster — ANN search in a vector database has its own latency profile, and sparse retrieval with an inverted index can be extremely fast for large corpora. The speed claim reverses which method tends to be faster for specific corpus sizes.

**Why D is wrong:** Hardware requirements are reversed. Dense retrieval benefits from GPU acceleration during embedding generation, but query-time ANN search runs on CPU. Sparse BM25 runs entirely on CPU. Neither method strictly requires a GPU.

---

## MCQ-2 — When BM25 outperforms dense retrieval

**Difficulty:** novice
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

**Why A is wrong:** "Supervised vs. unsupervised learning" is a conceptual question requiring semantic understanding. A person might phrase it many different ways, and the answer might be phrased differently in the corpus. Dense retrieval excels here; BM25 would only match documents that happen to use exactly those words.

**Why B is wrong:** "What is the capital of France?" is a short factual query where both methods would likely succeed if the document contains "France" and "Paris." Neither method clearly dominates for this type of short factual lookup.

**Why D is wrong:** "Strategies for managing stress at work" is a conceptual query that benefits from semantic retrieval — a document about "coping mechanisms for workplace anxiety" would be relevant but contains no BM25-matching keywords from the query.

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

**Why A is wrong:** Score product rewards documents that appear in both lists but catastrophically penalizes any document absent from one system (its score becomes zero). This destroys one of hybrid retrieval's main benefits: surfacing documents that score well in only one modality. Practitioners who intuit "combine two scores by multiplying" are following a reasonable math instinct but one that fails here.

**Why C is wrong:** Simple concatenation with deduplication does not account for ranking position — a document ranked #1 in BM25 and rank #1 in dense retrieval would be treated the same as a document that appears in only one list at rank #50. Fusion requires position-aware scoring, not just set union.

**Why D is wrong:** Score normalization and weighted average is a legitimate fusion technique (alpha-weighted hybrid), but it is not RRF. Confusing it with RRF is common because both produce a combined score. The critical difference is that RRF is rank-based and does not require scores from both systems to be on the same scale.

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
Vector retrieval returns documents that are geometrically close in embedding space, which is a proxy for relevance but not a direct measure of it. A reranker (typically a cross-encoder that jointly processes query and document) scores each candidate with direct attention to the query, producing a relevance ranking that is more discriminative than cosine similarity alone. This two-stage approach (fast ANN retrieval followed by precise reranking) balances latency and accuracy.

**Why A is wrong:** Rerankers do not retrain in real time. They are pre-trained models used at inference time to score query-document pairs. Real-time training from user feedback is a separate online learning paradigm that requires careful infrastructure and is not what rerankers provide. Developers who want a "learning" system reach for A.

**Why C is wrong:** A reranker scores and reorders — it does not compress documents. Summarization reduces token count; reranking changes rank order. This option appeals to developers who reason about context window limits and conflate "improving what goes to the LLM" with "compressing what goes to the LLM."

**Why D is wrong:** Re-indexing updates the stored vectors when document content changes. It is an indexing operation, not a query-time operation. Confusing reranking (query-time relevance scoring) with re-indexing (index maintenance) is common among developers who have not distinguished the querying and indexing pipelines.

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
Query expansion improves recall by casting a wider net — more phrasings means more chance of matching how the answer is phrased in the corpus. However, LLM-generated expansions can drift semantically: an expansion of "battery life" might include "energy density," which retrieves chemistry papers not relevant to the user's question about laptops. This semantic drift is the mechanism behind precision degradation.

**Why A is wrong:** Semantically similar queries produce similar but not identical embedding neighbors. The expanded queries are intentionally different phrasings — they intentionally retrieve different documents. If they were identical, expansion would produce no recall improvement. The distinction between "very similar neighbors" and "the same neighbors" is the whole point of query expansion.

**Why C is wrong:** Latency is a valid operational concern about query expansion (4 retrievals instead of 1) but is a separate problem from precision degradation. Timeout would produce missing results, not off-topic results. The question asks about precision, not latency.

**Why D is wrong:** Deduplication removes duplicate documents, not high-scoring ones. A document returned by all 4 queries would appear once in the deduplicated set, not zero times. This option inverts the mechanism of deduplication.

---

## MCQ-6 — BM25 on paraphrase-heavy corpora

**Difficulty:** intermediate
**Topic:** retrieval_methods

**Question:**
A customer support knowledge base is written by multiple authors over several years. Documents use varied vocabulary: "cancel subscription," "terminate account," "stop service," and "end billing" all refer to the same action. A BM25 retriever is deployed. A user queries "how do I cancel my subscription?" and receives no relevant results, despite there being relevant documents in the corpus. What is the most precise explanation?

**Options:**
A. BM25 cannot index documents longer than 512 tokens, so the relevant documents were silently skipped during indexing
B. BM25 assigns zero score to documents that share no query terms — if the relevant document uses only "terminate account" and "end billing" without any occurrence of "cancel" or "subscription," the BM25 score is zero regardless of semantic relevance
C. BM25 deprioritizes documents from older authors because term frequency statistics decay over time
D. The user's query is too short for BM25 to compute a reliable score — queries under 5 tokens always return zero results in BM25

**Correct answer:** B

**Explanation:**
BM25 is a pure term-frequency model. If a document contains none of the query terms (including stemmed variants), its BM25 score is zero. A corpus with high vocabulary variability — where authors paraphrase the same concept with different vocabulary — produces BM25 zero-scores for semantically relevant documents. This is the fundamental limitation that motivates hybrid retrieval: dense embeddings would bridge the semantic gap between "cancel subscription" and "terminate account," but BM25 cannot. In a paraphrase-heavy corpus, BM25 recall degrades proportionally to vocabulary inconsistency.

**Why A is wrong:** BM25 has no document length limit — it is an inverted index over term occurrences and handles arbitrary document length. Document length affects the normalization factor in the BM25 formula (the b parameter), but does not cause documents to be silently skipped.

**Why C is wrong:** BM25 statistics are computed at index time over the full corpus. There is no time-decay of term frequency — older documents are indexed and scored identically to newer ones. This option appeals to developers who assume BM25 behaves like a recommendation system with recency weighting.

**Why D is wrong:** BM25 can score a query of any length, including single-token queries. Short queries produce fewer term matches but are not treated specially. A two-word query like "cancel subscription" will score normally against documents containing those terms.

---

## MCQ-7 — HyDE hallucination steering retrieval

**Difficulty:** advanced
**Topic:** retrieval_methods

**Question:**
A team implements HyDE (Hypothetical Document Embeddings): before retrieval, an LLM generates a hypothetical document that would answer the user's query, and that hypothetical document's embedding is used for retrieval instead of the query's embedding. During evaluation, they observe that for some query types, HyDE retrieves less relevant documents than direct query embedding. What is the most precise failure mode?

**Options:**
A. The hypothetical document is always longer than the query, producing an embedding that is diluted by the extra tokens and scores lower similarity with all corpus documents
B. The LLM's hypothetical document introduces factual errors or domain-specific details inconsistent with the actual corpus vocabulary — the embedding of the hallucinated document steers retrieval toward documents that match the hallucination's content rather than the ground truth
C. HyDE requires a fine-tuned LLM to generate accurate hypothetical documents — with a general-purpose LLM, the generated document is always semantically identical to the original query, providing no benefit
D. The embedding model cannot handle hypothetical documents because they contain conditional language ("would," "might," "could") that the model was not trained on

**Correct answer:** B

**Explanation:**
HyDE works when the LLM's hypothetical document accurately mirrors the vocabulary and framing of real corpus documents, making the hypothetical embedding a better retrieval query than the raw question. It fails when the LLM hallucinates: if the hypothetical document includes factual claims, terminology, or framings not present in the corpus, the resulting embedding points toward a region of the vector space that contains documents matching the hallucination, not the actual answer. For example, a query about a proprietary internal system might produce a hypothetical document describing a well-known public system instead. HyDE is most useful for general, well-represented domains and most dangerous for specialized corpora where the LLM is likely to confabulate domain-specific details.

**Why A is wrong:** Embedding models produce fixed-length vectors regardless of input length (within the model's context window). A longer hypothetical document does not produce a diluted embedding — the embedding captures the semantic content of the full input, not token length. Length does affect what content is represented if the input exceeds the model's window, but dilution is not the mechanism.

**Why C is wrong:** HyDE is useful precisely because a general-purpose LLM can generate domain-plausible language for many query types. It does not require fine-tuning. The benefit comes from converting a question (which may be phrased differently from how answers are phrased in the corpus) into a document-style embedding.

**Why D is wrong:** Embedding models handle all natural language, including hypotheticals and conditional statements. There is no training data restriction that makes hypothetical language unembeddable. The embedding model does not parse grammatical mood — it encodes semantic content.

---

## MCQ-8 — Hybrid retrieval alpha miscalibration

**Difficulty:** advanced
**Topic:** retrieval_methods

**Question:**
A hybrid retrieval system uses alpha-weighted score fusion: `final_score = alpha * dense_score + (1-alpha) * bm25_score`. The team sets `alpha=0.5` as a default. In production, they observe that for queries containing rare product SKUs (e.g., "XR-9912-B replacement part"), retrieval recall is significantly lower than during testing. The test corpus had broad coverage of general product descriptions; the production corpus is more specialized with heavy use of alphanumeric identifiers. What is the most precise diagnosis?

**Options:**
A. alpha=0.5 over-weights dense retrieval for exact-identifier queries — BM25 is far more effective for alphanumeric SKU matching, and raising alpha toward 1.0 would increase recall
B. alpha=0.5 over-weights dense retrieval — but the fix is to lower alpha toward 0.0 to give BM25 full weight for SKU queries
C. The alpha parameter does not affect recall for exact-match queries — the recall failure is caused by the vector database's ANN index missing the relevant document during search
D. alpha=0.5 is correctly calibrated — the recall failure indicates the BM25 index was not updated to include the new production documents

**Correct answer:** B

**Explanation:**
For queries containing exact alphanumeric identifiers, BM25 is the dominant retrieval signal — the specific string "XR-9912-B" either appears in a document or it does not, and BM25 scores that exact match heavily. Dense embeddings are unreliable for rare alphanumeric strings that appear infrequently in training data. With `alpha=0.5`, the dense component contributes equally to the final score even though it provides near-zero signal for these queries. Lowering alpha (reducing dense weight, increasing BM25 weight) for identifier-heavy queries increases recall. Ideally, the alpha parameter is query-type-adaptive rather than a fixed global constant.

**Why A is wrong:** The direction of the fix is correct (de-emphasize dense retrieval) but the alpha direction is wrong. A higher alpha means more dense weight. Raising alpha toward 1.0 would make the problem worse, not better. This option contains the right diagnosis and the wrong remediation — a dangerous combination in production.

**Why C is wrong:** The alpha parameter directly affects the contribution of BM25 to the final score. If alpha=0.5 down-weights BM25, documents that BM25 would rank first may not appear in the final top-k even if BM25 found them. The recall failure is in the fusion step, not in the ANN index.

**Why D is wrong:** A correctly calibrated alpha for general queries is not correctly calibrated for all query types. Fixed hyperparameters that work in testing often require tuning when production query distribution shifts. The recall failure is not about indexing freshness — it is about weight miscalibration for a specific query pattern.

---

## MCQ-9 — Cross-encoder as first-stage retriever

**Difficulty:** expert
**Topic:** retrieval_methods

**Question:**
A developer proposes using a cross-encoder directly as the first-stage retriever (replacing ANN search) to maximize retrieval precision. They argue: "cross-encoders score query-document pairs more accurately than bi-encoders, so using them from the start will produce better results." What is wrong with this design and why does it fail at scale?

**Options:**
A. Cross-encoders cannot be used for retrieval because they do not produce vector embeddings — they can only be used for classification tasks
B. Cross-encoders require the full document text to score a pair — they cannot operate on chunks and require a full re-chunking step before every query
C. Cross-encoders score one query-document pair at a time with joint attention, requiring O(n) full forward passes through the model for a corpus of n documents — this is computationally infeasible at any corpus size beyond a few thousand documents
D. Cross-encoders are fine-tuned on ranking datasets and produce unreliable scores when the query and document come from different domains, making them unsuitable for first-stage retrieval

**Correct answer:** C

**Explanation:**
A bi-encoder embeds queries and documents independently — embeddings are precomputed offline and stored, so query time requires only one query embedding plus fast ANN search. A cross-encoder jointly encodes the query and each candidate document together, running a full attention mechanism over the combined input. This means for a corpus of n documents, scoring all of them requires n cross-encoder forward passes at query time. At 100,000 documents, this is 100,000 model inferences per query — with a typical cross-encoder taking 10–50ms per pair, this produces latency of 16 minutes to 83 minutes per query. Cross-encoders are operationally viable only as second-stage rerankers over a small candidate set (typically top-50 to top-200) already filtered by fast first-stage retrieval.

**Why A is wrong:** Cross-encoders can absolutely be used for relevance scoring of query-document pairs — they produce a scalar relevance score, not a vector embedding, but this is by design. They are commonly used in reranking pipelines. The claim that they "can only be used for classification" is technically partially true (they output a score that can be interpreted as a classification probability) but incorrectly restricts their use.

**Why B is wrong:** Cross-encoders process whatever text is passed to them — they can score chunks just as easily as full documents. The input length constraint is the model's context window, not a requirement to re-chunk. This option invents a limitation that does not exist.

**Why D is wrong:** Cross-encoders are trained on ranking signal and generalize well across domains when trained on diverse data (e.g., MS MARCO). Domain mismatch is a concern for any pre-trained model, but it is not the primary operational reason cross-encoders fail as first-stage retrievers. The computational complexity issue (C) is the disqualifying factor.

---

## MCQ-10 — MMR lambda and diversity cost

**Difficulty:** expert
**Topic:** retrieval_methods

**Question:**
A RAG pipeline uses Maximum Marginal Relevance (MMR) retrieval with `lambda=0.3` to diversify results. The evaluation team observes that context recall has dropped from 0.85 (with standard similarity retrieval) to 0.61 with MMR. A developer suggests raising `lambda` to 0.7. What is the precise tradeoff they are navigating, and when does MMR's diversity penalty become unacceptable?

**Options:**
A. Lambda controls the balance between relevance and diversity — higher lambda means more relevance weight, less diversity. Raising lambda to 0.7 will improve recall at the cost of returning more redundant documents. The diversity penalty becomes unacceptable when the query requires information from multiple distinct sub-topics
B. Lambda controls the balance between relevance and diversity — higher lambda means more diversity weight, less relevance. Raising lambda to 0.7 will further decrease recall. The correct fix is to increase the initial candidate pool size before MMR selection
C. MMR lambda has no effect on recall — recall measures what fraction of relevant documents are in the corpus, not what is retrieved. The 0.61 vs. 0.85 difference reflects a change in the retrieval budget, not the lambda setting
D. Lambda above 0.5 disables diversity entirely — raising lambda to 0.7 will revert to standard similarity retrieval with no diversity penalty

**Correct answer:** A

**Explanation:**
In MMR, `lambda` weights the tradeoff: `score = lambda * relevance - (1-lambda) * max_similarity_to_selected`. High lambda (near 1.0) means the selection is dominated by relevance — MMR behaves like standard similarity search. Low lambda (near 0.0) means the selection is dominated by novelty — each new document must be as different as possible from already-selected documents, even if that means selecting less relevant ones. At `lambda=0.3`, MMR strongly penalizes documents similar to already-selected ones, which can exclude highly relevant documents if they are semantically close to a previously selected document. Raising lambda to 0.7 reduces the diversity penalty and improves recall at the cost of returning more redundant chunks. The diversity penalty is most harmful when the query has a single correct answer that appears in multiple highly similar documents — MMR will only select one of them and replace the rest with less relevant but "diverse" documents.

**Why B is wrong:** Higher lambda means more relevance weight (less diversity), not more diversity weight. This inverts the direction of the lambda parameter. The confusion is common because "higher lambda = more diversity" sounds intuitive if you read lambda as controlling diversity, but the formula shows lambda scales the relevance term.

**Why C is wrong:** Context recall in RAGAS measures the fraction of relevant information present in the retrieved set. It is a per-query metric, not a corpus-level metric. MMR's lambda directly affects which documents are selected and therefore directly affects context recall. The 0.24 drop is a real metric degradation caused by MMR excluding relevant documents in favor of diverse ones.

**Why D is wrong:** Lambda is a continuous weight parameter in the range [0, 1]. There is no threshold above which diversity is disabled. At lambda=1.0, MMR is mathematically equivalent to pure relevance ranking. At lambda=0.7, diversity still plays a role — it is simply weighted less heavily than at 0.3.

---

## MCQ-11 — What retrieval returns to the LLM

**Difficulty:** novice
**Topic:** retrieval_methods

**Question:**
In a RAG query pipeline, what does the retrieval step pass to the LLM?

**Options:**
A. The raw embedding vector of the user's query
B. The full contents of every document in the knowledge base
C. The text of the most semantically similar document chunks, along with the user's original question
D. A ranked list of document titles that the LLM can then request to read

**Correct answer:** C

**Explanation:**
The retrieval step finds the K most semantically similar chunks to the query and passes their raw text content to the prompt assembly step. The prompt then combines those chunk texts with the user's question and hands the full prompt to the LLM for generation. The LLM never sees the embedding vector (A) — it only processes text. It does not receive the full document corpus (B) — retrieval exists precisely to select the most relevant subset. It does not receive a list of titles to then request (D) — the LLM in a standard RAG pipeline receives context, not the ability to issue further retrieval requests.

**Why A is wrong:** Embedding vectors are floating-point arrays used internally for similarity computation. LLMs process text tokens, not numeric vectors. The LLM never sees the embedding at any stage. A developer who has read about embeddings but not yet built a full RAG pipeline may confuse the intermediate representation (vector) with what the LLM ultimately receives (text).

**Why B is wrong:** The reason RAG uses retrieval at all is precisely to avoid sending the entire corpus to the LLM — which would far exceed the context window and be prohibitively expensive. A developer who understands RAG at the surface level ("RAG gives the LLM your documents") might choose B without distinguishing what the retrieval step selects.

**Why D is wrong:** Standard RAG pipelines inject the chunk text directly into the prompt rather than giving the LLM a list of titles to request. Agentic retrieval patterns (where the LLM can issue follow-up retrieval requests) are an advanced pattern beyond the standard pipeline, and even there, the LLM still receives text chunks, not just titles.

---

## MCQ-12 — The role of top-K in retrieval

**Difficulty:** novice
**Topic:** retrieval_methods

**Question:**
The top-K parameter in vector retrieval controls how many chunks are returned. If you increase K from 3 to 10, which of the following is most likely?

**Options:**
A. Retrieval latency doubles because the ANN index must scan twice as many vectors
B. Context recall increases (more relevant information is included) but context precision decreases (more irrelevant chunks may be included)
C. The embedding model must be re-run for each additional chunk, significantly increasing retrieval cost
D. The LLM becomes more likely to hallucinate because it receives too many instructions

**Correct answer:** B

**Explanation:**
Increasing K brings more chunks into the context. If the 4th through 10th most similar chunks include additional relevant content, context recall improves — more of the needed information is present. However, lower-ranked chunks are less similar to the query on average, so they are more likely to include off-topic content — reducing context precision. This recall-precision tradeoff is why top-K requires calibration rather than simply maximizing it. ANN search latency (A) is not proportional to K — it is proportional to the search beam width (ef parameter), not the number of results returned. Embedding is done once per query regardless of K (C). LLM hallucination is not caused by chunk count alone (D).

**Why A is wrong:** ANN search terminates when it has found the K nearest neighbors within the configured exploration budget (ef). Increasing K slightly affects only the final result selection step, not the core graph traversal. Latency is not proportional to K in any simple way — it is primarily a function of ef and index connectivity. A developer who assumes "more results = more search" misunderstands how ANN indexes work.

**Why C is wrong:** The embedding model runs once per query to produce the query vector. The K retrieved chunks were embedded at indexing time and stored. At query time, no additional embedding calls are needed regardless of how large K is. A developer who thinks "I retrieve 10 chunks so I need 10 embedding calls" has confused indexing-time embedding with query-time retrieval.

**Why D is wrong:** Hallucination risk in RAG is driven by the quality and relevance of retrieved context, not the count of chunks. A larger K with relevant additional chunks reduces hallucination (more grounding). A larger K with many irrelevant chunks can increase noise and reduce faithfulness — but the mechanism is context noise, not "too many instructions." Framing chunk count as "instructions" reflects a misunderstanding of how the LLM processes its prompt.

---

## MCQ-13 — Reranker position in a pipeline

**Difficulty:** novice
**Topic:** retrieval_methods

**Question:**
Where does a reranker sit in a RAG pipeline?

**Options:**
A. Before retrieval — the reranker filters documents in the index before the ANN search runs
B. Between the vector retriever and the LLM — it re-scores the retrieved candidates and reorders them before context injection
C. Inside the LLM — modern LLMs have built-in reranking that scores each retrieved chunk as it processes them
D. After the LLM generates its answer — the reranker scores each sentence in the answer for relevance

**Correct answer:** B

**Explanation:**
A reranker sits between the first-stage retriever and the LLM. The retriever returns top-K candidates quickly using ANN search. The reranker then scores each candidate (query, chunk) pair with a more precise model (typically a cross-encoder) and reorders the list. Only the top-N reranked chunks (typically 3–5) are passed to the LLM. This two-stage design balances speed (fast ANN retrieval) with precision (accurate reranking over a small candidate set). Option A describes a pre-filter, which is a different concept. Options C and D describe non-existent pipeline positions.

**Why A is wrong:** Pre-filtering restricts which vectors are eligible for ANN search using metadata predicates (e.g., department = "legal"). A reranker operates after ANN search has already completed and returned candidates — it never runs before retrieval. Confusing pre-filtering with reranking indicates a misunderstanding of both concepts: pre-filtering removes candidates before similarity search; reranking reorders candidates already retrieved by similarity search.

**Why C is wrong:** Standard LLMs do not contain built-in reranking mechanisms for retrieved chunks. They process their entire context window through attention layers but do not score or reorder individual chunks within the prompt. Agentic frameworks may implement tool use that simulates this, but that is application-level orchestration, not a built-in LLM capability. A developer who believes "the LLM is smart enough to know which chunks matter" may choose C, overestimating what the model does internally.

**Why D is wrong:** Post-generation scoring is an evaluation operation (like RAGAS faithfulness checking), not a reranking operation. A reranker operates on candidate chunks before they reach the LLM. Scoring sentences in the output after generation would be a different pattern — verifying the output, not selecting the input. This distractor catches developers who think of "reranking" as a quality control step at the end of the pipeline rather than a retrieval improvement step at the beginning.

---

## MCQ-14 — Why BM25 and dense retrieval complement each other

**Difficulty:** intermediate
**Topic:** retrieval_methods

**Question:**
A team uses only dense vector retrieval. On evaluation, they notice that queries containing rare product identifiers (part numbers, version strings) have significantly lower context_recall than general questions. Which statement best explains why and what the fix is?

**Options:**
A. Dense retrieval fails on rare identifiers because the ANN index cannot represent short strings — fix: use a character-level embedding model
B. Dense retrieval fails on rare identifiers because the embedding model likely has not seen these identifiers frequently in training, so the learned vector does not discriminate between "XR-9912" and similar-sounding strings — fix: add BM25 as a parallel retrieval path and fuse results with RRF
C. Dense retrieval fails because part numbers contain hyphens, which the tokenizer splits incorrectly — fix: preprocess part numbers to remove hyphens before embedding
D. The ANN index degrades for queries with rare vocabulary because infrequent query vectors land in low-density graph regions — fix: increase ef_construction to improve coverage in sparse graph regions

**Correct answer:** B

**Explanation:**
Dense embedding models learn representations from training data. Rare alphanumeric identifiers like part numbers appear infrequently in general training corpora and may not appear at all. The model cannot learn meaningful discriminative representations for them — "XR-9912" and "XR-9913" may produce nearly identical embeddings because the model has seen neither and cannot distinguish them. BM25 is immune to this: it operates on exact token frequency and scores documents containing "XR-9912" exactly higher than all others, regardless of how rare the identifier is. Hybrid retrieval (BM25 + dense with RRF fusion) captures both the semantic recall of dense retrieval and the exact-match precision of BM25.

**Why A is wrong:** Dense retrieval works on strings of all lengths, including short identifiers. Character-level models do exist but are not the standard fix for rare-identifier recall failure. The core issue is not string length — it is embedding quality for low-frequency vocabulary. Switching to a character-level model would partially help but introduces new problems (character-level models are weaker for semantic similarity) and misses the simpler, more targeted fix of adding BM25.

**Why C is wrong:** Tokenizers handle hyphens routinely — they split "XR-9912" into tokens such as ["XR", "-", "9912"] or similar. This tokenization does not cause the embedding to fail; the model has learned to incorporate punctuation-adjacent tokens. The failure is not tokenization but the absence of "XR-9912" as a meaningful unit in training data. Preprocessing by removing hyphens would actually make the problem worse by making similar-sounding identifiers more likely to collide in embedding space.

**Why D is wrong:** ANN index graph density is a function of how closely spaced the stored vectors are in the high-dimensional space, not of query vocabulary frequency. A rare query landing in a low-density region of the graph would still find its nearest neighbor — just with potentially fewer graph connections to navigate through. The recall problem for rare identifiers is an embedding quality problem (poor discrimination in the vector space), not a graph navigation problem. Increasing ef_construction improves graph connectivity but does not fix the fundamental issue of uninformative embeddings for rare tokens.

---

## MCQ-15 — Sparse vs. dense retrieval index update cost

**Difficulty:** intermediate
**Topic:** retrieval_methods

**Question:**
A production RAG system adds 10,000 new documents per day. The team is choosing between a BM25 sparse index and an HNSW dense index for retrieval. Which statement correctly describes the incremental update cost difference between the two?

**Options:**
A. Both indexes require a full rebuild when new documents are added — neither supports incremental insertion
B. BM25 index updates are more expensive than HNSW updates because recomputing IDF statistics across the corpus requires recalculating scores for all existing documents
C. HNSW supports O(log N) incremental insertion per document; BM25 index updates require recalculating global IDF statistics, which involves touching the full corpus vocabulary — making BM25 updates more expensive at scale
D. HNSW does not support incremental document insertion — new documents must accumulate in a separate flat index and merge in a nightly rebuild

**Correct answer:** C

**Explanation:**
HNSW supports efficient incremental insertion: each new vector is inserted into the graph by finding its neighbors and adding bidirectional edges. This is O(log N) per document in terms of graph traversal. BM25 depends on corpus-wide statistics: IDF (inverse document frequency) is computed as log(N / df), where N is the total document count and df is the number of documents containing each term. Adding new documents can change IDF values for every term those documents contain, requiring recalculation across the corpus. In practice, production BM25 implementations often defer full IDF recalculation and use approximate or staged updates, but the fundamental statistical dependency on corpus size makes BM25 updates more costly to keep perfectly calibrated than HNSW insertions.

**Why A is wrong:** HNSW supports incremental insertion natively — this is one of its key design properties. Adding a new vector connects it into the existing graph without rebuilding. BM25 indexes (implemented as inverted indexes) also support incremental document addition via posting list appends, though IDF recalculation remains a concern. Neither requires a full rebuild for every insertion, making A entirely incorrect.

**Why B is wrong:** Option B states the correct conclusion (BM25 updates are more expensive) but overstates the mechanism. BM25 incremental updates do not necessarily "recalculate scores for all existing documents" — inverted index posting lists append new document entries without reprocessing old documents. The cost is IDF statistics becoming stale, not a per-document re-scoring. The actual mechanism of B is incorrect even though the directional conclusion matches C.

**Why D is wrong:** HNSW does support incremental insertion — this is explicitly supported by major vector databases including Qdrant, Weaviate, and Milvus. The claim that HNSW requires a flat index accumulation layer and nightly rebuild is incorrect. This distractor captures developers who have read about HNSW's offline batch construction mode (used for initial index build from a large corpus) and incorrectly assumed it applies to all insertions.
