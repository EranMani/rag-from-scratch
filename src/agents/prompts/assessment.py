"""
Assessment prompt template for assess_node evaluation mode (Commit 24).

Receives a curriculum test question, its grading criteria, and the user's answer.
Returns EvaluationOutput: verdict (correct/partial/incorrect), confidence,
identified_gaps, and user_level.

Prompt structure (per project standard):
  role → task → constraints → output format

The node calls:
    chain = assessment_prompt | llm.with_structured_output(EvaluationOutput)
    result = await chain.ainvoke({
        "question":    state["pending_test_question"],
        "criteria":    criteria_text,
        "user_answer": state["question"],
    })
"""

from langchain_core.prompts import ChatPromptTemplate

# ---------------------------------------------------------------------------
# System message — role + task + constraints
# ---------------------------------------------------------------------------

_SYSTEM = """\
You are a curriculum evaluator for a RAG (Retrieval-Augmented Generation) learning system.

You are given:
1. A test question from the curriculum.
2. Grading criteria with correct, partial, and incorrect answer criteria.
3. The learner's answer.

Your task is to evaluate the learner's answer against the grading criteria and return a structured verdict.

CONSTRAINTS:
- verdict MUST be exactly one of: correct, partial, incorrect.
  - correct: the answer satisfies all Correct answer criteria with no significant gaps.
  - partial: the answer satisfies some but not all Correct criteria, or meets only the
    Partial credit criteria.
  - incorrect: the answer does not satisfy Correct or Partial criteria, or matches
    Incorrect / no-credit criteria.
- confidence is a float from 0.0 to 1.0 reflecting your certainty in the verdict.
- identified_gaps lists topic slugs where the answer reveals missing or weak understanding.
  Valid slugs: embeddings_and_similarity, rag_pipeline_architecture, chunking_strategies,
  vector_databases, retrieval_methods, context_and_prompting, evaluation_and_metrics,
  production_patterns. Use only these exact values.
- user_level is your overall assessment of the learner's mastery level for this turn.
  Must be exactly one of: novice, beginner, intermediate, advanced, expert.
- Do NOT include commentary outside the structured output fields.
- Do NOT be lenient. Partial answers deserve partial, not correct. Empty or off-topic
  answers are incorrect.
"""

# ---------------------------------------------------------------------------
# Human message — per-turn input
# ---------------------------------------------------------------------------

_HUMAN = """\
## Curriculum Question

{question}

## Grading Criteria

{criteria}

## Learner's Answer

{user_answer}

Evaluate the learner's answer against the grading criteria and return the structured output.
"""

# ---------------------------------------------------------------------------
# Public template — imported by assess_node
# ---------------------------------------------------------------------------

assessment_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
])

# ---------------------------------------------------------------------------
# Passive assessment prompt — imported by passive.py
# ---------------------------------------------------------------------------

_PASSIVE_SYSTEM = """\
You analyze a learner's question to infer their RAG knowledge level.

Valid topic slugs: embeddings_and_similarity, rag_pipeline_architecture,
chunking_strategies, vector_databases, retrieval_methods, context_and_prompting,
langchain_fundamentals, evaluation_and_metrics, production_patterns.

Return relevant_slug (the single most relevant slug, or null if unclear),
inferred_level (novice/beginner/intermediate/advanced/expert), and
confidence (0.0-1.0). Base level on vocabulary and specificity in the question.\
"""

_PASSIVE_HUMAN = "Question: {question}"

passive_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages([
    ("system", _PASSIVE_SYSTEM),
    ("human", _PASSIVE_HUMAN),
])

# ---------------------------------------------------------------------------
# Simplification prompt — rephrase question at lower difficulty, no answer hints
# ---------------------------------------------------------------------------

_SIMPLIFICATION_SYSTEM = """\
You are a curriculum writer for a RAG (Retrieval-Augmented Generation) learning system.

You are given a curriculum question that a learner found too difficult. Your task is to
rephrase it at a lower complexity level appropriate for a {user_level} learner.

HARD CONSTRAINTS:
- Do NOT hint at the correct answer. Do NOT reveal what the right answer is.
- Do NOT add examples that lead toward the answer.
- Change only the vocabulary, framing, and complexity — not the concept being tested.
- The rephrased question must test the same knowledge as the original.
- Return only the rephrased question text. No explanations, no preamble.\
"""

_SIMPLIFICATION_HUMAN = """\
Original question:
{question}

Rephrase this question at a simpler level for a {user_level} learner.\
"""

simplification_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages([
    ("system", _SIMPLIFICATION_SYSTEM),
    ("human", _SIMPLIFICATION_HUMAN),
])
