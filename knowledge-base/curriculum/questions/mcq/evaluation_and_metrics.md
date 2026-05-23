# MCQ Bank — evaluation_and_metrics
# Topic: evaluation_and_metrics
# Phase: 3 (Production)
# Questions: 12 (2 novice, 4 intermediate, 4 advanced, 2 expert)
# Last updated: 2026-05-21 (Commit 45)

---

## MCQ-1 — RAGAS faithfulness definition

**Difficulty:** novice
**Topic:** evaluation_and_metrics

**Question:**
What does the RAGAS metric "faithfulness" measure in a RAG system?

**Options:**
A. How well the retrieved chunks match the user's question
B. The fraction of claims in the generated answer that are supported by the retrieved context
C. How closely the generated answer matches a human-written reference answer
D. The proportion of relevant documents in the corpus that were successfully retrieved

**Correct answer:** B

**Explanation:**
Faithfulness measures whether the claims the LLM makes in its answer are attributable to the retrieved passages. A faithful answer contains no information the LLM invented beyond what the context supports.

**Why A is wrong:** Option A describes context precision or recall — how well the retrieved chunks match or cover the query. This is a retrieval quality metric, not a generation quality metric. Practitioners new to RAGAS often conflate "faithful" with "retrieved well," conflating the two evaluation stages.

**Why C is wrong:** Comparing to a human-written reference answer describes answer correctness or answer similarity — a different RAGAS metric that requires ground truth. Faithfulness does not require a reference answer at all; it only compares the generated answer against the retrieved context.

**Why D is wrong:** The proportion of relevant documents retrieved describes recall (coverage). This is measured at the retrieval stage and has nothing to do with whether the LLM's generation stays within the bounds of what was retrieved.

---

## MCQ-2 — Context precision definition

**Difficulty:** novice
**Topic:** evaluation_and_metrics

**Question:**
What does "context precision" measure in RAG evaluation?

**Options:**
A. The fraction of retrieved chunks that are actually relevant to answering the query
B. The fraction of information needed to answer the query that is present in the retrieved chunks
C. The accuracy of the embedding model at ranking the top-1 result above all others
D. The percentage of the retrieved context that the LLM uses in its final answer

**Correct answer:** A

**Explanation:**
Context precision measures retrieval quality from the perspective of signal-to-noise: of all the chunks returned, how many were relevant? A high-precision retrieval returns mostly useful chunks. Option B describes context recall — the coverage metric. Option C describes ranking accuracy, which is a retrieval evaluation but not RAGAS context precision. Option D measures LLM utilization of context, not retrieval precision.

---

## MCQ-3 — Low faithfulness vs. low context recall

**Difficulty:** intermediate
**Topic:** evaluation_and_metrics

**Question:**
A RAG system scores 0.45 on faithfulness and 0.90 on context recall. What is the most likely diagnosis?

**Options:**
A. The retrieval step is poor — it is not returning the documents the LLM needs to answer accurately
B. The LLM is generating content beyond what the retrieved context supports, rather than staying grounded — retrieval quality is good but the LLM is hallucinating
C. The chunking strategy is too coarse — large chunks contain irrelevant information that confuses the LLM
D. The embedding model is mismatched between indexing and query time, producing semantically incorrect retrievals

**Correct answer:** B

**Explanation:**
High context recall (0.90) means the retrieval step is returning the information needed to answer the question — the right content is in the retrieved set. Low faithfulness (0.45) means the LLM's generated answer contains claims not supported by that context. The fault is in the generation stage: the LLM is confabulating details beyond the grounding provided.

**Why A is wrong:** A retrieval problem would manifest as low context recall, not low faithfulness. A practitioner might choose A because they assume faithfulness and recall are correlated — they are not. Recall measures whether the right content was retrieved; faithfulness measures whether the LLM stayed within that content after receiving it. With 0.90 recall, retrieval is working.

**Why C is wrong:** Coarse chunking dilutes embedding signals and typically degrades context precision (too much noise per chunk) or context recall (concepts split across boundaries). It does not directly cause the LLM to generate ungrounded claims. A practitioner who conflates retrieval noise with generation hallucination makes this error.

