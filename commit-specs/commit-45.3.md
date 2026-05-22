# Commit 45.3 Spec — `question-type-balance`
> **Project:** rag-from-scratch · **Assignee:** ai-engineer · **Load only for the active commit.**
> **Note:** Added 2026-05-22 — product decision: question type ratio varies by user level. Mira reviewed; design validated.

---

### Commit 45.3 — `question-type-balance`

**Commit message:** `feat(EranMani): balance MCQ vs open question ratio by user level`

**Body:**
Implements level-based question type selection. The ratio of MCQ to open questions
scales with mastery level: novices receive only MCQs; experts receive mostly open
questions. Selection is probabilistic within each session.

**Motivation:**
MCQs scaffold novices with constrained choices. Open questions expose genuine
understanding gaps that MCQs cannot detect. As learners progress, the balance
shifts toward open questions to match their capability and provide richer signal.
Ratios agreed in product review (2026-05-22).

**Ratios by level:**
| Level | MCQ | Open |
|---|---|---|
| novice | 100% | 0% |
| beginner | 100% | 0% |
| intermediate | 80% | 20% |
| advanced | 60% | 40% |
| expert | 30% | 70% |

**What to build:**

Add `select_question_type(user_level: str) -> str` to `question_selection.py`:
- Returns `"mcq"` or `"open"` based on a weighted random draw using the ratios above
- `novice` and `beginner` always return `"mcq"` (deterministic, no random draw needed)

Update `select_test_question` in `test_delivery.py`:
- Call `select_question_type(user_level)` first
- Route to `select_mcq_question` or `select_open_question` accordingly
- Replace the current hardcoded MCQ path

**Files touched:**
- `src/agents/assessment/question_selection.py` — add `select_question_type`
- `src/agents/assessment/test_delivery.py` — route based on question type

**Depends on:** 45.2 (open question delivery must be wired first)
**Blocks:** 45.4

**Scope hard limits:**
- Ratio constants live in `question_selection.py` — not in test_delivery.py
- Do NOT touch evaluation.py, scoring.py, or state.py
- Level classification logic is unchanged — levels come from AgentState as-is

**Testing — done when:**
- [ ] `novice` and `beginner` always produce MCQ questions
- [ ] `intermediate`, `advanced`, `expert` can produce both MCQ and open questions
- [ ] Ratio distribution is approximately correct over multiple calls (not a hard assertion — a comment with the expected ratio is sufficient)
- [ ] All existing MCQ tests still pass
