import logging
import pathlib
import re
from typing import Any

from langchain_core.messages import AIMessage

from agents.prompts.assessment import assessment_prompt, simplification_prompt
from agents.state import VALID_MODULE_SLUGS, AgentState, EvaluationOutput
from rag.providers import get_provider

from .constants import _VERDICT_SCORE
from .results import build_eval_result

logger = logging.getLogger(__name__)

_CURRICULUM_DIR = (
    pathlib.Path(__file__).resolve().parents[3] / "knowledge-base" / "curriculum" / "questions"
)

_DIFFICULTY_PHRASES: tuple[str, ...] = (
    "too hard",
    "don't understand",
    "do not understand",
    "i don't know",
    "i do not know",
    "help",
    "can you simplify",
    "simplify",
    "hint",
    "not sure",
    "no idea",
    "give up",
)


def _is_difficulty_signal(message: str) -> bool:
    """Return True if the user is signaling difficulty, not answering the question."""
    lowered = message.lower().strip()
    return any(phrase in lowered for phrase in _DIFFICULTY_PHRASES)


async def _simplify_question(original_question: str, user_level: str) -> str:
    """Call LLM to rephrase the question at lower complexity. Returns rephrased text."""
    llm = get_provider().get_llm()
    chain = simplification_prompt | llm
    response = await chain.ainvoke({"question": original_question, "user_level": user_level})
    return response.content.strip()


def _breakdown_criteria_parts(section: str) -> list[str]:
    """
    Retrieve the question criteria parts:
    - Correct answer criteria
    - Partial credit criteria
    - Incorrect / no-credit criteria

    Return a list of each criteria part and its description
    """
    criteria_parts: list[str] = []
    for label in ("Correct answer criteria", "Partial credit criteria", "Incorrect / no-credit criteria"):
        pattern = rf"\*\*{re.escape(label)}:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)"
        match = re.search(pattern, section, re.DOTALL)
        if match:
            criteria_parts.append(f"**{label}:**\n{match.group(1).strip()}")

    return criteria_parts

def _load_open_question_criteria(slug: str, question_index: int = 0) -> str:
    """Extract grading criteria (Correct/Partial/Incorrect) for an open question."""
    # Get open questions content files
    path = _CURRICULUM_DIR / f"{slug}.md"
    content = path.read_text(encoding="utf-8")

    # Breaks file into per-question sections while keeping ## Q headers intact
    sections = re.split(r"(?=^## Q\d)", content, flags=re.MULTILINE)
    question_sections = [s for s in sections if s.strip().startswith("## Q")]

    if not question_sections:
        raise ValueError(f"No question sections found in curriculum file for slug '{slug}'")

    # Select which section question to use, creating varient by using indexed value
    idx = question_index % len(question_sections)
    section = question_sections[idx]
    criteria_parts = _breakdown_criteria_parts(section)

    if not criteria_parts:
        raise ValueError(f"No grading criteria found for slug '{slug}', question index {idx}")

    return "\n\n".join(criteria_parts)

def _evaluate_mcq_answer(user_message: str, correct_answer: str) -> float:
    """
    Deterministic binary MCQ evaluator — no LLM call
    Fetch the user decision answer and compare it against the correct answer
    """
    match = re.search(r"\b([A-Da-d])\b", user_message.strip())
    if match and match.group(1).upper() == correct_answer.upper():
        return 1.0
    return 0.0

def _verdict_to_score(verdict: str) -> float:
    if verdict in _VERDICT_SCORE:
        return _VERDICT_SCORE[verdict]
    logger.warning(
        "assess_node: invalid verdict '%s' received — treating as incorrect",
        verdict,
    )
    return 0.0

def _build_mcq_eval_result(state: AgentState, pending_slug: str) -> dict[str, Any]:
    correct = state.get("pending_mcq_correct_answer")
    if correct is None:
        logger.error(
            "assess_node: is_mcq=True but pending_mcq_correct_answer is None; trace_id=%s",
            state.get("trace_id"),
        )
        return build_eval_result(topic_scores_delta={}, identified_gaps=[], assessment_error=True)

    messages = state.get("messages") or []
    user_msg = messages[-1].content if messages else ""

    score = _evaluate_mcq_answer(user_msg, correct)
    delta: dict[str, float] = {pending_slug: score}
    eval_result = build_eval_result(
        topic_scores_delta=delta,
        identified_gaps=[],
        assessment_error=False,
    )

    return eval_result

