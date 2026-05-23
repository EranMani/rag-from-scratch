# Question Bank: `embeddings_and_similarity`
# Phase: 1 — Foundations
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-23 (Commit 51)

---

## Q1 — What is a vector embedding?

**Difficulty:** novice

**Question:**
In your own words, explain what a vector embedding is. What does it represent, and why
is it useful for comparing text?

**Correct answer criteria:**
- States that an embedding is a fixed-length numerical vector (array of floats) that
  represents a piece of text
- Explains that the vector encodes semantic meaning — similar texts produce vectors
  that are close together in the vector space
- Does not claim that individual dimensions correspond to specific words or human-readable
  concepts
- Mentions that the representation is learned (from training data), not manually crafted

**Partial credit criteria:**
- Correctly describes embeddings as numerical vectors but does not explain that closeness
  in vector space corresponds to semantic similarity
- Explains the semantic similarity property but describes it as "mapping words to numbers"
  without capturing the geometric/representational aspect

**Incorrect / no-credit criteria:**
- Describes embeddings as "a list of keywords extracted from the text"
- Claims each dimension means something specific (e.g., "dimension 42 measures sentiment")
- Confuses embedding with tokenization or hashing

**Follow-up probe:**
If the learner says "similar texts have similar vectors" but cannot explain what "similar"
means geometrically, ask: "How would you measure how similar two embedding vectors are?
What does that calculation tell you?"

---

## Q2 — Cosine similarity vs. Euclidean distance

**Difficulty:** intermediate

**Question:**
You have two embedding vectors representing two sentences. Explain the difference between
measuring their similarity using cosine similarity versus Euclidean distance. Which is
more commonly used for text embeddings and why?

**Correct answer criteria:**
- Cosine similarity measures the angle between two vectors (regardless of their magnitude)
- Euclidean distance measures the straight-line distance between vector endpoints, which
  is affected by vector magnitude
- For text embeddings, cosine similarity is generally preferred because embedding models
  often produce vectors of varying magnitudes, and semantic similarity is better captured
  by direction than absolute distance
- Notes that if vectors are L2-normalized (magnitude = 1), cosine similarity and Euclidean
  distance rank pairs identically (they become equivalent in that specific case)

**Partial credit criteria:**
- Correctly identifies cosine similarity as angle-based and Euclidean as distance-based
  but cannot explain why cosine is preferred for text
- States cosine is better for text but cannot explain the magnitude-invariance property

**Incorrect / no-credit criteria:**
- Claims Euclidean distance is preferred for text without justification
- Defines cosine similarity as "the dot product of two vectors" without noting the
  normalization step that makes it angle-based
- Cannot distinguish between the two methods at all

---

## Q3 — The geometry of semantic similarity

**Difficulty:** intermediate

**Question:**
A learner trains an embedding model and notices that the embedding of "automobile" is
very close to the embedding of "car" in the vector space, but far from the embedding of
"democracy." Explain why the model produces this geometry. What was the model learning
during training that causes this?

**Correct answer criteria:**
- Embedding models learn from context co-occurrence — words that appear in similar contexts
  get pushed toward each other in the embedding space
- "Automobile" and "car" appear in similar contexts (traffic, repair, driving), so their
  vectors converge during training
- "Democracy" appears in entirely different contexts (politics, elections, governance),
  so its vector diverges
- The model is not explicitly programmed with these relationships — they emerge from
  distributional statistics in the training corpus

**Partial credit criteria:**
- Explains that similar words end up close together but attributes it to the model
  "knowing" the definitions rather than learning from context statistics
- Correctly identifies context-based learning but cannot explain the mechanism
  (e.g., does not mention co-occurrence or distributional hypothesis)

**Incorrect / no-credit criteria:**
- Explains it as "the model was told which words are synonyms"
- Claims the model compares dictionary definitions
- Cannot explain what the model was learning at all

---

## Q4 — Embedding model choice and domain shift

**Difficulty:** intermediate

**Question:**
You are building a RAG system for a medical records search tool. Your teammate suggests
using a general-purpose text embedding model trained on web crawl data (like Wikipedia
and news articles). What concerns should you raise, and what alternative would you
recommend?