**Why D is wrong:** Embedding model mismatch causes retrieval to degrade significantly — you would expect context recall well below 0.90, likely near 0.20–0.40 with near-random retrieval. A 0.90 recall score eliminates this hypothesis. This distractor catches practitioners who jump to infrastructure explanations before reading the metrics carefully.

---

## MCQ-4 — Offline vs. online evaluation

**Difficulty:** intermediate
**Topic:** evaluation_and_metrics

**Question:**
A team has a labeled evaluation dataset of 200 query/expected-answer pairs. They use this to measure RAGAS scores before each production deployment. A colleague argues this is insufficient and suggests adding online evaluation via user feedback signals. Which statement correctly describes the complementary roles of offline and online evaluation?

**Options:**
A. Offline evaluation is more accurate; online evaluation should only be used when a labeled dataset is unavailable
B. Offline evaluation measures quality on a fixed benchmark — good for catching regressions before deployment; online evaluation captures real user query distributions and failure patterns that may not appear in the benchmark
C. Online evaluation is superior because it measures real behavior; offline evaluation only confirms the system performs well on training data
D. Offline evaluation requires human annotators; online evaluation is fully automated and therefore preferred for continuous monitoring

**Correct answer:** B

**Explanation:**
Offline evaluation (benchmark datasets) is essential for reproducible regression testing — you can compare system versions on the same queries before deploying. Online evaluation captures the actual query distribution, user satisfaction, and failure modes that only emerge in production (e.g., queries your benchmark never anticipated). Neither replaces the other: offline evaluation gates deployments; online evaluation surfaces systemic issues after deployment.

**Why A is wrong:** Neither mode is simply "more accurate" — they measure different things. Offline evaluation is precise and reproducible; online evaluation is representative of real usage. A practitioner might choose A if they over-trust their benchmark set and dismiss the value of production signals.

**Why C is wrong:** This reverses the failure mode: offline evaluation uses a held-out test set, not training data. Conflating evaluation data with training data is a data contamination concern, not an inherent property of offline evaluation. A practitioner might choose C after reading criticisms of static benchmarks and overcorrecting.

**Why D is wrong:** Online evaluation typically requires human sampling and review — for example, sampling 50 queries per day and having a human evaluate faithfulness. Automated online evaluation exists (LLM-as-judge on production traffic) but it is not the defining characteristic. The claim that "fully automated" makes it preferred is also false — automation introduces its own scoring noise.

---

## MCQ-5 — Answer correctness vs. faithfulness tradeoff

**Difficulty:** advanced
**Topic:** evaluation_and_metrics

**Question:**
A RAG system achieves faithfulness = 0.92 and answer correctness = 0.61. A second system achieves faithfulness = 0.71 and answer correctness = 0.84. Which statement most precisely characterizes the tradeoff and the appropriate production decision?

**Options:**
A. System 1 is better — faithfulness is more important than correctness because hallucination is a safety risk
B. System 2 is better — answer correctness directly measures whether users get right answers, which is the ultimate goal
C. The two systems represent different failure modes: System 1 is constrained but retrieval-limited (faithful but often incomplete or wrong because it only uses what it retrieved); System 2 is more capable but less grounded (often correct but sometimes fabricates). The right choice depends on the use case's tolerance for hallucination vs. incomplete answers
D. System 1 should be used for regulated industries; System 2 for consumer products — there is no universally correct choice

**Correct answer:** C

**Explanation:**
Faithfulness and answer correctness measure different failure modes. A system with high faithfulness but low correctness is grounded in retrieved context but may be providing incomplete or wrong answers because the retrieved context was insufficient — it will not make things up, but it will fail to fully answer. A system with high correctness but lower faithfulness may be drawing on parametric knowledge to supplement weak retrieval — getting the right answer more often, but with a higher hallucination risk when it does confabulate.

**Why A is wrong:** Hallucination risk depends on context, not on an absolute ranking of metrics. A practitioner who works primarily in high-stakes domains might reflexively choose A without considering whether correctness is also a safety concern — an incomplete answer can be as dangerous as a fabricated one. The statement is too categorical.

