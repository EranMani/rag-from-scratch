# Commit 35 — `mcq-assessment-engine`
# Assignee: Nova (ai-engineer)
# Phase: Progression System · Wave E (parallel with Commit 36; depends on Commits 33 + 34)
# Status: pending

---

## Goal

Replace open-ended question delivery in `assess_node` with MCQ format. The existing
flow uses rubric-based LLM evaluation for assessment. This commit replaces it with
deterministic binary scoring (answer-key comparison) using the MCQ question banks
created in Commit 33. No LLM call is needed for MCQ evaluation.

---

## Context

**Commits this depends on:**
- Commit 33: MCQ question files at `knowledge-base/curriculum/questions/mcq/[slug].md`,
  5 questions each, format defined in `mcq-format.md`
- Commit 34: `_select_test_slug()` is now phase-gated — MCQ engine inherits the phase gate

**From Lara's Commit 33 handoff:**
- Answer key field: `**Correct answer:** [A|B|C|D]`
- Binary scoring only — no partial credit for MCQ
- Session minimum of 3 questions still applies (inherited from gates.md)

**Key design decision:** Open-ended questions remain in the knowledge base (used for
curriculum reference), but `assess_node` no longer serves them as test questions.
MCQ is the assessment format going forward until an open-ended scorer is validated.

**Cross-domain touch:** `src/rag/chain.py` is a Nova-adjacent file (owned by Nova per
her interfaces). Adding `is_mcq` to `ChatResponse` is required so Aria can render
MCQ option buttons in Commit 37.

---

## Files to Modify

| File | Action | What |
|---|---|---|
| `src/agents/state.py` | **update** | Add `is_mcq: bool` and `pending_mcq_correct_answer: str \| None` fields to `AgentState` |
| `src/agents/nodes/assess.py` | **update** | Add MCQ loaders; replace open-ended test delivery with MCQ delivery; add binary MCQ evaluator path |
| `src/rag/chain.py` | **update** | Add `is_mcq: bool = False` to `ChatResponse`; extract from state in `build_chat_response` |

No new files.

---

## AgentState New Fields (state.py)

```python
is_mcq: bool
"""True when the pending test question is MCQ format (A/B/C/D options).
False for open-ended questions and when no question is pending."""

pending_mcq_correct_answer: str | None
"""The correct answer letter ('A', 'B', 'C', or 'D') for the current MCQ question.
Set when assess_node delivers an MCQ question; cleared after evaluation.
None when no MCQ question is pending."""
```

Add both fields to `AgentState` TypedDict. Add both to `initial_state` in `chat.py`
with defaults `is_mcq=False` and `pending_mcq_correct_answer=None`.

**chat.py cross-domain note:** `chat.py` is Nova's file. Adding two fields to
`initial_state` is a mechanical extension of the existing pattern — not a logic change.

---

## assess.py — New and Modified Functions

### New: `_load_mcq_question(slug: str, question_index: int) -> tuple[str, str]`

Loads an MCQ question from `knowledge-base/curriculum/questions/mcq/[slug].md`.

Returns `(display_text, correct_answer)` where:
- `display_text` = the question text + formatted options block (ready to send as AI message)
- `correct_answer` = the answer letter extracted from `**Correct answer:** X` field

Parsing rules:
- Split file into question blocks by `## MCQ-` headers
- Extract `**Question:**` text
- Extract `**Options:**` block (A. through D.)
- Extract `**Correct answer:**` letter (first word after the colon, stripped, uppercased)
- Modulo wrap on `question_index` (5 questions per file)
- Raises `FileNotFoundError` if mcq file for slug doesn't exist
- Raises `ValueError` if question block is malformed (missing required fields)

Display text format (exactly as rendered in chat):
```
Knowledge check: [Question text]

A. [Option A]
B. [Option B]
C. [Option C]
D. [Option D]
```

### New: `_evaluate_mcq_answer(user_message: str, correct_answer: str) -> float`

Deterministic binary evaluator — no LLM call.

```python
def _evaluate_mcq_answer(user_message: str, correct_answer: str) -> float:
    # Extract the first A/B/C/D letter from the user's message (case-insensitive)
    # User may type "A", "A.", "Option A", or full option text
    match = re.search(r'\b([A-Da-d])\b', user_message.strip())
    if match and match.group(1).upper() == correct_answer.upper():
        return 1.0
    return 0.0
```

Returns 1.0 for correct, 0.0 for incorrect. No partial credit.

### Modified: `_select_test_question(state)`