def _update_session_questions_count(state: AgentState, pending_slug: str) -> dict[str, int]:
    counts = dict(state.get("session_question_counts") or {})
    counts[pending_slug] = counts.get(pending_slug, 0) + 1
    return counts

async def _invoke_ai_model(state: AgentState, criteria: str) -> EvaluationOutput:
    llm = get_provider().get_llm()

    chain = assessment_prompt | llm.with_structured_output(EvaluationOutput)
    # Keys must match the {placeholder} names defined in the assessment_prompt template.
    eval_output: EvaluationOutput = await chain.ainvoke({
        "question": state.get("pending_test_question") or "",
        "criteria": criteria,
        "user_answer": state.get("question") or "",
    })

    return eval_output
    
async def evaluate_answer(state: AgentState) -> dict[str, Any]:
    """Evaluate the user's answer — difficulty degradation, MCQ binary, or open LLM path."""
    pending_slug: str | None = state.get("pending_test_slug")

    if pending_slug not in VALID_MODULE_SLUGS:
        logger.warning(
            "assess_node: pending_test_slug '%s' not in VALID_MODULE_SLUGS, trace_id=%s",
            pending_slug,
            state.get("trace_id"),
        )
        return build_eval_result(topic_scores_delta={}, identified_gaps=[], assessment_error=True)

    # None not in VALID_MODULE_SLUGS, so the guard above already exits — narrows type for the type checker
    assert pending_slug is not None

    # Difficulty degradation path — check before MCQ/open branch
    messages = state.get("messages") or []
    user_msg = messages[-1].content if messages else ""
    if _is_difficulty_signal(user_msg):
        already_simplified = state.get("question_simplified") or False
        original_question = state.get("pending_test_question") or ""
        existing_gaps = list(state.get("identified_gaps") or [])

        if not already_simplified:
            # Step 2 — rephrase at lower difficulty, do not reveal answer
            try:
                user_level = state.get("user_level") or "novice"
                simplified = await _simplify_question(original_question, user_level)
                logger.info("assess_node: simplified question for trace_id=%s", state.get("trace_id"))
                return {
                    "pending_test_question": simplified,
                    "question_simplified": True,
                    "messages": [AIMessage(content=(
                        "Let me rephrase that question at a simpler level:\n\n" + simplified
                    ))],
                }
            except Exception:
                logger.warning(
                    "assess_node: simplification failed, trace_id=%s",
                    state.get("trace_id"),
                    exc_info=True,
                )
                return build_eval_result(topic_scores_delta={}, identified_gaps=[], assessment_error=True)
        else:
            # Step 3 — reveal answer from docs; mark as gap and clear pending question
            if pending_slug not in existing_gaps:
                existing_gaps.append(pending_slug)
            logger.info(
                "assess_node: difficulty signal after simplification — revealing answer; trace_id=%s",
                state.get("trace_id"),
            )
            result = build_eval_result(
                topic_scores_delta={},
                identified_gaps=existing_gaps,
                assessment_error=False,
            )
            return result

    # Answer came from MCQ question
    if state.get("is_mcq"):
        eval_result = _build_mcq_eval_result(state, pending_slug)
        eval_result["session_question_counts"] = _update_session_questions_count(state, pending_slug)
        return eval_result

    # Answer came from open question
    try:
        message_count = len(messages)
        criteria = _load_open_question_criteria(pending_slug, message_count)

        model_response = await _invoke_ai_model(state, criteria)

        score = _verdict_to_score(model_response.verdict)
        llm_delta: dict[str, float] = {pending_slug: score} if score > 0.0 else {}

        eval_result = build_eval_result(
            topic_scores_delta=llm_delta,
            identified_gaps=model_response.identified_gaps,
            assessment_error=False,
        )
        eval_result["session_question_counts"] = _update_session_questions_count(state, pending_slug)
        return eval_result

    except Exception:
        logger.warning(
            "assess_node: evaluation failed, trace_id=%s",
            state.get("trace_id"),
            exc_info=True,
        )
        return build_eval_result(topic_scores_delta={}, identified_gaps=[], assessment_error=True)
