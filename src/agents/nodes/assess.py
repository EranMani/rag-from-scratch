"""
assess_node — curriculum-driven assessment node.

Three operating modes determined from state:

  Test mode (default when no pending question):
    - Runs passive assessment LLM call to infer mastery from the user's natural query.
    - Passive scores are capped at 0.3; emitted only when confidence >= 0.4.
    - Deterministically selects a curriculum question for the current topic.
    - Loads question text from knowledge-base/curriculum/questions/<slug>.md.
    - Returns test_mode=True with pending_test_question/slug set.

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

Architecture details: docs/architecture/assessment-node.md
"""

import logging
import pathlib
import re
from typing import Any, Literal

from langchain_core.messages import AIMessage

from agents.prompts.assessment import assessment_prompt
from langchain_core.prompts import ChatPromptTemplate

from agents.state import (
    VALID_MODULE_SLUGS,
    AgentState,
    EvaluationOutput,
    PassiveAssessmentOutput,
)
from rag.providers import get_provider

logger = logging.getLogger(__name__)

_CURRICULUM_DIR = (
    pathlib.Path(__file__).resolve().parents[3] / "knowledge-base" / "curriculum" / "questions"
)

# Maps LLM evaluation verdicts to numeric scores for active testing
_VERDICT_SCORE: dict[str, float] = {
    "correct": 1.0,
    "partial": 0.5,
    "incorrect": 0.0,
}

# Rewards query sophistication with capped mastery increments (max 0.3)
_PASSIVE_LEVEL_SCORE: dict[str, float] = {
    "novice": 0.05,
    "beginner": 0.1,
    "intermediate": 0.2,
    "advanced": 0.25,
    "expert": 0.3,
}

# Minimum confidence to accept passive inference into the skill profile
_PASSIVE_CONFIDENCE_THRESHOLD: float = 0.4

_PASSIVE_SYSTEM = """\
You analyze a learner's question to infer their RAG knowledge level.

Valid topic slugs: embeddings_and_similarity, rag_pipeline_architecture,
chunking_strategies, vector_databases, retrieval_methods, context_and_prompting,
evaluation_and_metrics, production_patterns.

Return relevant_slug (the single most relevant slug, or null if unclear),
inferred_level (novice/beginner/intermediate/advanced/expert), and
confidence (0.0-1.0). Base level on vocabulary and specificity in the question.\
"""

_PASSIVE_HUMAN = "Question: {question}"

_passive_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages([
    ("system", _PASSIVE_SYSTEM),
    ("human", _PASSIVE_HUMAN),
])


def _load_question_text(slug: str, question_index: int = 0) -> str:
    """Load a question from a curriculum Markdown file by index.

    Args:
        slug: A valid topic slug from VALID_MODULE_SLUGS.
        question_index: Zero-based index; wrapped via modulo for safe rotation.

    Returns:
        The question text string.

    Raises:
        FileNotFoundError: If the curriculum file for slug does not exist.
        ValueError: If no question sections are found in the file.
    """
    path = _CURRICULUM_DIR / f"{slug}.md"
    content = path.read_text(encoding="utf-8")

    # Extract all **Question:** blocks — captures text until the next ** header or EOF
    matches = re.findall(r"\*\*Question:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)", content, re.DOTALL)

    if not matches:
        raise ValueError(f"No question blocks found in curriculum file for slug '{slug}'")

    # Modulo ensures round-robin rotation driven by conversation depth
    idx = question_index % len(matches)
    return matches[idx].strip()


def _load_rubric_text(slug: str, question_index: int = 0) -> str:
    """Extract grading criteria (Correct/Partial/Incorrect) for a question.

    Args:
        slug: The topic identifier used to locate the Markdown file.
        question_index: Wrapped via modulo to select the question block.

    Returns:
        Concatenated rubric labels and criteria, or empty string if none found.
    """
    path = _CURRICULUM_DIR / f"{slug}.md"
    content = path.read_text(encoding="utf-8")

    # Lookahead split: breaks file into per-question sections while keeping ## Q headers intact
    sections = re.split(r"(?=^## Q\d)", content, flags=re.MULTILINE)
    question_sections = [s for s in sections if s.strip().startswith("## Q")]
    if not question_sections:
        return ""

    idx = question_index % len(question_sections)
    section = question_sections[idx]

    # Extract each rubric section (Correct/Partial/Incorrect) to form the LLM's grading guide
    rubric_parts: list[str] = []
    for label in ("Correct answer criteria", "Partial credit criteria", "Incorrect / no-credit criteria"):
        pattern = rf"\*\*{re.escape(label)}:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)"
        match = re.search(pattern, section, re.DOTALL)
        if match:
            rubric_parts.append(f"**{label}:**\n{match.group(1).strip()}")
    return "\n\n".join(rubric_parts)


def _select_question_index(state: AgentState) -> int:
    """Deterministically select a question index based on conversation depth."""
    messages = state.get("messages") or []
    return len(messages) % 8  # 8 questions per topic file