**Correct answer criteria:**
- Domain shift: a general-purpose model trained on web text will not have learned the
  distributional patterns of medical vocabulary — clinical abbreviations, drug names,
  anatomical terms will not be well-represented
- This leads to poor retrieval quality: a query about "MI" (myocardial infarction) may
  not retrieve records containing "heart attack" or vice versa
- Recommendation: use a medical-domain embedding model (e.g., BioBERT, PubMedBERT) that
  was trained or fine-tuned on clinical or biomedical text
- Optionally: fine-tune a general model on a medical corpus if a domain-specific model
  is unavailable

**Partial credit criteria:**
- Raises the domain mismatch concern but cannot explain why web-trained embeddings
  fail on medical text specifically
- Recommends a domain-specific model but cannot explain what property of that model
  makes it better

**Incorrect / no-credit criteria:**
- Says any embedding model will work equally well as long as the chunks are good
- Recommends using a larger general-purpose model as the solution (size alone does
  not solve domain shift)
- Does not raise any domain-related concerns

---

## Q5 — The curse of dimensionality and embedding scale

**Difficulty:** advanced

**Question:**
A team running a high-volume RAG system is debating whether to upgrade from 768-dimensional
embeddings to 3072-dimensional embeddings to improve retrieval quality. Describe two
specific risks or costs of moving to higher dimensions, and explain the conditions under
which higher-dimensional embeddings actually improve retrieval quality.

**Correct answer criteria:**
- Cost 1: increased memory and storage — a 4x increase in dimensions means 4x more storage
  per vector, which compounds at millions of vectors
- Cost 2: increased compute per similarity search — distance computations scale linearly
  with dimension count, increasing query latency and cost
- (Acceptable alternative cost): The curse of dimensionality — in very high-dimensional
  spaces, distances between all pairs of vectors tend to converge, reducing discriminative
  power (though this affects truly extreme dimensions more than 768→3072)
- Higher dimensions improve retrieval when: the tasks require fine-grained semantic
  distinctions that lower-dimensional models compress out, or when the new model has
  been retrained on a more representative corpus (dimension increase often accompanies
  a better-trained model, so the gains may be from training improvements, not dimensions alone)

**Partial credit criteria:**
- Identifies cost (memory or compute) but only one, not two
- States higher dimensions are always better without qualification
- Notes the tradeoffs but cannot state when the upgrade is actually justified

**Incorrect / no-credit criteria:**
- Claims higher dimensions always reduce retrieval quality
- Says the only cost is "more disk space" without mentioning compute impact
- Cannot identify any conditions under which higher dimensions provide benefit

---

## Q6 — Polysemy and embedding limitations

**Difficulty:** advanced

**Question:**
The word "bank" can mean a financial institution or the side of a river. Explain how this
polysemy (multiple meanings) affects embedding quality in a RAG retrieval scenario, and
describe one technique that partially addresses this limitation.

**Correct answer criteria:**
- Standard word embeddings (non-contextual) collapse multiple meanings into a single
  vector that represents the average of all senses — this reduces precision
- In a RAG scenario, a query about "river bank" might retrieve documents about financial
  institutions because their embeddings are near each other in the averaged space
- Contextual embeddings (like those from transformer models) generate different vectors
  for "bank" depending on its surrounding context — this largely resolves the polysemy
  problem at the sentence level
- Optionally: query rewriting, hypothetical document expansion, or domain-scoped collections
  can reduce polysemy-driven retrieval noise

**Partial credit criteria:**
- Identifies polysemy as a problem but attributes it to all embedding models equally
  (does not distinguish static word embeddings from contextual sentence embeddings)
- Describes contextual embeddings as the fix without explaining what makes them different
  from static embeddings

**Incorrect / no-credit criteria:**
- Claims embeddings handle polysemy perfectly
- Suggests the solution is to rename documents to avoid ambiguous terms
- Cannot identify any technique to address the limitation

---

## Q7 — Comparing embedding spaces across different models

**Difficulty:** advanced

**Question:**
You have two documents. Document A was embedded with Model X, and Document B was embedded
with Model Y (a different embedding model). Can you meaningfully compute cosine similarity
between Document A's vector and Document B's vector? Explain your answer.

