"""
LLM-synthesized MCQ question generation for the curriculum test delivery layer.

Reads the existing bank blocks for a (slug, mastery_level) pair, calls the LLM
to synthesize N new questions, validates output structure, and returns the list.
Callers must handle all exceptions — this module raises on any failure so the
caller can fall back to bank questions silently.
"""

import asyncio
import json
import logging
import re
from typing import Any

from rag.providers import get_provider

logger = logging.getLogger(__name__)

# Number of questions to request per synthesis call
_N_GENERATE: int = 3

# Hard timeout for the LLM call; keeps the event loop from hanging
_LLM_TIMEOUT_SECONDS: float = 15.0

# Valid option keys for MCQ
_VALID_OPTION_KEYS: frozenset[str] = frozenset({"A", "B", "C", "D"})

# ---------------------------------------------------------------------------
# Prompt — kept in this file per spec (this is the prompt owner module)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a curriculum question writer for a RAG (Retrieval-Augmented Generation) learning platform.

You will be given example questions from a question bank for a specific topic and difficulty level.
Your task is to synthesize {n} new MCQ questions that extend, reframe, or combine concepts from
the examples — without copying them verbatim.

HARD CONSTRAINTS:
- Every question MUST test the same topic slug as the examples: {slug}
- Every question MUST be at the same difficulty tier: {mastery_level}
- Every question MUST have exactly 4 options labeled A, B, C, D
- Exactly ONE option must be correct; the other three are distractors
- You MUST provide a "Why X is wrong" explanation for each of the 3 distractor options
- Do NOT copy any question stem verbatim from the examples
- Do NOT hint at the correct answer in the question stem
- Do NOT include topics outside the slug: {slug}

OUTPUT FORMAT: Return a JSON array of exactly {n} objects. No markdown fences, no preamble.
Each object must have this exact structure:
{{
  "question": "<question stem>",
  "options": {{"A": "<text>", "B": "<text>", "C": "<text>", "D": "<text>"}},
  "correct": "<A|B|C|D>",
  "slug": "{slug}",
  "mastery_level": "{mastery_level}",
  "explanations": {{"<wrong_key_1>": "<why wrong>", "<wrong_key_2>": "<why wrong>", "<wrong_key_3>": "<why wrong>"}}
}}\
"""

_HUMAN_PROMPT = """\
Here are example questions from the bank for topic '{slug}' at difficulty '{mastery_level}':

{examples}

Generate {n} new MCQ questions following the constraints above.\
"""


def _extract_examples(blocks: list[str], max_examples: int = 3) -> str:
    """Extract question stems from up to max_examples bank blocks as LLM context."""
    examples: list[str] = []
    for block in blocks[:max_examples]:
        q_match = re.search(r"\*\*Question:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)", block, re.DOTALL)
        if q_match:
            examples.append(q_match.group(1).strip())
    return "\n\n".join(f"{i + 1}. {q}" for i, q in enumerate(examples)) if examples else "(no examples available)"


def _validate_question(q: Any, expected_slug: str) -> bool:
    """Return True if the question object passes all structural checks."""
    if not isinstance(q, dict):
        return False

    # Required keys present
    for key in ("question", "options", "correct", "slug", "mastery_level", "explanations"):
        if key not in q:
            return False

    # Exactly 4 options with keys A-D
    options = q.get("options")
    if not isinstance(options, dict) or set(options.keys()) != _VALID_OPTION_KEYS:
        return False

    # Exactly 1 correct answer key
    correct = q.get("correct")
    if correct not in _VALID_OPTION_KEYS:
        return False

    # Explanations for exactly the 3 distractor keys
    explanations = q.get("explanations")
    if not isinstance(explanations, dict):
        return False
    expected_distractor_keys = _VALID_OPTION_KEYS - {correct}
    if set(explanations.keys()) != expected_distractor_keys:
        return False

    # No circular distractor (explanation must not repeat question stem verbatim)
    stem: str = str(q.get("question", ""))
    for exp_text in explanations.values():
        if isinstance(exp_text, str) and stem and stem.strip() in exp_text:
            return False

    # Slug must match
    if q.get("slug") != expected_slug:
        return False

    return True


async def generate_questions(
    slug: str,
    mastery_level: str,
    bank_blocks: list[str],
) -> list[dict[str, Any]]:
    """Synthesize N MCQ questions using the LLM, with structural validation.

    Raises on LLM failure, timeout, JSON parse error, or if no questions pass
    validation. Caller is responsible for catching and falling back to bank.
    """
    examples_text = _extract_examples(bank_blocks)
    system = _SYSTEM_PROMPT.format(n=_N_GENERATE, slug=slug, mastery_level=mastery_level)
    human = _HUMAN_PROMPT.format(
        slug=slug,
        mastery_level=mastery_level,
        examples=examples_text,
        n=_N_GENERATE,
    )

    llm = get_provider().get_llm()

    async def _call() -> str:
        from langchain_core.messages import HumanMessage, SystemMessage
        response = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=human)])
        return str(response.content)

    raw: str = await asyncio.wait_for(_call(), timeout=_LLM_TIMEOUT_SECONDS)

    # Strip any accidental markdown fences the LLM might add despite instructions
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())

    parsed: Any = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError(f"LLM output is not a JSON array for slug='{slug}'")

    valid = [q for q in parsed if _validate_question(q, slug)]
    if not valid:
        raise ValueError(f"No questions passed validation for slug='{slug}' level='{mastery_level}'")

    logger.info(
        "question_generation: generated %d/%d valid questions for slug='%s' level='%s'",
        len(valid), len(parsed), slug, mastery_level,
    )
    return valid