**Why B is wrong:** "Answer correctness" is meaningful only when you have ground truth to compare against. More importantly, a system that is correct 84% of the time but fabricates information on the other 16% is not simply "better" — the 16% fabrication represents a trust-destroying failure mode. A practitioner who optimizes for a single metric without understanding the failure mode distribution chooses B.

**Why D is wrong:** Option D is a partial insight — industry context does matter. But the logic underlying the decision is the hallucination-vs-incompleteness tradeoff, which applies within any industry. Framing it as a simple industry rule misses the reasoning a practitioner needs to make the decision themselves when industry classification is ambiguous.

---

## MCQ-6 — LLM-as-judge evaluation bias

**Difficulty:** intermediate
**Topic:** evaluation_and_metrics

**Question:**
A team evaluates their RAG system using GPT-4 as the judge model to score faithfulness and answer relevancy. Their faithfulness scores are consistently higher than expected based on manual inspection. What is the most likely cause?

**Options:**
A. GPT-4 scores too conservatively — it penalizes answers that are technically correct but phrased differently from the context
B. GPT-4 exhibits a self-consistency bias — it tends to rate answers generated by similar LLMs as more faithful than a human judge would, because it shares their generation tendencies and does not recognize subtle hallucinations as errors
C. The evaluation dataset is too small — with fewer than 500 queries, GPT-4 cannot calibrate its scores accurately
D. GPT-4 has a higher context window than the generation model, so it can process more context than the original system, inflating faithfulness scores

**Correct answer:** B

**Explanation:**
LLM-as-judge evaluation has well-documented biases. When the judge model and the generation model share similar training data and generation tendencies, the judge tends to recognize and accept the same patterns it would itself generate — including subtle hallucinations that a human reader would flag. This is the self-consistency (or model-family) bias. Teams that use the same model (or same model family) to both generate and evaluate will systematically overestimate faithfulness.

**Why A is wrong:** GPT-4 generally skews toward leniency in scoring, not conservatism. The documented failure mode in production is inflated scores, not deflated ones. A practitioner who has only heard about benchmark leaderboard inflation might guess A, but the direction of the bias is inverted.

**Why C is wrong:** Dataset size affects variance (reliability of the mean score), not systematic directional bias. A small dataset produces noisy scores that could be high or low. The problem described — consistent inflation — is a systematic bias, not a variance problem. A practitioner who conflates statistical reliability with accuracy chooses C.

**Why D is wrong:** Context window size affects what the judge can read during evaluation, but faithfulness scoring is performed per-claim against the retrieved context, not against some additional context the generation model lacked. The judge's context window advantage does not inflate faithfulness scores — it would affect completeness of evaluation, not directional bias in faithfulness scoring.

---

## MCQ-7 — RAGAS answer relevancy computation

**Difficulty:** intermediate
**Topic:** evaluation_and_metrics

**Question:**
RAGAS computes "answer relevancy" without a ground truth answer. What is the mechanism it uses to score this metric?

**Options:**
A. It computes the semantic similarity between the generated answer and the original query using an embedding model
B. It uses an LLM to generate multiple synthetic questions from the generated answer, then measures how similar those questions are to the original query — answers that consistently generate questions similar to the original query score high
C. It extracts named entities from both the answer and the query and computes their overlap ratio
D. It compares the answer's token length to the average answer length in the evaluation dataset to detect under-answering

**Correct answer:** B

**Explanation:**
RAGAS answer relevancy is computed by reverse-engineering: given the generated answer, an LLM is asked to generate N hypothetical questions that this answer would address. The cosine similarity between those hypothetical questions and the original query is averaged as the relevancy score. An answer that contains relevant information will generate questions close to the original; an off-topic or rambling answer generates questions dissimilar to the original. This approach does not require a reference answer.

**Why A is wrong:** Direct query-answer similarity using embeddings is a simpler approach that RAGAS does not use, because it conflates length and surface similarity with relevancy. A short, direct answer to the question and a long, rambling answer mentioning the same terms could score similarly under option A. A practitioner familiar with semantic search but not RAGAS's specific implementation chooses this.

**Why C is wrong:** Named entity overlap is a recall-style metric more suited to information extraction evaluation. It misses the case where an answer is semantically on-topic but uses different entities, and it penalizes appropriate paraphrase. Practitioners with NLP background might reach for this pattern.