**Correct answer criteria:**
- No — embedding vectors from different models are not comparable. Each model defines its
  own vector space with its own axes (learned latent dimensions), which are independent
  across models
- Cosine similarity between cross-model vectors is meaningless: the numerical value
  produced has no interpretable relationship to semantic similarity
- To compare Document A and Document B semantically, both must be re-embedded using the
  same model to ensure they exist in the same vector space
- Practical implication: if you change your embedding model, you must re-embed your entire
  corpus — you cannot partially migrate

**Partial credit criteria:**
- States that cross-model comparison doesn't work but cannot explain why (i.e., cannot
  explain that each model defines its own independent vector space)
- Identifies the re-embedding requirement but presents it as a best practice rather than
  a hard requirement

**Incorrect / no-credit criteria:**
- Claims you can average or normalize the vectors to make them comparable
- Believes that larger dimensions always produce a "universal" space
- Does not identify any problem with comparing cross-model embeddings

---

## Q8 — Embedding normalization and inner product

**Difficulty:** advanced

**Question:**
An engineer tells you: "We use inner product (dot product) instead of cosine similarity
for our vector search — it's faster." Under what conditions is this exactly equivalent
to cosine similarity? What happens to retrieval quality if vectors are not normalized
and you use inner product anyway?

**Correct answer criteria:**
- Inner product equals cosine similarity when all vectors are L2-normalized (unit vectors
  with magnitude = 1.0). In that case, the dot product IS the cosine of the angle
- If vectors are not normalized and inner product is used, vectors with larger magnitudes
  will dominate the ranking regardless of semantic direction — a very long document chunk
  may rank higher than a more semantically relevant shorter chunk simply because its
  embedding has larger magnitude
- Practical implication: if the embedding model does not normalize its outputs, using inner
  product without normalization will degrade retrieval quality and introduce
  length/magnitude bias

**Partial credit criteria:**
- Correctly identifies the normalization equivalence condition but cannot explain the
  failure mode when vectors are not normalized
- Describes the failure mode (magnitude bias) but cannot identify when dot product and
  cosine are equivalent

**Incorrect / no-credit criteria:**
- Claims inner product and cosine similarity are always equivalent
- Says the difference is only a performance optimization with no quality impact
- Cannot identify any condition under which one is preferred over the other

---

## Q9 — Fine-tuning an embedding model vs. using a general-purpose model

**Difficulty:** advanced

**Question:**
Your RAG system has been running for three months using a general-purpose embedding model.
Retrieval RAGAS scores show context_precision = 0.65 and context_recall = 0.71. A teammate
suggests fine-tuning the embedding model on your domain corpus. What specific signals in
your retrieval metrics would indicate that fine-tuning would help, and what risks does
fine-tuning introduce that a general-purpose model does not have?

**Correct answer criteria:**
- Signals that indicate fine-tuning would help:
  1. Context_precision is consistently low (below 0.70) despite good chunking and appropriate
     top-K — this suggests the embedding model's similarity rankings are imprecise in your
     domain, returning semantically related but domain-mismatched documents
  2. Manual inspection of retrieval failures reveals a systematic vocabulary mismatch
     pattern: user queries use domain-specific terminology (abbreviations, product names,
     specialized jargon) while retrieved documents use different vocabulary for the same
     concepts. This is the domain shift signal — the general-purpose model was not trained
     on text where these terms appeared in similar contexts
  3. Embedding visualization (e.g., UMAP) shows your domain's documents clustering poorly
     — relevant documents are not close together in the embedding space
- Risks that fine-tuning introduces:
  1. Catastrophic forgetting: fine-tuning on a narrow domain corpus can degrade the model's
     performance on queries or documents outside that domain. If your corpus grows to include
     broader content, the fine-tuned model may underperform the general model on the new content
  2. Re-indexing requirement: after fine-tuning, the embedding space changes. Every document
     in the vector store must be re-embedded with the new model before it can be queried.
     This is a full re-indexing event — potentially expensive and disruptive
  3. Training data quality dependency: if the fine-tuning corpus is not representative of
     the actual query-document pairs the system will see, fine-tuning can worsen performance.
     Fine-tuning requires positive and negative query-document pairs; constructing these
     from a document corpus alone (without labeled query data) is an approximation

