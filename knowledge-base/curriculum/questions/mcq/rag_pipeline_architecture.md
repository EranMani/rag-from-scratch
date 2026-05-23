# MCQ Bank — rag_pipeline_architecture
# Topic: rag_pipeline_architecture
# Phase: 1 (Foundations)
# Questions: 10 (2 novice, 2 intermediate, 3 advanced, 3 expert)
# Last updated: 2026-05-21 (Commit 45)

---

## MCQ-1 — RAG pipeline stages

**Difficulty:** novice
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

**Why A is wrong:** RAG does not involve training the LLM. The model weights are frozen — RAG augments the LLM's input context at inference time. Describing RAG as "training + inference" conflates RAG with fine-tuning, which is a different approach to adapting LLMs to specific domains.

**Why C is wrong:** "Embedding and decoding" describes two operations within the pipeline, not the two phases of the pipeline itself. Decoding is a term from generative modeling (token-by-token generation), not a RAG pipeline phase. This option reflects an LLM-centric view that misses the indexing phase entirely.

**Why D is wrong:** Fine-tuning is a complementary or alternative approach where the LLM's weights are updated on domain-specific data. It is not a phase of RAG. Describing RAG as "retrieval + fine-tuning" conflates two architecturally distinct methods.

---

## MCQ-2 — Role of the vector database

**Difficulty:** novice
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

**Why A is wrong:** Storing full text is a capability some vector databases offer (as a metadata payload alongside the vector), but it is not the primary role. A traditional document store or object store handles full-text storage. Conflating the vector index with the document store leads to architectural decisions that put undue pressure on the vector database for storage workloads it is not optimized for.

**Why B is wrong:** Embedding models are trained once offline on large corpora. The vector database has no visibility into the model's training process. At query time, the embedding model is called externally; the vector database only receives the resulting vector. Confusing the storage layer with the model training layer indicates a fundamental misunderstanding of where each component sits in the pipeline.

**Why D is wrong:** LLM response caching is a separate optimization layer, typically implemented at the API gateway or application level. A semantic cache might store query-response pairs keyed by query embedding, but this is a separate service built on top of the vector database, not the vector database's primary role.

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

**Why A is wrong:** LLMs are not constrained to statistically copy or closely resemble source text. They can paraphrase, interpolate, and in some cases ignore the context entirely — the "statistical similarity" framing reflects a frequency-based view of language generation that does not accurately describe how transformer attention and generation work. RAG reduces hallucination through grounding, not through stylistic constraint.

**Why C is wrong:** Retrieval always returns something — the best match in the index, regardless of whether the index contains a correct answer. If the corpus does not contain information relevant to a query, retrieval still returns the highest-scoring chunks. The LLM may then hallucinate using that irrelevant context as a launching point. RAG does not filter unanswerable questions.

**Why D is wrong:** Cosine similarity scores measure embedding distance in vector space, not the LLM's confidence in its answer. A high similarity score between query and retrieved chunk says nothing about whether the chunk actually answers the query correctly. Thresholding on similarity to infer answer confidence conflates retrieval quality with generation quality.

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

**Why A is wrong:** You cannot embed a full document if it exceeds the model's token limit — the embedding call would fail or silently truncate. Even if documents fit, embedding the full document first and then chunking means each chunk cannot be independently associated with a granular embedding. The vector in the database would represent the whole document, not the chunk retrieved at query time.

**Why C is wrong:** Storing raw documents in the vector database before chunking and embedding has the causal dependencies backward. The vector database requires a vector to store alongside each item. You cannot create that vector without embedding, and you cannot reliably embed without chunking first.

**Why D is wrong:** Query-time chunking means the document would be chunked fresh for every query, which defeats the purpose of the indexing phase. The indexing phase exists to do this work once, offline, so query time only needs to perform retrieval — not parsing, chunking, and embedding from scratch.

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

**Why A is wrong:** Embedding model generalization failure would show up as incorrect retrieval — the system would return wrong chunks regardless of how many are concatenated. The scenario describes degraded response quality with a large corpus, where the retrieved chunks are presumably more numerous and longer, pointing to context window and attention distribution problems rather than embedding quality.

