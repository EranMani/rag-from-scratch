# Question Bank: `evaluation_and_metrics`
# Phase: 3 — Production
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-11 (Commit 22)

---

## Q1 — RAGAS framework overview

**Difficulty:** novice

**Question:**
Name the four core metrics in the RAGAS evaluation framework. For each, state in one
sentence what it measures and which pipeline stage it evaluates.

**Correct answer criteria:**
1. Faithfulness — measures whether the generated answer is factually consistent with
   the retrieved context (no claims made that are not supported by the context).
   Evaluates the generation stage.
2. Answer Relevancy — measures how well the generated answer addresses the user's
   question (even if it is faithful to the context, is it actually answering what
   was asked?). Evaluates the generation stage (and implicitly retrieval quality).
3. Context Precision — measures how much of the retrieved context is actually relevant
   to answering the question (signal-to-noise in retrieval). Evaluates the retrieval
   stage.
4. Context Recall — measures how much of the information needed to answer the question
   is present in the retrieved context (coverage of retrieval). Evaluates the retrieval
   stage.

**Partial credit criteria:**
- Names all four metrics with correct definitions but misattributes one to the wrong
  pipeline stage
- Correctly attributes all to the right stage but provides imprecise definitions for
  two or more

**Incorrect / no-credit criteria:**
- Cannot name more than two of the four metrics
- Confuses faithfulness with answer relevancy (one is about factual grounding, the other
  about question-answering relevance)
- Describes RAGAS as an LLM evaluation framework (it is specifically for RAG pipelines)

---

## Q2 — Faithfulness in depth

**Difficulty:** novice

**Question:**
Explain faithfulness as a RAGAS metric. How is it computed, and give a concrete example
of a generation that scores 0.0 on faithfulness despite retrieving correct context.

**Correct answer criteria:**
- Faithfulness = the fraction of claims in the generated answer that are attributable
  to the retrieved context. Computed by: (1) decomposing the answer into atomic claims,
  (2) checking each claim against the context using an LLM evaluator, (3) scoring
  supported_claims / total_claims
- A score of 0.0 means none of the answer's claims can be found in the context
- Concrete example of 0.0 faithfulness despite correct context: the retrieved context
  states "Product X was released in 2019." The LLM generates "Product X was released
  in 2021 and won multiple industry awards." Both claims are wrong/unsupported — the
  LLM hallucinated despite having the correct context available. Faithfulness = 0/2 = 0.0

**Partial credit criteria:**
- Correctly explains faithfulness and the computation method but gives an example
  of low (e.g., 0.5) rather than zero faithfulness
- Gives a correct zero-faithfulness example but cannot describe the computation method

**Incorrect / no-credit criteria:**
- Confuses faithfulness with factual accuracy against ground truth (faithfulness
  measures consistency with retrieved context, not with real-world truth)
- Cannot give an example of a faithfulness failure
- Describes faithfulness as binary (pass/fail) rather than a continuous score

---

## Q3 — Context precision vs. context recall

**Difficulty:** intermediate

**Question:**
You have a RAG system that retrieves 10 chunks for every query. A RAGAS evaluation
shows context precision = 0.3 and context recall = 0.9. Interpret these scores: what
do they tell you about the retrieval stage, and what would you change?

**Correct answer criteria:**
- Context precision = 0.3: only 30% of the retrieved chunks are actually relevant to
  answering the question — 7 out of 10 retrieved chunks are noise. The retrieval is
  over-retrieving irrelevant content.
- Context recall = 0.9: 90% of the information needed to answer the question is present
  in the retrieved chunks — retrieval coverage is excellent.
- Interpretation: retrieval is casting a wide net that catches most relevant content
  (high recall) but also pulls in a lot of irrelevant material (low precision).
  This wastes context window tokens, introduces noise for the LLM, and increases cost.
- What to change:
  1. Reduce top-K (retrieve fewer chunks — precision will improve as low-ranked,
     irrelevant chunks are dropped, though recall may decrease slightly)
  2. Add a reranker to re-score the top-10 and select only the top-5 highest-scoring
     chunks before injection
  3. Improve chunking to ensure chunks are more focused units of meaning

**Partial credit criteria:**
- Correctly interprets one metric but not the other
- Correctly interprets both metrics but proposes only one improvement

