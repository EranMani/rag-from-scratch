"""
Shared MCQ file loader — extracted from agents.nodes.assess for reuse by onboarding routes.

Pure file I/O: no agent state, no LLM calls.
"""

import pathlib
import re

_CURRICULUM_DIR = (
    pathlib.Path(__file__).resolve().parents[2] / "knowledge-base" / "curriculum" / "questions"
)
_MCQ_DIR = _CURRICULUM_DIR / "mcq"


def load_mcq_question(slug: str, question_index: int) -> tuple[str, str]:
    """Load an MCQ question from knowledge-base/curriculum/questions/mcq/[slug].md.

    Returns (display_text, correct_answer) where display_text is ready to render.

    Raises:
        FileNotFoundError: MCQ file for slug does not exist.
        ValueError: Question block is malformed (missing required fields).
    """
    path = _MCQ_DIR / f"{slug}.md"
    content = path.read_text(encoding="utf-8")

    blocks = re.split(r"(?=^## MCQ-)", content, flags=re.MULTILINE)
    question_blocks = [b for b in blocks if b.strip().startswith("## MCQ-")]

    if not question_blocks:
        raise ValueError(f"No MCQ question blocks found in file for slug '{slug}'")

    idx = question_index % len(question_blocks)
    block = question_blocks[idx]

    q_match = re.search(r"\*\*Question:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)", block, re.DOTALL)
    if not q_match:
        raise ValueError(f"MCQ block {idx} for slug '{slug}' missing **Question:** field")
    question_text = q_match.group(1).strip()

    opts_match = re.search(r"\*\*Options:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)", block, re.DOTALL)
    if not opts_match:
        raise ValueError(f"MCQ block {idx} for slug '{slug}' missing **Options:** field")
    options_text = opts_match.group(1).strip()

    ans_match = re.search(r"\*\*Correct answer:\*\*\s*([A-Da-d])", block)
    if not ans_match:
        raise ValueError(f"MCQ block {idx} for slug '{slug}' missing **Correct answer:** field")
    correct_answer = ans_match.group(1).strip().upper()

    display_text = f"Knowledge check: {question_text}\n\n{options_text}"
    return display_text, correct_answer