**Why C is wrong:** ANN index recall does degrade slightly with very large corpora (due to approximate search trade-offs), but not in a way that causes the dramatic qualitative degradation described. The index is not "statistically saturated" — that is not a real ANN failure mode. The symptom (degraded responses with correct-looking retrieval) points to the LLM processing stage.

**Why D is wrong:** Adversarial query coverage is a testing practice concern. It might explain why certain edge-case queries fail, but not why the system degrades broadly across production traffic that presumably resembles the development test set. A systemic production degradation with corpus scale points to the architecture, not the test set coverage.

---

## MCQ-6 — Multi-stage failure isolation

**Difficulty:** advanced
**Topic:** rag_pipeline_architecture

**Question:**
A production RAG system shows a drop in RAGAS faithfulness from 0.82 to 0.61 after a weekly content refresh that added 40,000 new documents. context_precision is unchanged at 0.79. Which component most likely caused the faithfulness drop, and what diagnostic step isolates it?

**Options:**
A. The embedding model degraded because the new documents overwhelmed the vector index — run a full re-index rebuild to restore embedding quality
B. The LLM generation step is producing answers that go beyond the retrieved context — faithfulness measures grounding, not retrieval quality. Stable context_precision means retrieval did not change; isolate by running the LLM over the same retrieved chunks from before the refresh and checking if faithfulness scores recover
C. The chunking pipeline introduced poorly-formed chunks from the new documents that diluted the prompt with incoherent context — inspect chunk quality from the new batch before diagnosing the LLM
D. The context window is now overwhelmed because 40,000 new documents increased the number of retrieved chunks per query — reduce top_k to restore context budget

**Correct answer:** B

**Explanation:**
Faithfulness measures whether the LLM's answer is supported by the retrieved context. Context_precision measures whether the retrieved chunks are relevant to the query. When context_precision is stable (retrieval quality unchanged) but faithfulness drops, the LLM generation step is the likely culprit — the model is generating content not grounded in the provided context. This can happen if new documents shifted prompt length (more tokens triggered truncation of key context) or if the new content surface patterns that cause the LLM to revert to parametric knowledge. The diagnostic is to hold the retrieved chunks constant and vary only the LLM input, isolating the generation stage from the retrieval stage.

**Why A is wrong:** Embedding model degradation would show up as lower context_precision (wrong chunks retrieved), not lower faithfulness with stable context_precision. The two metrics are in different pipeline stages. Attributing faithfulness degradation to the index without evidence that retrieval changed is incorrect — it skips the diagnostic step.

**Why C is wrong:** Poorly-formed chunks would reduce retrieval quality and show up as lower context_precision or lower recall, not as faithfulness degradation with stable context_precision. Inspecting chunk quality is a valid pipeline health check, but it is the wrong stage to investigate when the retrieval metric is stable.

**Why D is wrong:** If top_k increased with corpus size and context window pressure caused truncation, the symptom would be lower context_precision (wrong or truncated chunks) combined with faithfulness degradation. But context_precision is stable — the retrieval set is not degraded. Top_k reduction is a valid mitigation for context window pressure but is not the correct diagnosis for this specific metric pattern.

---

## MCQ-7 — Query-time vs. index-time decisions

**Difficulty:** advanced
**Topic:** rag_pipeline_architecture

**Question:**
A team wants to add query expansion (generating multiple phrasings of the user query to improve recall). A developer suggests doing this at index time by pre-expanding every document's content with synonyms before embedding. Another suggests doing it at query time by generating query variants and merging their results. Which statement correctly characterizes the operational difference and the correct placement?