def _select_test_slug(state: AgentState) -> str | None:
    """Determine the next topic slug for testing.

    Priority:
      1. First slug in identified_gaps that is in VALID_MODULE_SLUGS.
      2. Fall back to canonical curriculum ordering.

    Returns None only if VALID_MODULE_SLUGS is empty.
    """
    gaps: list[str] = state.get("identified_gaps") or []
    for slug in gaps:
        if slug in VALID_MODULE_SLUGS:
            return slug

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
    """State-gate: returns True only when a question is pending and the user has responded."""
    pending = state.get("pending_test_question")
    if not pending:
        return False

    messages = state.get("messages") or []
    if not messages:
        return False

    last = messages[-1]
    # getattr guards against malformed message objects in multi-agent state
    return getattr(last, "type", None) == "human"


async def assess_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: curriculum-driven test administration and answer evaluation.

    Routes to evaluation if a pending answer exists, otherwise selects
    the next curriculum question.

    Returns exactly: topic_scores_delta, identified_gaps, assessment_error,
                     test_mode, pending_test_question, pending_test_slug,
                     test_answer_score.
    """
    # Route: if user answered a pending question → evaluate; otherwise → serve next question
    if _is_evaluation_mode(state):
        return await _evaluate_answer(state)
    return await _select_test_question(state)


async def _run_passive_assessment(question: str) -> dict[str, float]:
    """Infer knowledge level from the user's natural query (no formal test).

    Returns a single-key dict {slug: score} or empty dict on failure/low confidence.
    """
    try:
        llm = get_provider().get_llm()
        # Pipe-and-Filter chain: prompt | LLM | Pydantic parser — atomic unit that
        # either produces a validated PassiveAssessmentOutput or fails cleanly
        chain = _passive_prompt | llm.with_structured_output(PassiveAssessmentOutput)
        result: PassiveAssessmentOutput = await chain.ainvoke({"question": question})

        if result.relevant_slug is None:
            return {}

        if result.relevant_slug not in VALID_MODULE_SLUGS:
            logger.warning(
                "passive_assessment: slug '%s' not in VALID_MODULE_SLUGS — ignoring",
                result.relevant_slug,
            )
            return {}

        if result.confidence < _PASSIVE_CONFIDENCE_THRESHOLD:
            return {}

        score = _PASSIVE_LEVEL_SCORE.get(result.inferred_level, 0.0)
        return {result.relevant_slug: score} if score > 0.0 else {}

    except Exception:
        logger.warning("passive_assessment: LLM call failed — continuing with empty delta", exc_info=True)
        return {}


async def _select_test_question(state: AgentState) -> dict[str, Any]:
    """Run passive assessment then select and load a curriculum question."""
    # First, infer a score from the user's natural question (no test needed)
    passive_delta = await _run_passive_assessment(state.get("question") or "")

    slug = _select_test_slug(state)
    if slug is None:
        logger.warning("assess_node: no valid slug available for test selection")
        return {
            "topic_scores_delta": passive_delta,
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
            "topic_scores_delta": passive_delta,
            "identified_gaps": state.get("identified_gaps") or [],
            "assessment_error": True,
            "test_mode": False,
            "pending_test_question": None,
            "pending_test_slug": None,
            "test_answer_score": None,
        }

    return {
        "messages": [AIMessage(content=f"\n\nKnowledge check: {question_text}")],
        "topic_scores_delta": passive_delta,
        "identified_gaps": state.get("identified_gaps") or [],
        "assessment_error": False,
        "test_mode": True,
        "pending_test_question": question_text,
        "pending_test_slug": slug,
        "test_answer_score": None,
    }


async def _evaluate_answer(state: AgentState) -> dict[str, Any]:
    """Evaluate the user's answer against the rubric via LLM structured output."""
    pending_slug: str | None = state.get("pending_test_slug")

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
        # Load the rubric so the LLM grades against human-authored criteria, not its own knowledge
        rubric = _load_rubric_text(pending_slug, q_idx)
        pending_question: str = state.get("pending_test_question") or ""
        user_answer: str = state.get("question") or ""
        llm = get_provider().get_llm()

        # Chain: assessment prompt | LLM | EvaluationOutput (verdict + identified_gaps)
        chain = assessment_prompt | llm.with_structured_output(EvaluationOutput)

        result: EvaluationOutput = await chain.ainvoke({
            "question": pending_question,
            "rubric": rubric,
            "user_answer": user_answer,
        })

        # Map the LLM's verdict string to a deterministic numeric score
        verdict: str = result.verdict if result.verdict in _VERDICT_SCORE else "incorrect"
        if result.verdict not in _VERDICT_SCORE:
            logger.warning(
                "assess_node: invalid verdict '%s' received — treating as incorrect",
                result.verdict,
            )
        score: float = _VERDICT_SCORE[verdict]

        # Sparse delta: only updates the tested topic, only if the user scored > 0
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
