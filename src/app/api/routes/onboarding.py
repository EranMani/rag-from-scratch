"""
Onboarding API — placement diagnostic for new users.

Three endpoints:
  GET  /api/onboarding/status      — is onboarding needed?
  POST /api/onboarding/diagnostic  — return 3 MCQ questions for a self-report level
  POST /api/onboarding/complete    — score answers and write confirmed level to profile

Placement rules:
  3/3 or 2/3 correct → self-report level
  1/3 correct        → one level below self-report
  0/3 correct        → two levels below self-report
  Floor              → novice (cannot drop below)

Diagnostic slug by self-report level:
  novice       → embeddings_and_similarity     (Phase 1, mixed difficulty)
  intermediate → chunking_strategies           (Phase 2, mixed difficulty)
  expert       → evaluation_and_metrics        (Phase 3, mixed difficulty)
"""

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from agents.mcq_utils import load_mcq_question
from app.auth.deps import get_current_user
from app.profile.db import get_or_create_profile, update_profile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SELF_REPORT_LEVELS = ("novice", "intermediate", "expert")

_DIAGNOSTIC_SLUG: dict[str, str] = {
    "novice": "embeddings_and_similarity",
    "intermediate": "chunking_strategies",
    "expert": "evaluation_and_metrics",
}

# Ordered sequence for level drops (floor = novice)
_LEVEL_ORDER: list[str] = ["novice", "intermediate", "advanced", "expert"]

_NUM_DIAGNOSTIC_QUESTIONS = 3

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

SelfReportLevel = Literal["novice", "intermediate", "expert"]


class DiagnosticRequest(BaseModel):
    level: SelfReportLevel


class DiagnosticQuestion(BaseModel):
    index: int
    text: str


class DiagnosticResponse(BaseModel):
    questions: list[DiagnosticQuestion]
    slug: str


class CompleteRequest(BaseModel):
    level: SelfReportLevel
    answers: list[str]
    skipped: bool = False


class CompleteResponse(BaseModel):
    confirmed_level: str
    correct_count: int
    message: str


class StatusResponse(BaseModel):
    needed: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _drop_level(level: str, n: int) -> str:
    """Drop level by n steps; floor at 'novice'."""
    idx = _LEVEL_ORDER.index(level) if level in _LEVEL_ORDER else 0
    return _LEVEL_ORDER[max(0, idx - n)]


def _placement_message(confirmed_level: str, correct_count: int, skipped: bool) -> str:
    if skipped:
        return "Onboarding skipped. Starting at novice level."
    if correct_count == 3:
        return f"Excellent! You're placed at {confirmed_level} level."
    if correct_count == 2:
        return f"Great start! You're placed at {confirmed_level} level."
    if correct_count == 1:
        return f"Good effort. You're placed at {confirmed_level} level."
    return f"No worries — you're placed at {confirmed_level} level to build a solid foundation."


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=StatusResponse)
async def get_onboarding_status(current_user: dict = Depends(get_current_user)) -> StatusResponse:
    """Return whether onboarding placement is still needed for this user.

    needed=True  when: mastery_level is 'novice' AND topic_scores has no scored (non-None) value.
    needed=False when: any topic has been scored (onboarding or regular chat has run).
    """
    user_id: str = current_user["id"]
    profile = await asyncio.to_thread(get_or_create_profile, user_id)

    topic_scores: dict = profile.get("topic_scores") or {}
    mastery_level: str = profile.get("mastery_level") or "novice"

    has_any_score = any(v is not None for v in topic_scores.values())
    needed = not has_any_score and mastery_level == "novice"

    return StatusResponse(needed=needed)


@router.post("/diagnostic", response_model=DiagnosticResponse)
async def get_diagnostic_questions(
    body: DiagnosticRequest,
    current_user: dict = Depends(get_current_user),
) -> DiagnosticResponse:
    """Return 3 MCQ questions for the user's self-reported level.

    Does NOT return correct answers — only question text with A–D options.
    """
    slug = _DIAGNOSTIC_SLUG[body.level]
    questions: list[DiagnosticQuestion] = []

    try:
        for i in range(_NUM_DIAGNOSTIC_QUESTIONS):
            display_text, _ = load_mcq_question(slug, i)  # discard correct_answer
            questions.append(DiagnosticQuestion(index=i, text=display_text))
    except (FileNotFoundError, ValueError) as exc:
        logger.error("onboarding/diagnostic: failed to load MCQ for slug '%s': %s", slug, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Diagnostic questions unavailable. Please try again.",
        )

    return DiagnosticResponse(questions=questions, slug=slug)


@router.post("/complete", response_model=CompleteResponse)
async def complete_onboarding(
    body: CompleteRequest,
    current_user: dict = Depends(get_current_user),
) -> CompleteResponse:
    """Score the diagnostic answers and write the confirmed mastery level to the profile.

    If skipped=True, writes mastery_level='novice' immediately without scoring.
    """
    user_id: str = current_user["id"]

    if body.skipped:
        await asyncio.to_thread(update_profile, user_id, mastery_level="novice")
        return CompleteResponse(
            confirmed_level="novice",
            correct_count=0,
            message=_placement_message("novice", 0, skipped=True),
        )

    slug = _DIAGNOSTIC_SLUG[body.level]

    # Re-load MCQ files to verify answers — no caching to avoid stale state
    correct_count = 0
    try:
        for i, user_answer in enumerate(body.answers[:_NUM_DIAGNOSTIC_QUESTIONS]):
            _, correct_answer = load_mcq_question(slug, i)
            if user_answer.strip().upper() == correct_answer:
                correct_count += 1
    except (FileNotFoundError, ValueError) as exc:
        logger.error("onboarding/complete: failed to load MCQ for slug '%s': %s", slug, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not verify answers. Please try again.",
        )

    # Placement scoring
    if correct_count >= 2:
        confirmed_level = body.level
    elif correct_count == 1:
        confirmed_level = _drop_level(body.level, 1)
    else:
        confirmed_level = _drop_level(body.level, 2)

    await asyncio.to_thread(update_profile, user_id, mastery_level=confirmed_level)

    return CompleteResponse(
        confirmed_level=confirmed_level,
        correct_count=correct_count,
        message=_placement_message(confirmed_level, correct_count, skipped=False),
    )