**Why D is wrong:** Answer length as a proxy for quality is not a RAGAS metric — it would punish concise, correct answers and reward verbose, padded ones. This distractor captures practitioners who conflate "complete" with "long" when reasoning about evaluation.

---

## MCQ-8 — Context recall requiring ground truth

**Difficulty:** advanced
**Topic:** evaluation_and_metrics

**Question:**
A team wants to add context recall to their evaluation suite but discovers they do not have ground truth contexts (the passages that should have been retrieved). They propose using LLM-generated synthetic contexts as a substitute. What is the precise risk of this approach?

**Options:**
A. Synthetic contexts generated by an LLM will contain hallucinations, making them unusable as evaluation references
B. If the LLM generates synthetic contexts from the same documents that are in the index, the synthetic contexts will match the index perfectly and context recall will always score near 1.0, making the metric uninformative
C. Context recall requires exact string match between retrieved and ground truth contexts — LLM-generated paraphrases will never match even when the retrieval is correct
D. Using LLM-generated contexts creates a circular dependency: the system being evaluated may have been used to generate the synthetic ground truth, so the evaluation becomes self-referential and systematically biased toward systems with high coverage

**Correct answer:** D

**Explanation:**
If the same RAG system (or a similar one) generates synthetic ground truth contexts by asking "what passages should answer this query?" and then also answers queries using those passages, the evaluation becomes self-referential. The system is evaluated on how well it retrieves what it itself defined as the relevant context — not on whether the defined context was actually correct or complete. This inflates scores for the generating system and biases comparisons against alternative systems.

**Why A is wrong:** LLM hallucination is a real concern for synthetic ground truth, but it does not make the approach categorically unusable — it is a quality management problem, not a structural invalidity. RAGAS's own test set generation uses LLMs and includes validation steps. A practitioner who reflexively avoids LLM-generated data chooses A.

**Why B is wrong:** This describes a real problem (document-sourced synthetic contexts scoring high) but misidentifies the mechanism. Context recall measures whether the retrieved chunks contain the necessary information, not whether they are verbatim matches to ground truth. Even perfect document-sourced contexts would not guarantee a score near 1.0 if the retrieval system fails to return them. This option confuses "recall nearly always high" with "metric always near 1.0."

**Why C is wrong:** RAGAS context recall does not use exact string matching — it uses an LLM evaluator to check whether each statement in the ground truth answer is supported by the retrieved context. Paraphrase and semantic equivalence are handled. This misconception comes from conflating keyword-based evaluation (F1 on tokens) with RAGAS's LLM-based approach.

---

## MCQ-9 — Diagnosing high precision / low recall

**Difficulty:** advanced
**Topic:** evaluation_and_metrics

**Question:**
A RAG system consistently scores context_precision = 0.88 and context_recall = 0.41 across 300 evaluation queries. Which diagnosis is most operationally precise and which single change would most directly address the root cause?

**Options:**
A. The LLM is summarizing retrieved chunks too aggressively, losing information before faithfulness is computed. Fix: disable answer summarization
B. The retrieval is precise but narrow — the top-K returned chunks are highly relevant but the system is missing a large portion of the content needed to answer correctly. Fix: increase top-K or broaden retrieval to surface more relevant chunks
C. The embedding model is producing high-magnitude vectors that cluster tightly, reducing diversity in ANN results. Fix: normalize vectors before indexing
D. The RAGAS evaluation dataset has low-quality ground truth contexts, artificially deflating context recall. Fix: rebuild the evaluation dataset

**Correct answer:** B

**Explanation:**
Context precision = 0.88 means the chunks that are returned are almost all relevant — retrieval is accurate when it does return something. Context recall = 0.41 means that 59% of the information needed to answer the question is not present in the retrieved set — the system is returning the right kind of content but not enough of it. The root cause is coverage failure: top-K is too small, the chunking strategy is splitting relevant content so it falls below the top-K cutoff, or the embedding space does not capture all relevant formulations of the answer. Increasing top-K is the most direct first fix.

