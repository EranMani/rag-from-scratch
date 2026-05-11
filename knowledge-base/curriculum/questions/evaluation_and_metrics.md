# Question Bank: `evaluation_and_metrics`
# Phase: 3 — Production
# Maintained by: Lara (RAG Curriculum Specialist)
# Last updated: 2026-05-11 (Commit 22)

---

## Q1 — RAGAS framework overview

**Difficulty:** beginner

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

**Difficulty:** beginner

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