**Options:**
A. Index-time expansion is equivalent to query-time expansion — both add the same information to the retrieval process, so the simpler option (index-time) should be chosen
B. Index-time synonym expansion permanently modifies the corpus — it increases index size, can introduce noise if expansions are low quality, and cannot be changed without re-indexing. Query-time expansion operates on the live query, is reversible, can be model-driven (LLM-generated variants), and does not require re-indexing when expansion strategy changes. Query-time is the correct placement for expansion that needs iteration
C. Index-time expansion is always superior because document embeddings are pre-computed; query-time expansion adds latency for every user query with no quality benefit
D. Query-time expansion increases context_recall but decreases faithfulness because multiple query variants retrieve more chunks, increasing the chance of irrelevant context reaching the LLM

**Correct answer:** B

**Explanation:**
Index-time and query-time expansion are not equivalent — they have fundamentally different operational properties. Index-time expansion is a data pipeline decision: once embedded, the expanded documents define the retrieval surface permanently until re-indexing. Changes to expansion strategy require a full re-index, which is expensive for large corpora. Query-time expansion (HyDE, multi-query retrieval) operates per-request: each query generates variants, retrieval runs for each, and results are merged. This is reversible, can be model-driven, and can be changed without touching the index. The cost is added latency per query from the LLM call that generates variants. For expansion strategies that are likely to evolve (which is most of them), query-time is the correct placement.

**Why A is wrong:** Index-time and query-time expansion are not equivalent. Index-time expansion changes what is stored — every document's embedding now reflects expanded content, which may cause false positive matches for queries that should not match that document. Query-time expansion changes what is searched for on a per-query basis, with full context of the specific user intent. The operational tradeoffs are completely different.

**Why C is wrong:** Index-time expansion is not universally superior. It trades flexibility for pre-computation. A team that ships bad synonyms at index time must re-index to fix them. A team that ships bad query-time expansion can fix it with a prompt change and a deploy. The "no latency cost" advantage of index-time expansion is real, but it is outweighed by the re-indexing cost when expansion quality needs to be iterated.

**Why D is wrong:** Query-time expansion can increase context_recall (more relevant documents found) without necessarily decreasing faithfulness, if the extra chunks are relevant. Faithfulness decreases when irrelevant context reaches the LLM — which is a risk of any recall-improving strategy, but it is not caused by query-time expansion per se. This option incorrectly treats recall and faithfulness as inherently inversely correlated.

---

## MCQ-8 — Stateless RAG and multi-turn failure

**Difficulty:** expert
**Topic:** rag_pipeline_architecture

**Question:**
A RAG chatbot handles multi-turn conversations. A user asks: "What are the side effects of metformin?" (Turn 1), then "Are there any interactions with alcohol?" (Turn 2). The system retrieves and answers Turn 1 correctly. For Turn 2, the system returns a general overview of drug-alcohol interactions, not metformin-specific information. What architectural failure caused this and what is the correct fix?

**Options:**
A. The embedding model does not understand conversational context — fine-tune it on dialogue data to make it resolve pronouns and implicit references
B. The RAG pipeline is stateless — Turn 2's query "Are there any interactions with alcohol?" is embedded without conversational context, so the retriever searches for generic alcohol-drug interactions rather than metformin-specific ones. Fix: implement query rewriting (use an LLM to rewrite the current turn into a self-contained query, e.g., "metformin interactions with alcohol") before retrieval
C. The vector database does not support session-scoped filtering — add a session_id metadata filter so retrieval is scoped to documents retrieved in the current conversation
D. The context window truncated Turn 1 when Turn 2 was processed, causing the LLM to lose the metformin context. Fix: increase context window allocation for multi-turn sessions

**Correct answer:** B

**Explanation:**
A stateless RAG pipeline embeds each query in isolation and retrieves against the full corpus independently per turn. Turn 2's query "Are there any interactions with alcohol?" carries no explicit reference to metformin — the anaphoric reference ("any interactions" implying the drug from Turn 1) is in the conversation history, not in the query text. The retriever sees the raw Turn 2 query and returns generic drug-alcohol content. Query rewriting solves this: before retrieval, an LLM rewrites Turn 2 using conversation history to produce a self-contained query ("What are the alcohol interactions with metformin?"), which the retriever can then match correctly against the corpus. This is an architectural fix at the retrieval stage, not the generation stage.