**Why A is wrong:** Faithfulness and context recall are computed independently in RAGAS. Summarization by the LLM affects faithfulness (whether the answer stays within context) but not context recall (which is computed directly from the retrieved chunks against ground truth, before the LLM generates an answer). A practitioner who conflates generation-stage issues with retrieval-stage metrics chooses A.

**Why C is wrong:** Vector magnitude and normalization affect whether dot product and cosine are equivalent — but they do not cause the specific pattern of high precision with low recall. Normalization is a metric equivalence concern, not a recall-precision tradeoff driver. A practitioner who remembers the normalization lecture but cannot connect it to the actual symptom chooses C.

**Why D is wrong:** Low-quality ground truth would produce noisy scores in both directions, not a consistent systematic pattern across 300 queries. A consistently low recall with high precision on a large evaluation set is a reliable signal about the system, not about the dataset. A practitioner who defaults to blaming the evaluation data when scores are unexpectedly low chooses D.

---

## MCQ-10 — Metric stability under query distribution shift

**Difficulty:** expert
**Topic:** evaluation_and_metrics

**Question:**
A production RAG system has been stable at faithfulness = 0.83 for six months. After a marketing campaign, query volume doubles and the query distribution shifts significantly (new user segments asking questions the original corpus handles poorly). Faithfulness drops to 0.71. What is the most precise interpretation, and what is the correct diagnostic first step?

**Options:**
A. The LLM API is experiencing degradation — double query volume stresses the inference endpoint, causing truncated responses. First step: check LLM API error rates and response latency
B. The faithfulness drop reflects real quality degradation caused by distribution shift — the new queries expose gaps between the current corpus/retrieval strategy and the new user needs. First step: segment faithfulness scores by user cohort or query topic to identify which query types are failing
C. The evaluation pipeline itself is under load stress — RAGAS metrics become less accurate at higher query volumes. First step: reduce the evaluation sample rate to maintain metric accuracy
D. Faithfulness drift of 0.12 points over a volume doubling is within normal variance and should not trigger investigation. First step: collect 30 more days of data before acting

**Correct answer:** B

**Explanation:**
A sustained metric drop coinciding with a documented distribution shift is a strong signal of real quality degradation, not instrumentation noise. The correct diagnostic is to decompose the aggregate metric: segment faithfulness by query topic, user segment, or time slice to identify which new query patterns are driving the drop. This tells you whether the problem is corpus coverage (the corpus has no content for the new topics), embedding model alignment (the new queries phrase things in ways the embedding model handles poorly), or retrieval precision (new topics have noisy overlapping content).

**Why A is wrong:** LLM API degradation under load would manifest as latency spikes, error rate increases, and truncated responses — these would affect all queries equally, not specifically the queries introduced by the new user segment. This distractor catches practitioners who jump to infrastructure explanations before looking at query-level data.

**Why C is wrong:** RAGAS evaluation computes per-claim scoring using an LLM evaluator — the accuracy of scoring does not degrade with sample volume. The evaluator processes each query independently. Load stress on the evaluation pipeline is an operational concern (evaluation takes longer), not a metric accuracy concern. This distractor catches practitioners who conflate evaluation system performance with evaluation metric validity.

**Why D is wrong:** A 0.12-point drop (from 0.83 to 0.71) in faithfulness is a 14% relative degradation — significant by any production quality standard. "Wait 30 more days" is the wrong response when a known causal event (distribution shift from the campaign) provides a plausible immediate explanation. This distractor catches practitioners who confuse statistical significance thresholds with operational significance thresholds.

---

## MCQ-11 — Evaluation metric sensitivity to chunk count

**Difficulty:** expert
**Topic:** evaluation_and_metrics

**Question:**
A team is comparing two retrieval configurations: Config A retrieves top-3 chunks; Config B retrieves top-10 chunks. All other pipeline components are identical. They run RAGAS evaluation and find Config A has higher context_precision but lower context_recall than Config B. They report Config B is "better" because its RAGAS composite score is higher. What is wrong with this conclusion?