**Incorrect / no-credit criteria:**
- Interprets high recall as a problem (it is not — the relevant information is present)
- Recommends changing the LLM rather than the retrieval stage based on these scores
- Cannot interpret what 0.3 precision means in concrete terms

**Follow-up probe:**
"If you reduced top-K from 10 to 3 to fix the precision problem, what RAGAS metric
would most likely worsen, and why?"

---

## Q4 — Constructing a RAGAS evaluation dataset

**Difficulty:** intermediate

**Question:**
You need to evaluate your RAG system before deploying to production. RAGAS requires
a test dataset. Describe the three components of a RAGAS test example, explain why
ground truth quality matters, and list one practical method for constructing ground
truth at scale.

**Correct answer criteria:**
- Three components of a RAGAS test example:
  1. Question — the user query
  2. Ground truth contexts — the passages from the knowledge base that should be
     retrieved to answer this question (used to compute context recall)
  3. Ground truth answer — the correct answer to the question (used as reference for
     answer relevancy and faithfulness evaluation)
- Why ground truth quality matters: if ground truth contexts are wrong (they don't
  actually contain the answer), context recall will be miscalculated — you may think
  retrieval is failing when it is correct, or vice versa. If ground truth answers are
  vague or incomplete, RAGAS scores are noisy and unreliable.
- Practical method for constructing at scale:
  1. LLM-generated synthetic data: use an LLM to generate (question, answer) pairs
     from each document chunk. This is fast and scalable but requires human sampling
     to verify quality. (RAGAS itself includes a test set generator for this.)
  2. (Acceptable alternative): Mine from existing support tickets, FAQ pages, or
     historical query logs — real user questions with human-verified answers.

**Partial credit criteria:**
- Lists the three components but explains only one in depth
- Describes ground truth quality importance but cannot describe a concrete construction
  method

**Incorrect / no-credit criteria:**
- Describes only two of three required components
- Claims any LLM output is a valid ground truth answer without validation
- Cannot identify why ground truth quality affects metric reliability

---

## Q5 — Offline vs. online evaluation

**Difficulty:** intermediate

**Question:**
Distinguish offline evaluation from online evaluation for a RAG system. When is each
actionable, and what signal does each provide that the other cannot?

**Correct answer criteria:**
- Offline evaluation: run the system against a labeled test set with ground truth
  answers and contexts before or outside of production. Produces RAGAS scores
  (faithfulness, answer relevancy, context precision/recall). Actionable for:
  pre-deployment validation, A/B testing pipeline changes, regression testing.
- Online evaluation: monitor production traffic — user ratings (thumbs up/down), click-
  through on cited sources, session length, fallback rate (how often the system says
  "I don't know"). Actionable for: monitoring live quality drift, identifying new query
  types not covered by the test set, detecting index staleness impact.
- What offline provides that online cannot: controlled, reproducible measurements.
  You can isolate retrieval vs. generation quality, run the same query 100 times,
  and compare configurations scientifically.
- What online provides that offline cannot: real query distribution. The test set is
  a sample — production reveals edge cases, multi-turn behavior, query volume patterns,
  and user satisfaction signals that no test set captures.

**Partial credit criteria:**
- Correctly defines both but cannot articulate what unique signal each provides
- Identifies unique signals for one direction but not both

**Incorrect / no-credit criteria:**
- Claims offline evaluation is sufficient for production monitoring
- Cannot distinguish the two evaluation paradigms
- Describes online evaluation as simply "running RAGAS on production data"

---

## Q6 — Evaluating retrieval independent of generation

**Difficulty:** intermediate

**Question:**
Why is it important to evaluate retrieval quality separately from generation quality?
Describe a scenario where overall answer quality is poor, but the cause is in the
generation stage rather than retrieval, and explain how you would distinguish the two.

**Correct answer criteria:**
- Importance of separate evaluation: if you only evaluate the final answer, you cannot
  distinguish a retrieval failure (wrong chunks) from a generation failure (correct chunks,
  wrong answer). Without this distinction, you may "fix" the wrong stage — e.g., switching
  embedding models when the real problem is the prompt template.
