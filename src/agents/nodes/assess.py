"""
assess_node — curriculum-driven assessment node (Commit 24).

Two operating modes determined from state:

  Test mode (default when no pending question):
    - Deterministically selects a curriculum question for the current topic.
    - Loads question text from knowledge-base/curriculum/questions/<slug>.md.
    - No LLM call. Returns test_mode=True with pending_test_question/slug set.

  Evaluation mode (when pending_test_question is set and user has answered):
    - Calls LLM with EvaluationOutput schema (verdict: correct/partial/incorrect).
    - Maps verdict to test_answer_score: correct=1.0, partial=0.5, incorrect=0.0.
    - Derives sparse topic_scores_delta from test_answer_score and pending_test_slug.
    - Returns test_mode=False with scored result.

Node output keys (all modes):
    topic_scores_delta, identified_gaps, assessment_error,
    test_mode, pending_test_question, pending_test_slug, test_answer_score

Does NOT write: messages, docs, answer, question, retrieval_source, user_id,
trace_id, latency_ms, cache_hit, user_level.
"""

import logging
import pathlib
import re
from typing import Any, Literal

from agents.prompts.assessment import assessment_prompt
from agents.state import (
    VALID_MODULE_SLUGS,
    AgentState,
    EvaluationOutput,
)
from rag.providers import get_provider

logger = logging.getLogger(__name__)

# Path to curriculum question files.
_CURRICULUM_DIR = pathlib.Path(__file__).parents[4] / "knowledge-base" / "curriculum" / "questions"

# Maps verdict string to numeric score.
_VERDICT_SCORE: dict[str, float] = {
    "correct": 1.0,
    "partial": 0.5,
    "incorrect": 0.0,
}


def _load_question_text(slug: str, question_index: int = 0) -> str:
    """Load the first question text from a curriculum question file.

    Args:
        slug: A valid topic slug from VALID_MODULE_SLUGS.
        question_index: Zero-based index of question to load (default: first question).

    Returns:
        The question text string.

    Raises:
        FileNotFoundError: If the curriculum file for slug does not exist.
        ValueError: If no question sections are found in the file.
    """
    path = _CURRICULUM_DIR / f"{slug}.md"
    content = path.read_text(encoding="utf-8")
    # Extract all **Question:** blocks.
    matches = re.findall(r"\*\*Question:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)", content, re.DOTALL)
    if not matches:
        raise ValueError(f"No question blocks found in curriculum file for slug '{slug}'")
    idx = question_index % len(matches)
    return matches[idx].strip()


def _load_rubric_text(slug: str, question_index: int = 0) -> str:
    """Load correct/partial/incorrect criteria for a curriculum question.

    Returns a formatted rubric string for injection into the evaluation prompt.
    """
    path = _CURRICULUM_DIR / f"{slug}.md"
    content = path.read_text(encoding="utf-8")
    # Split into question sections by ## Q header.
    sections = re.split(r"(?=^## Q\d)", content, flags=re.MULTILINE)
    question_sections = [s for s in sections if s.strip().startswith("## Q")]
    if not question_sections:
        return ""
    idx = question_index % len(question_sections)
    section = question_sections[idx]
    # Extract rubric blocks.
    rubric_parts: list[str] = []
    for label in ("Correct answer criteria", "Partial credit criteria", "Incorrect / no-credit criteria"):
        pattern = rf"\*\*{re.escape(label)}:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)"
        match = re.search(pattern, section, re.DOTALL)
        if match:
            rubric_parts.append(f"**{label}:**\n{match.group(1).strip()}")
    return "\n\n".join(rubric_parts)


def _select_question_index(state: AgentState) -> int:
    """Deterministically select a question index for the current topic.

    Uses the number of messages in state as a simple rotation key so
    consecutive sessions on the same topic cycle through questions.
    """
    messages = state.get("messages") or []
    return len(messages) % 8  # 8 questions per topic file


def _select_test_slug(state: AgentState) -> str | None:
    """Select which topic slug to test next.

    Priority order:
      1. First slug in identified_gaps that is in VALID_MODULE_SLUGS.
      2. Fall back to the first valid slug in the canonical ordering.

    Returns None only if VALID_MODULE_SLUGS is empty (impossible in practice).
    """
    gaps: list[str] = state.get("identified_gaps") or []
    for slug in gaps:
        if slug in VALID_MODULE_SLUGS:
            return slug
    # Canonical ordering from topic-slugs.json.
    _ORDERED_SLUGS = [
        "embeddings_and_similarity",
        "rag_pipeline_architecture",
        "chunking_strategies",
        "vector_databases",
        "retrieval_methods",
        "context_and_prompting",
        "evaluation_and_metrics",
        "production_patterns",
    ]
    for slug in _ORDERED_SLUGS:
        if slug in VALID_MODULE_SLUGS:
            return slug
    return None