**Partial credit criteria:**
- Identifies the vocabulary mismatch signal but cannot connect it to the specific RAGAS
  metric pattern that reveals it
- Correctly identifies re-indexing as a risk but treats it as a one-time cost rather than
  an ongoing constraint (every future fine-tune requires another full re-index)

**Incorrect / no-credit criteria:**
- Recommends fine-tuning based on low faithfulness scores (faithfulness is a generation
  metric, not a signal for embedding model quality)
- Claims fine-tuning has no risks compared to using a general-purpose model
- Cannot identify any metric signal that would indicate fine-tuning is needed

---

## Q10 — Detecting embedding model drift from your document corpus

**Difficulty:** advanced

**Question:**
Your RAG system uses an embedding model that was state-of-the-art when you deployed it
18 months ago. Your document corpus has grown significantly with new content in emerging
product areas. You do not have labeled test queries. What operational signal would alert
you that your embedding model has drifted from your corpus — meaning it no longer
represents your documents' semantic space well — and how would you act on that signal?

**Correct answer criteria:**
- Signal 1: retrieval latency does not change, but answer quality (measured by proxy
  signals) degrades over time. Track fallback rate ("I don't know" responses or very low
  confidence answers) over rolling 30-day windows. A rising fallback rate against stable
  query volume indicates retrieval is increasingly failing to surface relevant context,
  consistent with drift
- Signal 2: embedding space density check. Periodically embed a sample of recent documents
  and compute their average distance to their nearest neighbors in the existing index. If
  new documents are systematically farther from their nearest neighbors than older documents
  were at index time, the model's embedding space does not accommodate the new vocabulary
  well — new document vectors are landing in sparse, low-density regions of the space
- Signal 3: query-document similarity score distribution. Track the distribution of the
  top-1 cosine similarity score across a sample of queries over time. A downward drift in
  the median top-1 score (i.e., even the best-matching document is matching less strongly)
  indicates the model's representation of queries and documents is diverging
- How to act: first, benchmark the current model against a recently released general-purpose
  model using a small held-out query sample (even without labeled ground truth, you can
  use an LLM-as-judge to prefer one retrieval result over another). If the new model is
  preferred, plan a full re-indexing migration (see shadow index approach)

**Partial credit criteria:**
- Identifies fallback rate as a proxy signal but cannot describe the embedding space
  density check or similarity score distribution method
- Correctly describes two signals but conflates model drift with index staleness (they
  are different problems: staleness is about document content not being in the index;
  drift is about the model's representations no longer fitting the content that is indexed)

**Incorrect / no-credit criteria:**
- Recommends waiting for a full RAGAS evaluation to detect drift (requires labeled data
  the question specifies is unavailable)
- Cannot identify any operational signal that does not require labeled test queries
- Claims embedding model drift is detectable only through direct user feedback

---

## Q11 — Shadow index strategy for embedding model upgrades

**Difficulty:** advanced

**Question:**
You need to upgrade your embedding model from model-v1 to model-v2. Your production
system serves 500 queries per minute and cannot tolerate a retrieval outage or a period
where half the corpus is indexed under model-v1 and half under model-v2. Describe the
shadow index approach for this migration, including what the consistency window looks
like during cutover and when you would declare the migration complete.

**Correct answer criteria:**
- The shadow index approach:
  1. Build a new, separate index (shadow index) using model-v2 on the full corpus while
     the production index (model-v1) continues serving all traffic. The shadow index is
     write-only — no production queries reach it during build
  2. Once the shadow index contains all documents, begin a validation period: run a sample
     of production queries against both indexes in parallel (shadow evaluation). Compare
     the retrieved chunks — measure context_precision and faithfulness on both indexes
     using an LLM evaluator. Do not switch traffic yet
  3. When shadow index quality meets or exceeds the production index quality on the sampled
     queries, perform the cutover: update the retriever to point to the shadow index.
     This is an atomic configuration change — queries shift from model-v1 to model-v2 in
     a single deployment
- The consistency window: during the build phase, new documents being added to the corpus
  must be dual-written to both indexes — added to the model-v1 production index so they
  are retrievable now, and to the model-v2 shadow index so it remains current. Without
  dual-write, the shadow index is stale by the time the build completes
- Declaring migration complete: after cutover, monitor the model-v2 index for 48–72 hours.
  If fallback rate, faithfulness proxy metrics, and query latency are stable or improved,
  decommission the model-v1 index. Until then, keep model-v1 available as a rollback target

**Partial credit criteria:**
- Correctly describes building the shadow index in parallel but does not address the dual-
  write requirement during the build phase (the consistency window problem)
- Identifies the dual-write requirement but proposes a cutover without a validation period,
  making the migration a blind swap

**Incorrect / no-credit criteria:**
- Proposes stopping writes to the production index during the build phase (causes retrieval
  outage or staleness)
- Describes a rolling migration where some queries go to model-v1 and others to model-v2
  simultaneously (produces split-brain retrieval — query results are inconsistent depending
  on which index is hit)
- Cannot identify the consistency window as a problem that requires dual-write

---

## Q12 — What an embedding model produces

**Difficulty:** novice

**Question:**
When you pass a sentence through an embedding model, what does the model return?

**Correct answer criteria:**
- A fixed-length list of numbers (a vector or array of floating-point values)
- The length of the list is determined by the model's architecture (e.g., 384 dimensions,
  768 dimensions, 1536 dimensions) — it is the same length for every input, regardless
  of how long or short the input text is