- Scenario: the retrieved chunks contain the complete, correct information to answer the
  question. The LLM's answer is still wrong because it misread a numerical value in the
  context or hallucinated a detail not present in the chunks.
  - Context recall = 1.0 (all needed information is in the chunks)
  - Context precision = 0.9 (mostly relevant chunks)
  - Faithfulness = 0.4 (many claims are not supported by context — generation failure)
- How to distinguish: inspect the retrieved chunks directly. If the correct answer is
  present in the chunks but absent from the generated response — generation failure.
  If the correct answer is absent from the chunks — retrieval failure.

**Partial credit criteria:**
- Describes the importance of separate evaluation but cannot give a concrete scenario
  with specific RAGAS scores
- Gives a correct scenario but describes the diagnostic procedure imprecisely

**Incorrect / no-credit criteria:**
- Claims you only need to evaluate the final answer quality
- Cannot construct a scenario where retrieval is correct but generation fails
- Confuses the RAGAS metric that indicates generation failure (faithfulness) with
  retrieval metrics (context precision/recall)

---

## Q7 — Interpreting RAGAS scores in context

**Difficulty:** advanced

**Question:**
A team reports their RAG system achieves faithfulness = 0.85, answer relevancy = 0.82,
context precision = 0.70, context recall = 0.65. The system serves medical triage queries.
Evaluate whether these scores are acceptable for this use case, and identify which metric
most urgently needs improvement.

**Correct answer criteria:**
- Medical triage is a high-stakes domain where errors have serious patient safety consequences.
  Acceptable score thresholds are higher than for general-purpose systems.
- Context recall = 0.65 is the most urgent concern: only 65% of the information needed
  to answer triage questions is present in the retrieved context. In a medical context,
  missing 35% of relevant information is dangerous — the LLM is answering with incomplete
  context, which may produce guidance that omits critical contraindications, dosing limits,
  or safety warnings.
