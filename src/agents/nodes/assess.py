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

Design notes:
- This commit (12) ships the scaffold: the LLM call is a deterministic stub that
  returns an empty AssessmentOutput.  The real assessment prompt is introduced in
  Commit 13.
- assessment_error is set to True when the LLM call or structured-output parsing
  fails.  When True, the conditional edge in graph.py routes directly to
  update_profile_node — no delta is applied to the profile.
- AssessmentOutput is imported from agents.state (the single schema source of truth).
  The validator on topic_scores_delta silently drops unknown module slugs.
- The stub returns an empty AssessmentOutput with user_level set to the value
  already in state.  This is intentionally conservative: the profile is unchanged
  when no real assessment has run.
"""

import logging

from agents.state import AgentState, AssessmentOutput

logger = logging.getLogger(__name__)


async def assess_node(state: AgentState) -> dict:
    """LangGraph node: assess user understanding from this turn's answer and question.

    STUB IMPLEMENTATION (Commit 12): returns a deterministic empty AssessmentOutput.
    The real LLM prompt and structured-output call are added in Commit 13.

    On any assessment failure the node catches the exception, logs a warning,
    sets assessment_error=True, and returns empty deltas.  The conditional edge
    in graph.py routes the fallback path so the graph never terminates on an
    assessment failure.
    """
    try:
        # --- Stub LLM call (Commit 12) -----------------------------------------
        # In Commit 13 this block is replaced with:
        #   llm = get_provider().get_llm()
        #   chain = assessment_prompt | llm.with_structured_output(AssessmentOutput)
        #   result: AssessmentOutput = await chain.ainvoke({...})
        # For now return a deterministic empty output so the graph compiles and all
        # downstream wiring can be exercised without a live LLM.
        result: AssessmentOutput = AssessmentOutput(
            topic_scores_delta={},
            identified_gaps=[],
            user_level=state["user_level"],
        )
        # -----------------------------------------------------------------------

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
