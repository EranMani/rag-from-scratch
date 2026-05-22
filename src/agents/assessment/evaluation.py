import logging
import pathlib
import re
from typing import Any

from agents.prompts.assessment import assessment_prompt
from agents.state import VALID_MODULE_SLUGS, AgentState, EvaluationOutput
from rag.providers import get_provider

from .constants import _VERDICT_SCORE
from .results import _build_eval_result
from .slug_selection import _select_mcq_question_index

logger = logging.getLogger(__name__)

_CURRICULUM_DIR = (
    pathlib.Path(__file__).resolve().parents[3] / "knowledge-base" / "curriculum" / "questions"
)


def _load_rubric_text(slug: str, question_index: int = 0) -> str:
    """Extract grading criteria (Correct/Partial/Incorrect) for a question."""
    path = _CURRICULUM_DIR / f"{slug}.md"
    content = path.read_text(encoding="utf-8")

    # Lookahead split: breaks file into per-question sections while keeping ## Q headers intact
    sections = re.split(r"(?=^## Q\d)", content, flags=re.MULTILINE)
    question_sections = [s for s in sections if s.strip().startswith("## Q")]
    if not question_sections:
        return ""

    idx = question_index % len(question_sections)
    section = question_sections[idx]

    rubric_parts: list[str] = []
    for label in ("Correct answer criteria", "Partial credit criteria", "Incorrect / no-credit criteria"):
        pattern = rf"\*\*{re.escape(label)}:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)"
        match = re.search(pattern, section, re.DOTALL)
        if match:
            rubric_parts.append(f"**{label}:**\n{match.group(1).strip()}")
    return "\n\n".join(rubric_parts)


def _evaluate_mcq_answer(user_message: str, correct_answer: str) -> float:
    """Deterministic binary MCQ evaluator — no LLM call."""
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
        delta: dict[str, float] = {pending_slug: score}
        eval_result = _build_eval_result(
            topic_scores_delta=delta,
            identified_gaps=[],
            assessment_error=False,
            test_answer_score=score,
        )
        counts = dict(state.get("session_question_counts") or {})
        counts[pending_slug] = counts.get(pending_slug, 0) + 1
        eval_result["session_question_counts"] = counts
        return eval_result

    try:
        q_idx = _select_mcq_question_index(state, pending_slug)
        rubric = _load_rubric_text(pending_slug, q_idx)
        llm = get_provider().get_llm()

        chain = assessment_prompt | llm.with_structured_output(EvaluationOutput)
        eval_output: EvaluationOutput = await chain.ainvoke({
            "question": state.get("pending_test_question") or "",
            "rubric": rubric,
            "user_answer": state.get("question") or "",
        })

        score = _verdict_to_score(eval_output.verdict)
        llm_delta: dict[str, float] = {pending_slug: score} if score > 0.0 else {}

        eval_result = _build_eval_result(
            topic_scores_delta=llm_delta,
            identified_gaps=eval_output.identified_gaps,
            assessment_error=False,
            test_answer_score=score,
        )
        counts = dict(state.get("session_question_counts") or {})
        counts[pending_slug] = counts.get(pending_slug, 0) + 1
        eval_result["session_question_counts"] = counts
        return eval_result

    except Exception:
        logger.warning(
            "assess_node: evaluation failed, trace_id=%s",
            state.get("trace_id"),
            exc_info=True,
        )
        return _build_eval_result(topic_scores_delta={}, identified_gaps=[], assessment_error=True)