**Why A is wrong:** Embedding models do not perform coreference resolution across conversation turns — they embed the text they receive. Fine-tuning on dialogue data teaches the model to encode single utterances better, but it does not give the retriever access to prior turns. The retriever's input is still the raw Turn 2 query; fine-tuning the embedding model does not change that.

**Why C is wrong:** Session-scoped filtering restricts retrieval to a subset of the corpus — it would prevent the system from returning information from outside documents already seen in the session. This is the wrong architectural layer to fix. The problem is not which documents to search; it is how to form the query. Scoping retrieval to session-seen documents would actually make recall worse.

**Why D is wrong:** Context window truncation would affect the LLM's generation quality — it might produce a less coherent answer or fail to reference prior turns when generating. But the failure described is at the retrieval stage: the wrong documents are returned before the LLM even sees them. Increasing context window allocation does not fix a retrieval query formation problem.

---

## MCQ-9 — Router pattern silent misfires

**Difficulty:** expert
**Topic:** rag_pipeline_architecture

**Question:**
A RAG system routes queries to one of three retrievers: a product documentation retriever, a support ticket retriever, and a general knowledge retriever. Routing is done by an LLM classifier that assigns each query to a category. After deployment, users report that complex queries (e.g., "my device shows error E44, is this a known issue and what's the documented fix?") receive correct answers 60% of the time but incorrect or incomplete answers 40% of the time. Logs show the router assigns the correct category on these queries only 72% of the time. What is the most operationally precise diagnosis and fix?

**Options:**
A. The LLM router is non-deterministic — the same query routes to different retrievers on different calls. Fix: set temperature=0 on the router LLM to make routing deterministic
B. The query spans multiple categories (error code lookup → support tickets; documented fix → product documentation), and the single-route architecture forces a single retriever to handle a multi-domain query. Routing to only one retriever means the other's relevant content is never retrieved. Fix: implement parallel multi-route retrieval for queries that score above threshold in more than one category, then merge and rerank the results
C. The LLM router is too slow and times out on complex queries, causing fallback to the general knowledge retriever. Fix: replace the LLM router with a faster embedding-based classifier
D. The 72% routing accuracy is acceptable given query complexity — the 40% failure rate is caused by gaps in the underlying document corpora, not routing errors. Fix: improve corpus coverage

**Correct answer:** B

**Explanation:**
A query like "is this a known issue and what's the documented fix?" is a multi-intent query spanning at least two retrieval domains: the support ticket retriever would recognize the error code and known issue patterns, while the product documentation retriever would have the official fix procedure. A single-route architecture forces a winner-take-all decision, so even when the router picks correctly for one intent, the other intent's relevant content is silently missed. The symptom — 40% failure rate on complex queries, 72% routing accuracy — is consistent with the 28% outright misrouting plus a subset of "correctly" routed queries that are missing one domain. Parallel multi-route retrieval with result merging handles multi-intent queries without requiring the router to be perfect.

**Why A is wrong:** Setting temperature=0 makes routing deterministic — the same query will always route the same way. But if the route is wrong at temperature=0, it will be wrong every time, which is worse than the current 28% error rate, not better. Determinism is not the same as accuracy. The router's problem is not variance; it is that single-route architecture cannot handle multi-intent queries.

**Why C is wrong:** LLM router latency is a valid optimization concern, but the problem described is accuracy, not latency. Timeouts would produce a consistent fallback behavior (always routed to general knowledge), not a 72% accuracy pattern. Replacing the router with an embedding-based classifier might be faster but does not address the single-route limitation.

**Why D is wrong:** The 28% routing error rate on queries where accuracy matters is not negligible. Dismissing routing errors as "acceptable" without investigation and attributing 40% failure to corpus gaps is optimistic without evidence. A 72% routing accuracy on complex queries is a diagnosable problem, not a baseline to accept.

---

## MCQ-10 — Query expansion metric inversion: high faithfulness, low context_precision

**Difficulty:** expert
**Topic:** rag_pipeline_architecture

