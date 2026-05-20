"""
assess_node — curriculum-driven assessment node.

Flow Diagram:
                        ┌─────────────────┐
                        │   assess_node   │
                        └────────┬────────┘
                                 │
                    ┌────────────┴────────────┐
                    │  _is_evaluation_mode?   │
                    └────────────┬────────────┘
                        ┌────── │ ──────┐
                        │ No           │ Yes
                        ▼              ▼
         ┌──────────────────┐   ┌───────────────────┐
         │_select_test_question│   │ _evaluate_answer  │
         └────────┬─────────┘   └────────┬──────────┘
                  │                       │
                  ▼                       ▼
    ┌──────────────────────┐   ┌────────────────────┐
    │_run_passive_assessment│   │ _load_rubric_text  │
    │  (infer from query)  │   │ (grading criteria) │
    └──────────┬───────────┘   └────────┬───────────┘
               │                        │
               ▼                        ▼
    ┌──────────────────────┐   ┌────────────────────┐
    │_validated_passive_delta│   │  LLM structured    │
    │  (guards + scoring)  │   │  output chain      │
    └──────────┬───────────┘   └────────┬───────────┘
               │                        │
               ▼                        ▼
    ┌──────────────────────┐   ┌────────────────────┐
    │  _select_test_slug   │   │ _verdict_to_score  │
    │  (gaps → curriculum) │   │ (verdict → float)  │
    └──────────┬───────────┘   └────────┬───────────┘
               │                        │
               ▼                        ▼
    ┌──────────────────────┐   ┌────────────────────┐
    │ _load_question_text  │   │  _build_eval_result│
    │ (slug → markdown)    │   │  (test_mode=False) │
    └──────────┬───────────┘   └────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  _build_test_result  │
    │  (test_mode=True)    │
    └──────────────────────┘

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
from typing import Any

from langchain_core.messages import AIMessage

from agents.prompts.assessment import assessment_prompt
from langchain_core.prompts import ChatPromptTemplate

from agents.mcq_utils import load_mcq_question as _load_mcq_question  # shared utility
from agents.state import (
    VALID_MODULE_SLUGS,
    AgentState,
    EvaluationOutput,
    PassiveAssessmentOutput,
)
from app.profile.scoring import PHASE_1_TOPICS, PHASE_2_TOPICS, PHASE_3_TOPICS
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

_ALL_TOPICS: frozenset[str] = PHASE_1_TOPICS | PHASE_2_TOPICS | PHASE_3_TOPICS

_LEVEL_TO_PHASE: dict[str, frozenset[str]] = {
    "novice":       PHASE_1_TOPICS,
    "beginner":     PHASE_1_TOPICS,
    "intermediate": PHASE_2_TOPICS,
    "advanced":     PHASE_3_TOPICS,
    "expert":       _ALL_TOPICS,
}

# Canonical ordering: Phase 1 first, Phase 3 last
_ORDERED_SLUGS: list[str] = [
    "embeddings_and_similarity",
    "rag_pipeline_architecture",
    "chunking_strategies",
    "vector_databases",
    "retrieval_methods",
    "context_and_prompting",
    "evaluation_and_metrics",
    "production_patterns",
]

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


# ---------------------------------------------------------------------------
# Result builders — single source of truth for the node's output shape
# ---------------------------------------------------------------------------

def _build_test_result(
    *,
    topic_scores_delta: dict[str, float],
    identified_gaps: list[str],
    assessment_error: bool,
    test_mode: bool,
    pending_test_question: str | None = None,
    pending_test_slug: str | None = None,
    test_answer_score: float | None = None,
    is_mcq: bool = False,
    pending_mcq_correct_answer: str | None = None,
    messages: list[Any] | None = None,
) -> dict[str, Any]:
    """Construct the standard node output for test-selection mode."""
    result: dict[str, Any] = {
        "topic_scores_delta": topic_scores_delta,
        "identified_gaps": identified_gaps,
        "assessment_error": assessment_error,
        "test_mode": test_mode,
        "pending_test_question": pending_test_question,
        "pending_test_slug": pending_test_slug,
        "test_answer_score": test_answer_score,
        "is_mcq": is_mcq,
        "pending_mcq_correct_answer": pending_mcq_correct_answer,
    }
    if messages is not None:
        result["messages"] = messages
    return result


def _build_eval_result(
    *,
    topic_scores_delta: dict[str, float],
    identified_gaps: list[str],
    assessment_error: bool,
    test_answer_score: float | None = None,
) -> dict[str, Any]:
    """Construct the standard node output for evaluation mode (always exits test mode)."""
    return {
        "topic_scores_delta": topic_scores_delta,
        "identified_gaps": identified_gaps,
        "assessment_error": assessment_error,
        "test_mode": False,
        "pending_test_question": None,
        "pending_test_slug": None,
        "test_answer_score": test_answer_score,
        "is_mcq": False,
        "pending_mcq_correct_answer": None,
    }


# ---------------------------------------------------------------------------
# Helpers — small, named units of logic
# ---------------------------------------------------------------------------

def _verdict_to_score(verdict: str) -> float:
    """Map an LLM verdict string to a deterministic numeric score.

    Logs a warning and falls back to 0.0 for unknown verdicts.
    """
    if verdict in _VERDICT_SCORE:
        return _VERDICT_SCORE[verdict]

    logger.warning(
        "assess_node: invalid verdict '%s' received — treating as incorrect",
        verdict,
    )
    return 0.0


def _validated_passive_delta(result: PassiveAssessmentOutput) -> dict[str, float]:
    """Apply validation guards to passive assessment output.

    Returns a single-key {slug: score} dict, or empty dict if any guard fails.
    """
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


# ---------------------------------------------------------------------------
# Curriculum content loaders
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# MCQ loaders and evaluator
# ---------------------------------------------------------------------------

def _evaluate_mcq_answer(user_message: str, correct_answer: str) -> float:
    """Deterministic binary MCQ evaluator — no LLM call."""
    match = re.search(r"\b([A-Da-d])\b", user_message.strip())
    if match and match.group(1).upper() == correct_answer.upper():
        return 1.0
    return 0.0


# ---------------------------------------------------------------------------
# State selectors
# ---------------------------------------------------------------------------

def _select_question_index(state: AgentState) -> int:
    """Deterministically select a question index based on conversation depth."""
    messages = state.get("messages") or []
    return len(messages) % 5  # 5 MCQ questions per topic file


def _select_test_slug(state: AgentState) -> str | None:
    """Determine the next topic slug for testing, gated to the user's current phase.

    Priority:
      1. First slug in identified_gaps that is eligible for the user's phase.
      2. Fall back to canonical ordering within the eligible phase.

    Returns None only if VALID_MODULE_SLUGS is empty.
    """
    user_level: str = state.get("user_level") or "novice"
    eligible: frozenset[str] = _LEVEL_TO_PHASE.get(user_level, PHASE_1_TOPICS)

    gaps: list[str] = state.get("identified_gaps") or []
    for slug in gaps:
        if slug in eligible and slug in VALID_MODULE_SLUGS:
            return slug

    for slug in _ORDERED_SLUGS:
        if slug in eligible and slug in VALID_MODULE_SLUGS:
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


# ---------------------------------------------------------------------------
# Main node + orchestration functions
# ---------------------------------------------------------------------------

async def assess_node(state: AgentState) -> dict[str, Any]:
    """LangGraph node: curriculum-driven test administration and answer evaluation.

    Routes to evaluation if a pending answer exists, otherwise selects
    the next curriculum question.
    """
    # Route: if user answered a pending question → evaluate; otherwise → serve next question
    if _is_evaluation_mode(state):
        return await _evaluate_answer(state)
    return await _select_test_question(state)


async def _run_passive_assessment(question: str) -> tuple[dict[str, float], bool]:
    """Infer knowledge level from the user's natural query (no formal test).

    Returns (delta, is_rag_related) where is_rag_related=True when relevant_slug is not None.
    On exception, returns ({}, True) — permissive fallback avoids suppressing the knowledge check.
    """
    try:
        llm = get_provider().get_llm()
        # Pipe-and-Filter chain: prompt | LLM | Pydantic parser — atomic unit that
        # either produces a validated PassiveAssessmentOutput or fails cleanly
        chain = _passive_prompt | llm.with_structured_output(PassiveAssessmentOutput)
        result: PassiveAssessmentOutput = await chain.ainvoke({"question": question})
        is_rag_related = result.relevant_slug is not None
        return _validated_passive_delta(result), is_rag_related

    except Exception:
        logger.warning("passive_assessment: LLM call failed — continuing with empty delta", exc_info=True)
        return {}, True


async def _select_test_question(state: AgentState) -> dict[str, Any]:
    """Run passive assessment then select and load a curriculum question."""
    # First, infer a score from the user's natural question (no test needed)
    passive_delta, is_rag_related = await _run_passive_assessment(state.get("question") or "")
    gaps = state.get("identified_gaps") or []

    # Off-topic query (e.g. greetings, chitchat) — skip knowledge check entirely
    if not is_rag_related:
        return _build_test_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=False,
            test_mode=False,
        )

    slug = _select_test_slug(state)
    if slug is None:
        logger.warning("assess_node: no valid slug available for test selection")
        return _build_test_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=True,
            test_mode=False,
        )

    try:
        q_idx = _select_question_index(state)
        display_text, correct_answer = _load_mcq_question(slug, q_idx)
    except (FileNotFoundError, ValueError) as exc:
        logger.warning("assess_node: failed to load MCQ question for slug '%s': %s", slug, exc)
        return _build_test_result(
            topic_scores_delta=passive_delta,
            identified_gaps=gaps,
            assessment_error=True,
            test_mode=False,
        )

    return _build_test_result(
        topic_scores_delta=passive_delta,
        identified_gaps=gaps,
        assessment_error=False,
        test_mode=True,
        pending_test_question=display_text,
        pending_test_slug=slug,
        is_mcq=True,
        pending_mcq_correct_answer=correct_answer,
        messages=[AIMessage(content=f"\n\n{display_text}")],
    )


async def _evaluate_answer(state: AgentState) -> dict[str, Any]:
    """Evaluate the user's answer — MCQ binary path or LLM rubric path."""
    pending_slug: str | None = state.get("pending_test_slug")

    if pending_slug not in VALID_MODULE_SLUGS:
        logger.warning(
            "assess_node: pending_test_slug '%s' not in VALID_MODULE_SLUGS, trace_id=%s",
            pending_slug,
            state.get("trace_id"),
        )
        return _build_eval_result(topic_scores_delta={}, identified_gaps=[], assessment_error=True)

    if state.get("is_mcq"):
        correct = state.get("pending_mcq_correct_answer")
        if correct is None:
            logger.error(
                "assess_node: is_mcq=True but pending_mcq_correct_answer is None; trace_id=%s",
                state.get("trace_id"),
            )
            return _build_eval_result(topic_scores_delta={}, identified_gaps=[], assessment_error=True)
        user_msg = (state.get("messages") or [])[-1].content or ""
        score = _evaluate_mcq_answer(user_msg, correct)
        delta: dict[str, float] = {pending_slug: score} if score > 0.0 else {}
        return _build_eval_result(
            topic_scores_delta=delta,
            identified_gaps=[],
            assessment_error=False,
            test_answer_score=score,
        )

    try:
        q_idx = _select_question_index(state)
        # Load the rubric so the LLM grades against human-authored criteria, not its own knowledge
        rubric = _load_rubric_text(pending_slug, q_idx)
        llm = get_provider().get_llm()

        # Chain: assessment prompt | LLM | EvaluationOutput (verdict + identified_gaps)
        chain = assessment_prompt | llm.with_structured_output(EvaluationOutput)

        result: EvaluationOutput = await chain.ainvoke({
            "question": state.get("pending_test_question") or "",
            "rubric": rubric,
            "user_answer": state.get("question") or "",
        })

        score = _verdict_to_score(result.verdict)
        # Sparse delta: only updates the tested topic, only if the user scored > 0
        llm_delta: dict[str, float] = {pending_slug: score} if score > 0.0 else {}

        return _build_eval_result(
            topic_scores_delta=llm_delta,
            identified_gaps=result.identified_gaps,
            assessment_error=False,
            test_answer_score=score,
        )

    except Exception:
        logger.warning(
            "assess_node: evaluation failed, trace_id=%s",
            state.get("trace_id"),  # type: ignore[call-overload]
            exc_info=True,
        )
        return _build_eval_result(topic_scores_delta={}, identified_gaps=[], assessment_error=True)