- Faithfulness = 0.85 means 15% of claims in the answer are not supported by context —
  this is also concerning for medical use, but context recall is the more foundational
  problem (can't generate correctly from incomplete context).
- Answer relevancy = 0.82 and context precision = 0.70 are secondary concerns in this domain.
- The learner should recognize that absolute score thresholds are domain-dependent:
  0.85 faithfulness that is "fine" for a product FAQ is insufficient for medical guidance.

**Partial credit criteria:**
- Correctly identifies context recall as the most urgent metric but does not apply
  domain-specific reasoning to justify the urgency
- Applies medical domain reasoning to one metric but evaluates the others as if for
  a general-purpose system

**Incorrect / no-credit criteria:**
- Accepts all scores as adequate without reference to the domain's risk profile
- Identifies faithfulness as the only concern without addressing context recall
- Cannot explain why context recall is more critical than precision in high-stakes domains

---

## Q8 — Building a continuous evaluation pipeline

**Difficulty:** advanced

**Question:**
Describe how you would set up a continuous evaluation pipeline for a production RAG
system to detect quality degradation automatically. What triggers would you monitor,
what metrics would you compute, and how would you alert the team?

**Correct answer criteria:**
- Trigger monitoring: run automated evaluation on a sample of production queries (e.g.,
  100 randomly sampled queries per day). Also trigger on: new document ingestion events
  (index update may affect retrieval), embedding model version change, LLM model version
  change.
- Metrics to compute continuously: faithfulness and answer relevancy on the sampled queries
  (using an LLM evaluator against retrieved context). Also track: fallback rate ("I don't
  know" responses) and retrieval latency as leading indicators.
- Alerting: define baseline scores from the pre-deployment evaluation. Alert when a
  rolling 7-day average drops more than X% below the baseline (e.g., faithfulness drops
  below 0.75). Immediate alert for: fallback rate spike (system suddenly failing to
  retrieve relevant context), latency spike (infrastructure degradation).
- Optional: periodic offline re-evaluation against the full labeled test set to detect
  slow drift, not just spikes.
- The learner should demonstrate that continuous evaluation is not the same as a one-time
  pre-deployment check — it requires scheduled sampling, baseline tracking, and alerting
  thresholds.

**Partial credit criteria:**
- Describes the sampling and metric computation but does not address alerting thresholds
  or baseline tracking
- Correctly describes what to monitor but cannot explain how changes to the pipeline
  (new documents, model updates) trigger re-evaluation

**Incorrect / no-credit criteria:**
- Describes continuous evaluation as running RAGAS once before deployment and never again
- Cannot identify what events should trigger re-evaluation beyond scheduled sampling
- Cannot define what constitutes a degradation worth alerting on

---

## Q9 — Evaluation pipeline without ground truth

**Difficulty:** advanced

**Question:**
You are deploying a RAG system over an internal knowledge base that has never been
formally evaluated. There are no labeled query-answer pairs, no existing test set, and
no budget for manual annotation. Describe how you would build an evaluation pipeline
using synthetic ground truth generation. What specific risks must you avoid in generating
synthetic ground truth, and how would you validate that your synthetic eval actually
correlates with user satisfaction?

**Correct answer criteria:**
- Synthetic ground truth generation: for each document chunk, prompt an LLM to generate
  a question that the chunk answers, along with the expected answer. The (question, chunk,
  answer) triple forms a synthetic RAGAS test example. RAGAS's `TestsetGenerator` automates
  this pattern
- Risk 1: circular evaluation. If you use the same LLM to generate synthetic questions
  and to evaluate answers, the evaluator is testing whether the RAG system can satisfy
  the question-generating LLM's style — not whether it produces correct answers. The
  evaluator may reward any fluent answer regardless of correctness, inflating faithfulness
  and answer relevancy scores. Mitigation: use a different, stronger LLM as the evaluator
  than the one that generated the synthetic questions
- Risk 2: distribution mismatch. Synthetic questions generated from document chunks are
  bottom-up (starting from the answer document). Real user queries are top-down (starting
  from a user's need). The synthetic distribution will over-represent easy, document-
  aligned questions and under-represent ambiguous, navigational, or comparative queries.
  Mitigation: supplement with real user query logs as soon as any production traffic exists
- Risk 3: synthetic questions that only one chunk can answer. If the test set is
  constructed chunk-by-chunk with one ground truth chunk per question, context_recall will
  artificially score well (the single relevant chunk is almost always retrieved), masking
  real recall problems for queries requiring multi-chunk synthesis
- Validation against user satisfaction: run a shadow evaluation where you manually review
  20–30 system responses and ask the corresponding users (via feedback widget or survey)
  to rate them. Compute correlation between RAGAS scores and user ratings for that sample.
  A correlation below 0.5 is a signal that your synthetic eval is not predictive of actual
  user satisfaction and needs redesign

**Partial credit criteria:**
- Correctly describes the generation procedure but identifies only one of the three risks
- Identifies all three risks but cannot describe a concrete validation method to check
  correlation with user satisfaction

**Incorrect / no-credit criteria:**
- Proposes using the same LLM for generation and evaluation without identifying the
  circular evaluation risk
- Claims synthetic ground truth is equivalent in quality to human-labeled ground truth
  with no caveats
- Cannot describe any method for validating that synthetic eval scores are meaningful

---

## Q10 — Diagnosing retrieval quality problems vs. generation quality problems with RAGAS

**Difficulty:** advanced

**Question:**
A RAGAS evaluation returns the following scores for your RAG system: faithfulness = 0.58,
answer_relevancy = 0.72, context_precision = 0.81, context_recall = 0.79. Diagnose
whether the primary failure is a retrieval quality problem or a generation quality problem.
Describe the metric pattern that leads you to this diagnosis and what you would investigate
first.

**Correct answer criteria:**
- Diagnosis: generation quality problem, not a retrieval quality problem
- The diagnostic pattern: context_precision (0.81) and context_recall (0.79) are both
  healthy — the retrieval stage is returning relevant chunks that cover the answer.
  Faithfulness (0.58) is significantly low while context quality is high. This combination
  — good retrieval, low faithfulness — means the LLM is generating claims that are not
  supported by the retrieved context even though the correct information is present in
  the context. The answer_relevancy (0.72) is moderate, suggesting the answers are on
  topic but not well-grounded
- What retrieval failure would look like instead: low context_recall (relevant information
  not present in retrieved chunks) combined with low faithfulness would indicate the LLM
  is hallucinating to fill in missing context. Low context_precision combined with low
  faithfulness would indicate the LLM is confused by retrieved noise
- What to investigate first: the prompt template — specifically whether the "answer only
  from context" instruction is present, whether the context is clearly delimited, and
  whether the LLM is being given a graceful fallback path when unsure. Also check context
  ordering (lost-in-the-middle effect) and whether the answer requires multi-chunk
  synthesis that the prompt is not explicitly handling

**Partial credit criteria:**
- Correctly diagnoses a generation problem but cannot articulate what the retrieval failure
  pattern would look like as a contrast
- Identifies the correct investigation area (prompt template) without fully explaining
  why the metric pattern points there

**Incorrect / no-credit criteria:**
- Diagnoses a retrieval problem based on low faithfulness without reading context_precision
  and context_recall
- Recommends switching the embedding model based on these scores
- Cannot describe what metric values would distinguish a retrieval failure from a
  generation failure

---

## Q11 — When a high faithfulness score is misleading

**Difficulty:** advanced

**Question:**
Your RAGAS evaluation shows faithfulness = 0.9. A colleague says "the system is working
well — almost everything it says is grounded in the retrieved context." Describe two
concrete scenarios where a faithfulness score of 0.9 masks a real failure that users
would notice. For each scenario, explain why faithfulness does not capture the problem.

**Correct answer criteria:**
- Scenario 1: the retrieved context is wrong, and the LLM faithfully reports the wrong
  information. Faithfulness measures whether the generated answer is consistent with the
  retrieved context — not whether the retrieved context is correct. If the index contains
  outdated documentation (e.g., a deprecated API endpoint), the LLM will faithfully state
  the wrong answer with faithfulness = 1.0. Users receive confidently wrong information.
  The metric that would capture this is context_recall against a ground truth that reflects
  current documentation — but faithfulness alone cannot detect index staleness
- Scenario 2: the retrieved context covers only one side of a controversial or multi-
  answer topic, and the LLM faithfully reports that one-sided view. The user asked "What
  are the tradeoffs of using synchronous replication?" The retrieved chunks only contain
  arguments in favor of synchronous replication. Faithfulness = 1.0 (every claim is in
  the context), but the answer is incomplete and misleading. Users believe the system
  has given them a complete analysis. The failure is in retrieval coverage (low
  context_recall relative to the full answer space), not in generation grounding
- Both scenarios require the evaluator to understand that faithfulness = consistency with
  retrieved context, not = correctness or completeness relative to the real world

**Partial credit criteria:**
- Describes one valid scenario clearly but the second scenario conflates faithfulness
  with factual accuracy (e.g., "the LLM said something wrong" without explaining the
  role of the retrieved context)
- Correctly identifies both scenarios but cannot articulate the precise mechanism that
  causes faithfulness to be blind to each problem

**Incorrect / no-credit criteria:**
- Claims a faithfulness score of 0.9 always indicates high system quality
- Cannot describe any scenario where high faithfulness coexists with a user-visible failure
- Confuses faithfulness with answer_relevancy or context_recall

---

## Q12 — What faithfulness measures in RAG evaluation

**Difficulty:** novice

**Question:**
What does the faithfulness metric measure in a RAG evaluation? What does a faithfulness
score of 1.0 tell you, and what does a score of 0.0 tell you?

**Correct answer criteria:**
- Faithfulness measures whether the generated answer is supported by the retrieved context —
  specifically, whether each claim in the answer can be found in or directly inferred from
  the retrieved chunks
- A score of 1.0 means every claim in the answer is grounded in the retrieved context;
  the LLM did not introduce any information from outside the provided passages
- A score of 0.0 means none of the claims in the answer are supported by the retrieved
  context — the LLM generated an answer entirely from its parametric knowledge or hallucinated
- Faithfulness does not measure whether the answer is factually correct in the real world —
  a faithfully wrong answer (one that accurately reports incorrect information from the context)
  still scores 1.0

**Partial credit criteria:**
- Correctly describes what faithfulness measures but conflates it with factual accuracy
  against ground truth
- Correctly explains the 1.0 and 0.0 extremes but does not articulate that faithfulness is
  about context grounding, not real-world correctness

**Incorrect / no-credit criteria:**
- Describes faithfulness as measuring whether the answer matches the user's question
  (that is answer_relevancy)
- Believes faithfulness = 1.0 proves the answer is factually correct
- Cannot explain what a faithfulness score represents

---

## Q13 — What context_recall measures

**Difficulty:** novice

**Question:**
What does the context_recall metric measure in RAGAS? Give a concrete example of a
retrieval result that would produce a low context_recall score.

**Correct answer criteria:**
- Context_recall measures how much of the information needed to answer the question is
  present in the retrieved chunks — it is a coverage metric for the retrieval stage
- High context_recall means the retrieval step found most or all of the passages needed
  to construct a correct answer; low context_recall means key information was not retrieved
- Concrete example of low context_recall: a user asks about the three eligibility criteria
  for a program. The correct answer requires chunks covering all three criteria. The
  retrieval step returns chunks covering only one criterion — context_recall would be
  approximately 0.33 (one of three required pieces of information was retrieved)

**Partial credit criteria:**
- Correctly defines context_recall as a coverage metric but cannot give a concrete example
- Gives a valid example of low recall but confuses context_recall with context_precision

**Incorrect / no-credit criteria:**
- Describes context_recall as measuring whether the answer is relevant to the question
  (that is answer_relevancy)
- Confuses context_recall with faithfulness
- Cannot describe what "coverage" means in the context of retrieval

---

## Q14 — What answer_relevancy measures

**Difficulty:** novice

**Question:**
What does the answer_relevancy metric measure in RAGAS? Describe a scenario where a RAG
system produces a high faithfulness score but a low answer_relevancy score.

**Correct answer criteria:**
- Answer_relevancy measures whether the generated answer addresses the user's actual
  question — it evaluates whether the response is on-topic and responsive to what was asked,
  not whether it is factually correct or grounded
- A high faithfulness, low answer_relevancy scenario: a user asks "What is the refund
  policy for orders over $100?" The retrieved chunks contain accurate information about
  the refund policy. The LLM generates a faithful, accurate response — but instead of
  stating the policy directly, it provides a long explanation of the company's customer
  service philosophy. Every claim is grounded in the retrieved context (high faithfulness),
  but the answer does not directly answer the user's question (low answer_relevancy)

**Partial credit criteria:**
- Correctly defines answer_relevancy but cannot construct a scenario where it diverges
  from faithfulness
- Gives a valid scenario but incorrectly describes it as a faithfulness problem rather
  than an answer_relevancy problem

**Incorrect / no-credit criteria:**
- Describes answer_relevancy as measuring factual accuracy
- Confuses answer_relevancy with faithfulness (they measure different things)
- Cannot describe any scenario where an answer is faithful but not relevant

---

## Q15 — Why faithfulness and context_precision can diverge

**Difficulty:** intermediate

**Question:**
A RAG evaluation shows context_precision = 0.88 but faithfulness = 0.52. Explain how
a system can retrieve highly relevant chunks (high precision) while simultaneously
generating answers with many unsupported claims (low faithfulness). What does this
divergence tell you about where the problem lives?

**Correct answer criteria:**
- Context_precision measures the fraction of retrieved chunks that are relevant to the
  query — 0.88 means most retrieved passages are on-topic and useful
- Faithfulness measures whether the claims in the generated answer are supported by the
  retrieved context — 0.52 means roughly half the answer's claims are not grounded in
  what was retrieved
- These metrics measure different stages: context_precision evaluates the retrieval stage;
  faithfulness evaluates the generation stage
- A system can have high precision and low faithfulness when: the retrieval step correctly
  selects relevant chunks, but the LLM ignores or underweights those chunks during
  generation — instead introducing information from its parametric knowledge. This can
  happen when the retrieved context is present but the prompt does not sufficiently
  constrain the LLM to "answer only from context"
- The divergence diagnoses the problem as a generation failure, not a retrieval failure.
  The correct fix is in the prompt (strengthen the grounding instruction) or in the LLM
  behavior, not in the retrieval configuration

**Partial credit criteria:**
- Correctly identifies that the problem is in the generation stage but cannot explain
  the mechanism by which a well-retrieving system produces unfaithful answers
- Correctly identifies the prompt as the likely fix but cannot articulate why high
  precision does not prevent low faithfulness

**Incorrect / no-credit criteria:**
- Recommends improving retrieval (changing embedding model, reranker, or K) based on
  this metric pattern — the retrieval is working well
- Claims that high context_precision should automatically produce high faithfulness
- Cannot distinguish which pipeline stage each metric evaluates
