# Question Bank: `embeddings_and_similarity`
# Phase: 1 — Foundations
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-11 (Commit 22)

---

## Q1 — What is a vector embedding?

**Difficulty:** beginner

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