- The numbers encode the meaning of the input text in a form that allows mathematical
  comparison with other embeddings

**Partial credit criteria:**
- States that the model returns a list of numbers but believes the length varies with
  input length
- Correctly identifies the fixed-length property but describes the output as "keywords"
  or "tokens" rather than floating-point values

**Incorrect / no-credit criteria:**
- Believes the model returns a summary or paraphrase of the text in natural language
- Thinks the model returns a single score (e.g., a relevance score)
- Confuses the embedding output with tokenization (which produces integers, not floats)

---

## Q13 — What "semantic similarity" means for embeddings

**Difficulty:** novice

**Question:**
Two sentences have "high semantic similarity" as measured by their embeddings. What does
this mean in plain terms, and give one example pair that would score high and one that
would score low.

**Correct answer criteria:**
- High semantic similarity means the two sentences carry similar meaning — they could be
  used to express the same idea or answer the same question
- High similarity example: "The store closes at 9 PM" and "The shop shuts at nine in the
  evening" — same meaning, different words
- Low similarity example: "The store closes at 9 PM" and "Photosynthesis converts light
  into energy" — unrelated topics, completely different meaning
- The similarity is captured by how close the two embedding vectors are in the vector space

**Partial credit criteria:**
- Correctly defines semantic similarity but gives only one example (high or low, not both)
- Gives appropriate examples but cannot connect them to what "close in vector space" means

**Incorrect / no-credit criteria:**
- Defines semantic similarity as "exact wording match" (that is lexical similarity, not
  semantic similarity)
- Cannot give any example pair
- Believes only sentences with shared words can have high semantic similarity

---

## Q14 — Why embedding models are trained rather than hand-crafted

**Difficulty:** novice

**Question:**
Why are embedding models trained on large text corpora rather than built by hand with
rules about which words are similar?

**Correct answer criteria:**
- The number of possible word and phrase relationships is too large to define manually —
  language has millions of words, idioms, and domain-specific terms
- Training on large corpora allows the model to discover similarity patterns from actual
  usage — words that appear in similar contexts are learned to have similar embeddings
  automatically
- Training captures relationships that no human could fully enumerate: synonyms, paraphrases,
  domain-specific equivalences, and even stylistic similarity

**Partial credit criteria:**
- States that hand-crafting is impractical due to scale but cannot explain what the
  training process captures instead
- Explains the distributional learning correctly but cannot articulate why scale rules
  out manual approaches

**Incorrect / no-credit criteria:**
- Believes a dictionary or thesaurus could substitute for a trained embedding model
- Claims embedding models are trained because it is faster, not because hand-crafting
  is infeasible at scale