**Question:**
A RAG pipeline adds a query expansion step that generates 3 query variants from each user query using an LLM, runs retrieval for each variant, and merges the result sets before passing context to the generator. After this change, RAGAS faithfulness increases from 0.74 to 0.89, but context_precision drops from 0.81 to 0.58. The team debates whether to keep the change. What is the structural reason for this specific metric pattern, and does it represent a net quality improvement?

**Options:**
A. Query expansion increased faithfulness because it retrieves more chunks, giving the LLM more material to be faithful to. Context_precision dropped because more chunks means more irrelevant chunks in the context window. This is an unambiguous net degradation — the system is now generating longer answers that quote irrelevant passages
B. Query expansion generates semantically diverse query variants, which retrieves a broader set of chunks. The broader set improves recall — more of the relevant documents are found — which increases the LLM's ability to ground its answer (faithfulness up). But the broader set also includes chunks that are relevant to the query variants but not the original query intent, which dilutes precision. Whether this is a net improvement depends on whether the use case is penalized more for missed answers (recall-sensitive) or for noisy context (precision-sensitive) — the metric pattern alone does not answer this
C. The metric inversion is caused by a RAGAS configuration error — faithfulness and context_precision are computed from the same retrieved context, so they cannot move in opposite directions by design. The correct action is to rerun the evaluation with a corrected RAGAS configuration
D. Query expansion always degrades context_precision because LLMs cannot generate query variants that match the original user intent. The faithfulness increase is an artifact of averaging over more chunks, which inflates the metric without reflecting genuine grounding improvement

**Correct answer:** B

**Explanation:**
Query expansion is a recall-improving technique: generating semantic variants of the original query retrieves documents that match the concept from different angles. This directly improves recall (more relevant documents found) and consequently faithfulness — the LLM has more correct grounding material available. The precision cost is real and structural: variant-retrieved chunks are relevant to the expanded query landscape, not exclusively to the original user intent. A chunk retrieved because it matches variant "metformin side effects in elderly patients" may be technically related but not directly answering "what are metformin side effects" in a general context. Whether this tradeoff is acceptable is a product decision, not a metric decision. In recall-sensitive use cases (high-stakes domains where missing an answer is worse than over-retrieving), the tradeoff is worthwhile. In precision-sensitive use cases (conversational assistants where a noisy context window produces verbose or confused answers), it may not be. The metric pattern is working as designed; the evaluation tells you the nature of the tradeoff, not the verdict.

**Why A is wrong:** The claim that more chunks causes the LLM to "quote irrelevant passages" and produce longer answers is only partially true. Faithfulness measures whether the claims in the answer are supported by the context — a faithfulness increase with more chunks means the LLM is generating claims that are supported by the broader context set, not that it is quoting irrelevant material verbatim. The characterization of this as "unambiguous net degradation" ignores the recall improvement: the system is now answering questions it previously could not. Whether that is worth the precision cost requires a use-case evaluation, not a declaration from the metric pattern alone.

**Why C is wrong:** Faithfulness and context_precision are computed by different operations and can absolutely move in opposite directions. Faithfulness measures claim-to-context support (did the LLM stay grounded in what it was given?). Context_precision measures whether the retrieved chunks were relevant to the query (was what it was given good quality?). A system can be highly faithful to a low-precision context set: the LLM accurately generates from the chunks it received, but those chunks contained irrelevant content. The metrics are independent by design. Concluding "configuration error" when metrics diverge reflects a misunderstanding of what each metric evaluates.

**Why D is wrong:** The faithfulness increase is not a statistical artifact of averaging. RAGAS faithfulness decomposes the generated answer into atomic claims and checks each against the context — it is not an average similarity score. More chunks do not inflate faithfulness unless the LLM's claims are actually traceable to those chunks. The claim that "LLMs cannot generate query variants that match original intent" is also false in practice — LLM-based query expansion with a well-designed prompt reliably generates semantically related variants. The precision drop is real and documented, but it does not make the faithfulness improvement spurious.