**Options:**
A. RAGAS composite scores weight all metrics equally, which is incorrect — precision matters more than recall for answer quality
B. The comparison conflates retrieval configuration differences with quality differences. A higher top-K will mechanically increase context_recall because more chunks are retrieved, but this does not mean the system produces better answers — the additional chunks may be noise that degrades generation quality even if RAGAS does not capture this
C. The evaluation dataset is biased — all RAGAS test queries were generated from documents that appear in Config B's additional retrieved chunks, making Config B's recall artificially high
D. The two configurations have different latency profiles, and RAGAS does not account for latency — Config B's higher score may not be worth the additional retrieval cost

**Correct answer:** B

**Explanation:**
Context recall mechanically increases as top-K increases — more chunks means more information present in the retrieved set. But more retrieved content also means more noise injected into the LLM prompt, which can degrade faithfulness and answer quality in ways RAGAS metrics may not fully capture (especially if the evaluation set is small or the LLM handles noise gracefully on the test queries). The correct comparison isolates retrieval precision as a quality signal, not recall-as-maximized-by-volume. A rigorous evaluation would also measure faithfulness and end-to-end answer quality under both configurations.

**Why A is wrong:** There is no universal rule that precision outweighs recall — the relative importance depends on the use case. A high-stakes system may prioritize recall (not missing relevant content) while a cost-sensitive system prioritizes precision (fewer wasted tokens). This option is false as a general claim.

**Why C is wrong:** Evaluation dataset bias is possible but requires evidence — it should not be assumed when a simpler structural explanation exists. The structural explanation (top-K mechanically increases recall) is the more parsimonious and common diagnosis. This distractor catches practitioners who over-index on dataset quality concerns.

**Why D is wrong:** Latency and cost differences are real operational concerns, but the claim in the question is about quality ("better"). Option D introduces a valid secondary concern without addressing the fundamental flaw in the comparison logic. This is a partial answer, not a wrong answer — but it does not identify the core methodological error.

---

## MCQ-12 — Detecting silent score inflation in LLM-as-judge pipelines

**Difficulty:** expert
**Topic:** evaluation_and_metrics

**Question:**
A team uses an LLM-as-judge pipeline to score faithfulness continuously in production. After six months, they notice scores have drifted upward by 0.08 points while user satisfaction (from thumbs up/down) has stayed flat. What is the most likely explanation and the correct action?

**Options:**
A. User satisfaction signals are noisy — thumbs up/down ratings are not reliable indicators of actual answer quality. The LLM judge is more reliable and the score drift reflects genuine improvement
B. The LLM judge has been silently updated (model version upgrade by the API provider), shifting its scoring calibration. The team should establish judge model version pinning and recalibrate scores against a fixed human-annotated baseline
C. The production query distribution has shifted toward easier queries that the system handles better, raising average faithfulness without changing satisfaction because users rate easy and hard queries the same way
D. Faithfulness naturally increases over time as the LLM learns from production traffic. The 0.08-point increase is expected and does not require investigation

**Correct answer:** B

**Explanation:**
LLM API providers routinely update their models without announcing breaking changes in evaluation behavior. A GPT-4 model in December may score faithfulness systematically differently from the same endpoint in June — not because the RAG system changed, but because the judge's scoring calibration shifted. Score drift that is not accompanied by any pipeline change and not reflected in user satisfaction signals is a strong indicator of judge model drift. The correct mitigation is judge model version pinning (using a specific model snapshot, not a rolling alias like "gpt-4-turbo") and periodic recalibration against a fixed human-annotated anchor set.

**Why A is wrong:** User satisfaction signals are noisy for any individual query but are reliable aggregated over thousands of interactions. When aggregate satisfaction stays flat while an automated metric rises, the automated metric is the more likely culprit — not the other direction. A practitioner who trusts the LLM judge over human signals makes this error.

**Why C is wrong:** Query distribution shift could explain the pattern, but this hypothesis needs to be tested (e.g., by looking at query topic distributions over the six months). The silent judge model update explanation is more parsimonious because API providers update models frequently without notification. Option C is not impossible but requires more evidence before accepting it over B.

**Why D is wrong:** LLM API deployments do not "learn from production traffic" in real-time inference mode. The model weights are fixed at deployment time. This misconception about continual learning in production LLMs is common among practitioners who know that ML models improve with more data but do not understand the deployment architecture of API-served models.