- Cannot identify what property of training produces useful embeddings

---

## Q15 — What happens to the embedding of a very long document

**Difficulty:** novice

**Question:**
Most embedding models have a maximum input length (e.g., 512 tokens). What happens when
you pass a 2,000-token document directly to such a model?

**Correct answer criteria:**
- The model truncates the input — only the first 512 tokens are embedded, and everything
  after the cutoff is silently ignored
- The resulting embedding represents only the beginning of the document, not its full content
- This is why RAG systems split documents into smaller chunks before embedding — to ensure
  each chunk fits within the model's input limit and is fully represented

**Partial credit criteria:**
- Correctly identifies that the model has a limit and the document will be truncated, but
  does not explain that the embedding only represents the truncated portion
- Explains the need for chunking without connecting it to the token limit

**Incorrect / no-credit criteria:**
- Believes the model automatically summarizes the document to fit the limit
- Claims the model returns an error and refuses to process the long input
- Does not identify any consequence of passing an oversized input

**Follow-up probe:**
"If you chunked the document into 400-token pieces, how many embeddings would you produce
from the original 2,000-token document, and how would you store them?"

---

## Q16 — When cosine similarity score is misleading

**Difficulty:** intermediate

**Question:**
You run cosine similarity between a user query and a document chunk and get a score of
0.91 — very high. The document chunk is clearly irrelevant to the query when a human
reads both. Describe two mechanisms that could produce a high cosine similarity score
between two semantically unrelated texts.

**Correct answer criteria:**
- Mechanism 1: domain mismatch in the embedding model — if the embedding model was not
  trained on text in this domain, it may cluster vocabulary in unexpected ways. Technical
  terms from two unrelated domains may land near each other in the embedding space if both
  are rare in the training corpus and the model treats "low-frequency" as a similarity signal
- Mechanism 2: shared surface features without shared meaning — short texts that contain
  common function words (articles, prepositions, connectives) without much content may
  embed similarly because the embedding is dominated by structural rather than semantic
  features. A very short query like "what is the limit?" and a short but unrelated chunk
  may score highly because both have similar function-word patterns
- Acceptable alternative mechanism: if vectors are not properly normalized and the embedding
  model produces high-magnitude vectors for certain text types, inner product (if used
  instead of true cosine similarity) can inflate scores for those texts regardless of meaning

**Partial credit criteria:**
- Identifies one valid mechanism with a concrete example but cannot identify a second
- States that domain mismatch can cause false positives but does not explain the mechanism
  (what the model does wrong)

**Incorrect / no-credit criteria:**
- Claims a high cosine similarity score always indicates semantic relevance
- Attributes the false positive only to "the model being wrong" without explaining the
  specific mechanism
- Cannot describe any condition under which cosine similarity produces a misleading result

---

## Q17 — The difference between embedding a query and embedding a document chunk

**Difficulty:** intermediate

**Question:**
Should you use the same embedding model to embed user queries and document chunks in a
RAG system? What breaks if you embed queries with one model and document chunks with
a different model?

**Correct answer criteria:**
- Yes — queries and document chunks must be embedded with the same model. They must share
  the same vector space for cosine similarity to be meaningful
- If different models are used: each model defines its own coordinate system with its own
  learned dimensions. A query vector from Model A and a document vector from Model B exist
  in different spaces. Cosine similarity between them produces a number that has no
  relationship to semantic similarity — retrieval becomes effectively random
- Some embedding models use asymmetric encoding (separate encoder weights for queries vs.
  documents, as in Cohere's models or bi-encoder rerankers). These are designed for this
  purpose — both encoders still map into the same shared vector space. This is not the
  same as using two completely different models.

**Partial credit criteria:**
- Correctly states that the same model must be used for both but cannot explain why
  (cannot explain the incompatible vector spaces concept)
- Identifies the failure mode (retrieval becomes random) but does not explain the mechanism

**Incorrect / no-credit criteria:**
- Believes different models can be used as long as they have the same embedding dimension
- Claims the problem can be solved by normalizing vectors from both models
- Cannot identify any consequence of using mismatched embedding models
