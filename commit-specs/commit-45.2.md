# Commit 45.2 Spec — `open-question-delivery`
> **Project:** rag-from-scratch · **Assignee:** ai-engineer · **Load only for the active commit.**
> **Note:** Added 2026-05-22 — open question evaluation path already exists in evaluation.py but delivery side hardcodes is_mcq=True. This commit makes open question delivery reachable.

---

### Commit 45.2 — `open-question-delivery`

**Commit message:** `feat(EranMani): wire open question delivery — select_open_question and is_mcq=False path`

**Body:**
The evaluation layer already handles open questions (grading criteria loader + LLM
evaluation path in evaluation.py). The delivery side never selects them — is_mcq=True
is hardcoded in test_delivery.py. This commit adds open question selection and makes
the is_mcq=False delivery path reachable for the first time.

**Motivation:**
As discussed in product review (2026-05-22), open questions are the appropriate format
for intermediate-and-above learners. The evaluation infrastructure is ready; only the
delivery side is missing.

**What to build:**

1. Add `select_open_question(state) -> tuple[str, int] | None` to `question_selection.py`
   - Same slug selection logic as `select_mcq_question` (gaps-first, phase-eligible, ordered)
   - Index: `len(messages) % get_open_question_count(slug)` — needs a `get_open_question_count` utility (mirror of `get_mcq_count`)
   - Returns `(slug, question_index)` or `None`

2. Add `load_open_question(slug, index) -> str` to `mcq_utils.py` (or equivalent utils module)
   - Loads the open question display text from the knowledge base
   - Mirror of `load_mcq_question` but for open question files

3. Update `test_delivery.py` — add `deliver_open_question` path:
   - Calls `select_open_question(state)`
   - Calls `load_open_question(slug, q_idx)`
   - Returns `build_selection_result(..., is_mcq=False, pending_test_question=display_text, pending_test_slug=slug)`
   - No `pending_mcq_correct_answer` — open questions are LLM-graded

**Files touched:**
- `src/agents/assessment/question_selection.py` — add `select_open_question`
- `src/agents/assessment/test_delivery.py` — add open question delivery branch
- `src/agents/mcq_utils.py` — add `get_open_question_count` and `load_open_question`

**Depends on:** 45.1
**Blocks:** 45.3

**Scope hard limits:**
- Do NOT change the ratio/selection logic yet — that is 45.3
- Do NOT touch evaluation.py — open question grading already works
- Do NOT change AgentState schema — all required fields already exist (is_mcq, pending_test_question, pending_test_slug)

**Testing — done when:**
- [ ] `select_open_question` returns `(slug, index)` for a valid state
- [ ] `load_open_question` loads display text from the correct knowledge-base file
- [ ] `test_delivery.py` has a reachable path that sets `is_mcq=False`
- [ ] Existing MCQ path unchanged — all existing tests pass