Replace `_load_question_text()` call with `_load_mcq_question()`. On success, set:
- `pending_test_question` = display_text (question + options)
- `pending_test_slug` = slug
- `is_mcq` = True
- `pending_mcq_correct_answer` = correct_answer letter
- `test_mode` = True

On `FileNotFoundError` or `ValueError`: log warning, set `assessment_error=True`,
return without a test question (same fallback as existing open-ended failure path).

### Modified: `_evaluate_answer(state)`

Branch on `is_mcq`:

```python
if state.get("is_mcq"):
    user_msg = (state.get("messages") or [])[-1].content or ""
    correct = state.get("pending_mcq_correct_answer") or ""
    score = _evaluate_mcq_answer(user_msg, correct)
    delta = {pending_slug: score} if score > 0.0 else {}
    return _build_eval_result(
        topic_scores_delta=delta,
        identified_gaps=[],   # MCQ evaluation does not produce gap inference
        assessment_error=False,
        test_answer_score=score,
    )
# else: existing LLM evaluation path (keep as-is for potential future use)
```

### Modified: `_build_test_result` and `_build_eval_result`

Add `is_mcq` and `pending_mcq_correct_answer` to both result builder functions.
`_build_eval_result` always clears both (`is_mcq=False`, `pending_mcq_correct_answer=None`).

---

## chain.py — ChatResponse Update

```python
class ChatResponse(BaseModel):
    answer: str = ""
    user_level: str | None = None
    assessed_topics: dict[str, float] = {}
    test_question: str | None = None
    is_mcq: bool = False          # NEW: True when test_question is MCQ format
```

`build_chat_response`:
```python
return ChatResponse(
    answer=state.get("answer", ""),
    user_level=state.get("user_level"),
    assessed_topics=state.get("topic_scores_delta", {}),
    test_question=state.get("pending_test_question"),
    is_mcq=bool(state.get("is_mcq", False)),  # NEW
)
```

The SSE `done` event now includes `"is_mcq": true|false`. Aria reads this in Commit 37
to decide whether to render MCQ option buttons or keep the standard text input.

---

## Quality Gate Triage

| Reviewer | Decision | Reason |
|---|---|---|
| Viktor | **run** | New logic paths, new state fields, cross-file changes |
| Sage | **skip** | No auth, secrets, external API; MCQ evaluation is deterministic in-process |
| Quinn | **run** | Wave trigger — this is commit ~35, within the every-5-commit cadence; covers accumulated commits 31–35 |
| Mira | **skip** | Internal engine change; MCQ rendering is Aria's Commit 37 |
| Ryan | **run** | Always; full entry — new engine pattern, non-obvious regex extraction, cross-file handoff |

---

## Test Gate

Existing test suite must pass. Nova must add tests covering:

**MCQ loader:**
- `_load_mcq_question` returns correct `(display_text, correct_answer)` for a valid slug
- `display_text` contains "Knowledge check:" prefix and all 4 options (A–D)
- `correct_answer` is exactly one of 'A', 'B', 'C', 'D'
- `FileNotFoundError` raised for unknown slug
- `ValueError` raised for malformed question block
- Modulo wrapping works (question_index=5 returns question 0 for a 5-question file)

**MCQ evaluator:**
- `_evaluate_mcq_answer("B", "B")` → 1.0
- `_evaluate_mcq_answer("b", "B")` → 1.0 (case-insensitive)
- `_evaluate_mcq_answer("A", "B")` → 0.0
- `_evaluate_mcq_answer("Option B is correct", "B")` → 1.0 (letter extracted from text)
- `_evaluate_mcq_answer("none of the above", "B")` → 0.0

**Integration: `_evaluate_answer` with `is_mcq=True`:**
- When `is_mcq=True`, result uses binary score (no LLM)
- `is_mcq` and `pending_mcq_correct_answer` are cleared in eval result
- `identified_gaps` is empty list for MCQ evaluation (no gap inference)

---

## Handoff Outputs

**→ Aria (Commit 37 `mcq-chat-ui`):**
- SSE done event now includes `"is_mcq": true|false`
- When `is_mcq=true`, `test_question` field contains the MCQ text with A–D options
- Aria should parse options from `test_question` using "^[A-D]\\." line pattern
- User selection should be submitted as the single letter ("A", "B", "C", or "D")

**→ Nova (Commit 36 `onboarding-level-check`):**
- `_load_mcq_question(slug, index)` is the function to use for diagnostic question loading
- Same format, same file path convention — onboarding diagnostic reads the same MCQ banks
