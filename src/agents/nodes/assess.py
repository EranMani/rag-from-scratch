"""
assess_node — LangGraph node that assesses user understanding from an answer turn.

Node contract:
    Input:  AgentState.answer          (str)  — the generated answer this turn
            AgentState.question        (str)  — the user's question this turn
            AgentState.docs            (list[Document]) — retrieved context
            AgentState.user_level      (Literal[...])  — current mastery level

    Output: {
        "topic_scores_delta": dict[str, float],  — sparse slug → score delta
        "identified_gaps":    list[str],          — slugs with low understanding
        "assessment_error":   bool,               — True if assessment failed
    }

    DOES NOT write: messages, docs, answer, question, retrieval_source, or any
    field owned by retrieve_node or generate_node.
    DOES NOT write: user_level — AssessmentOutput.user_level is used for the LLM
    assessment call only; it is NOT propagated back to AgentState to avoid a
    state ownership conflict (see Commit 12 design notes, deferred to Commit 15).

Design notes:
- Commit 13 replaces the scaffold stub with a real LLM call using
  assessment_prompt | llm.with_structured_output(AssessmentOutput).
- get_provider() is called per-invocation (not at module level) so the circuit
  breaker fallback (OpenAI → Ollama) is observed on every turn.
- assessment_error is set to True when the LLM call or structured-output parsing
  fails.  When True, the conditional edge in graph.py routes to update_profile_node
  with an empty delta — no delta is applied to the profile.
- AssessmentOutput is imported from agents.state (the single schema source of truth).
  The validator on topic_scores_delta silently drops unknown module slugs.
"""

import logging
from typing import Any

from agents.prompts.assessment import assessment_prompt
from agents.state import VALID_MODULE_SLUGS, AgentState, AssessmentOutput
from rag.providers import get_provider

logger = logging.getLogger(__name__)


async def assess_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: assess user understanding from this turn's answer and question.

    Calls the LLM via get_provider().get_llm().with_structured_output(AssessmentOutput)
    to extract topic understanding from the user's question and the generated answer.

    On any assessment failure the node catches the exception, logs a warning,
    sets assessment_error=True, and returns empty deltas.  The conditional edge
    in graph.py routes the fallback path so the graph never terminates on an
    assessment failure.

    Returns exactly three keys: topic_scores_delta, identified_gaps, assessment_error.
    Does NOT return user_level — state ownership deferred to Commit 15 design review.
    """
    try:
        # get_provider() is called here (not at module level) so every invocation
        # observes the current circuit breaker state: OpenAI primary → Ollama fallback.
        llm = get_provider().get_llm()
        chain = assessment_prompt | llm.with_structured_output(AssessmentOutput)

        result: AssessmentOutput = await chain.ainvoke({
            "question": state["question"],
            "answer": state["answer"],
            "valid_slugs": sorted(VALID_MODULE_SLUGS),
        })

        return {
            "topic_scores_delta": result.topic_scores_delta,
            "identified_gaps": result.identified_gaps,
            "assessment_error": False,
        }

    except Exception:
        logger.warning(
            "assess_node: assessment failed — setting assessment_error=True, "
            "trace_id=%s",
            state.get("trace_id"),  # type: ignore[call-overload]
            exc_info=True,
        )
        return {
            "topic_scores_delta": {},
            "identified_gaps": [],
            "assessment_error": True,
        }