def _is_evaluation_mode(state: AgentState) -> bool:
    """Return True when a pending test question exists and the user has replied."""
    pending = state.get("pending_test_question")
    if not pending:
        return False
    messages = state.get("messages") or []
    # The last message must be a HumanMessage (user answer), not an AIMessage.
    if not messages:
        return False
    last = messages[-1]
    return getattr(last, "type", None) == "human"


async def assess_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: curriculum-driven test administration and answer evaluation.

    In test mode: selects and returns a curriculum question; no LLM call.
    In evaluation mode: evaluates the user's answer against the rubric via LLM.

    Returns exactly: topic_scores_delta, identified_gaps, assessment_error,
                     test_mode, pending_test_question, pending_test_slug,
                     test_answer_score.
    """
    if _is_evaluation_mode(state):
        return await _evaluate_answer(state)
    return _select_test_question(state)


def _select_test_question(state: AgentState) -> dict[str, Any]:
    """Test mode: deterministically select a curriculum question. No LLM call."""
    slug = _select_test_slug(state)
    if slug is None:
        logger.warning("assess_node: no valid slug available for test selection")
        return {
            "topic_scores_delta": {},
            "identified_gaps": state.get("identified_gaps") or [],
            "assessment_error": True,
            "test_mode": False,
            "pending_test_question": None,
            "pending_test_slug": None,
            "test_answer_score": None,
        }
    try:
        q_idx = _select_question_index(state)
        question_text = _load_question_text(slug, q_idx)
    except (FileNotFoundError, ValueError) as exc:
        logger.warning(
            "assess_node: failed to load curriculum question for slug '%s': %s",
            slug,
            exc,
        )
        return {
            "topic_scores_delta": {},
            "identified_gaps": state.get("identified_gaps") or [],
            "assessment_error": True,
            "test_mode": False,
            "pending_test_question": None,
            "pending_test_slug": None,
            "test_answer_score": None,
        }

    return {
        "topic_scores_delta": {},
        "identified_gaps": state.get("identified_gaps") or [],
        "assessment_error": False,
        "test_mode": True,
        "pending_test_question": question_text,
        "pending_test_slug": slug,
        "test_answer_score": None,
    }


async def _evaluate_answer(state: AgentState) -> dict[str, Any]:
    """Evaluation mode: score the user's answer via LLM against curriculum rubric."""
    pending_slug: str | None = state.get("pending_test_slug")

    # Guard: slug must be valid.
    if pending_slug not in VALID_MODULE_SLUGS:
        logger.warning(
            "assess_node: pending_test_slug '%s' is not in VALID_MODULE_SLUGS — "
            "setting assessment_error=True, trace_id=%s",
            pending_slug,
            state.get("trace_id"),
        )
        return _eval_error_result(state)

    try:
        q_idx = _select_question_index(state)
        rubric = _load_rubric_text(pending_slug, q_idx)
        pending_question: str = state.get("pending_test_question") or ""
        user_answer: str = state.get("question") or ""

        llm = get_provider().get_llm()
        chain = assessment_prompt | llm.with_structured_output(EvaluationOutput)

        result: EvaluationOutput = await chain.ainvoke({
            "question": pending_question,
            "rubric": rubric,
            "user_answer": user_answer,
        })

        # Map verdict to score; treat unknown verdicts as incorrect.
        verdict: str = result.verdict if result.verdict in _VERDICT_SCORE else "incorrect"
        if result.verdict not in _VERDICT_SCORE:
            logger.warning(
                "assess_node: invalid verdict '%s' received — treating as incorrect",
                result.verdict,
            )
        score: float = _VERDICT_SCORE[verdict]

        # Derive sparse delta from score and slug.
        delta: dict[str, float] = {pending_slug: score} if score > 0.0 else {}

        return {
            "topic_scores_delta": delta,
            "identified_gaps": result.identified_gaps,
            "assessment_error": False,
            "test_mode": False,
            "pending_test_question": None,
            "pending_test_slug": None,
            "test_answer_score": score,
        }

    except Exception:
        logger.warning(
            "assess_node: evaluation failed — setting assessment_error=True, "
            "trace_id=%s",
            state.get("trace_id"),  # type: ignore[call-overload]
            exc_info=True,
        )
        return _eval_error_result(state)


def _eval_error_result(state: AgentState) -> dict[str, Any]:
    """Return the standard error payload for evaluation failures."""
    return {
        "topic_scores_delta": {},
        "identified_gaps": [],
        "assessment_error": True,
        "test_mode": False,
        "pending_test_question": None,
        "pending_test_slug": None,
        "test_answer_score": None,
    }
