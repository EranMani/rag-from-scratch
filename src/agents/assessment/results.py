from typing import Any


def build_test_result(
    *,
    topic_scores_delta: dict[str, float],
    identified_gaps: list[str],
    assessment_error: bool,
    test_mode: bool,
    pending_test_question: str | None = None,
    pending_test_slug: str | None = None,
    is_mcq: bool = False,
    pending_mcq_correct_answer: str | None = None,
    messages: list[Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "topic_scores_delta": topic_scores_delta,
        "identified_gaps": identified_gaps,
        "assessment_error": assessment_error,
        "test_mode": test_mode,
        "pending_test_question": pending_test_question,
        "pending_test_slug": pending_test_slug,
        "is_mcq": is_mcq,
        "pending_mcq_correct_answer": pending_mcq_correct_answer,
        "is_passive_delta": True,
    }
    if messages is not None:
        result["messages"] = messages
    return result


def build_eval_result(
    *,
    topic_scores_delta: dict[str, float],
    identified_gaps: list[str],
    assessment_error: bool,
) -> dict[str, Any]:
    return {
        "topic_scores_delta": topic_scores_delta,
        "identified_gaps": identified_gaps,
        "assessment_error": assessment_error,
        "test_mode": False,
        "pending_test_question": None,
        "pending_test_slug": None,
        "is_mcq": False,
        "pending_mcq_correct_answer": None,
        "is_passive_delta": False,
    }
