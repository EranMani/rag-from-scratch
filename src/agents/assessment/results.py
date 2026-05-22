from typing import Any


def build_selection_result(
    *,
    topic_scores_delta: dict[str, float],
    identified_gaps: list[str],
    assessment_error: bool,
    pending_test_question: str | None = None,
    pending_test_slug: str | None = None,
    is_mcq: bool = False,
    pending_mcq_correct_answer: str | None = None,
    messages: list[Any] | None = None,
) -> dict[str, Any]:
    """Pack the output of _select_test_question into a state update dict.

    Always sets ``is_passive_delta=True``. ``messages`` is only included in the
    returned dict when it is not ``None`` — callers must not assume the key exists.
    """
    result: dict[str, Any] = {
        "topic_scores_delta": topic_scores_delta,
        "identified_gaps": identified_gaps,
        "assessment_error": assessment_error,
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
    """
    Build an eval result dict after scoring a user answer — no pending question.

    Always sets ``is_passive_delta=False``, ``is_mcq=False``,
    and all pending-question fields to ``None``.
    """
    return {
        "topic_scores_delta": topic_scores_delta,
        "identified_gaps": identified_gaps,
        "assessment_error": assessment_error,
        "pending_test_question": None,
        "pending_test_slug": None,
        "is_mcq": False,
        "pending_mcq_correct_answer": None,
        "is_passive_delta": False,
    }
