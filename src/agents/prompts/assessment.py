"""
Assessment prompt template for assess_node.

This is a hidden second LLM call made once per user turn.  Latency matters.
Keep the prompt focused — no few-shot examples needed when the output schema
is enforced by .with_structured_output(AssessmentOutput).

Prompt structure (per project standard):
  role → task → constraints → output format

The prompt is a ChatPromptTemplate so the node can call:
    chain = assessment_prompt | llm.with_structured_output(AssessmentOutput)
    result = await chain.ainvoke({
        "question":     state["question"],
        "answer":       state["answer"],
        "valid_slugs":  sorted(VALID_MODULE_SLUGS),
    })
"""

from langchain_core.prompts import ChatPromptTemplate

# ---------------------------------------------------------------------------
# System message — role + task + constraints
# ---------------------------------------------------------------------------

_SYSTEM = """\
You are a learning assessment engine for a RAG-based tutoring system about \
Retrieval-Augmented Generation (RAG).

Given a user's question and the system-generated answer, your job is to assess:
1. Which knowledge modules the interaction touched.
2. How well the user appears to understand each touched module, expressed as a \
score delta (positive = stronger understanding, negative = weaker).
3. Which modules show apparent gaps in the user's understanding.

CONSTRAINTS:
- topic_scores_delta keys MUST come from the valid_slugs list provided. \
Do NOT invent or abbreviate slug names.
- Score deltas must be in the range [-1.0, 1.0]. Use 0.0 to omit a module. \
Only include modules that were meaningfully touched by the interaction.
- identified_gaps should list slugs from valid_slugs where the user's question \
reveals low or missing understanding. An empty list is valid.
- user_level reflects your overall assessment of the user's mastery level \
for this turn. It MUST be exactly one of: \
novice, beginner, intermediate, advanced, expert.
- Be conservative. If the interaction does not clearly evidence a module, \
do not include it in topic_scores_delta.
- Do NOT include commentary outside the structured output fields.
"""

# ---------------------------------------------------------------------------
# Human message — per-turn input
# ---------------------------------------------------------------------------

_HUMAN = """\
Valid module slugs: {valid_slugs}

User question:
{question}

System answer:
{answer}

Assess the interaction and return the structured output.
"""

# ---------------------------------------------------------------------------
# Public template — imported by assess_node
# ---------------------------------------------------------------------------

assessment_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
])
