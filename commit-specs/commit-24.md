# Commit 24 Spec — `assessment-engine-rewrite`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 24 — `assessment-engine-rewrite`

**Commit message:** `feat: curriculum-driven assessment — test-answer scoring replaces question-inference`

**Body:**
Full rewrite of the assessment pipeline. The broken model (LLM infers understanding
from question content) is replaced with a curriculum-driven model (LLM administers
curriculum test questions and derives scores from user answers).

**Spec reference:** `docs/scoring-model.md` (Commit 23) is the product contract.
**Curriculum reference:** `knowledge-base/curriculum/` (Commit 22) is the question bank and rubric source.

**What changes:**

`assess_node` stops observing question+answer pairs. It now operates in two modes:
- **Test mode:** selects a curriculum question for the current topic, injects it into
  the response flow, sets `test_mode=True` and `pending_test_question`
- **Evaluation mode:** evaluates the user's answer to a prior test question against
  the rubric, returns a score delta derived from test performance

`assessment_prompt` is fully rewritten: the new prompt evaluates a user's test answer
against a rubric from `knowledge-base/curriculum/questions/[slug].md`, not the content
of a Q&A pair. The LLM receives the test question, the rubric, and the user's answer —
it returns a structured evaluation (correct / partial / incorrect + confidence).

`AgentState` gains 4 new fields to support the test flow:
- `test_mode: bool` — True when this turn is a test administration or answer evaluation
- `pending_test_question: str | None` — the test question injected this turn (if any)
- `pending_test_slug: str | None` — which topic slug is being tested this turn
- `test_answer_score: float | None` — score from evaluating user's answer (0.0 / 0.5 / 1.0)

`TopicScoresDelta` schema is NOT changed in this commit — that is Rex's Commit 25.
Nova's node produces deltas compatible with the existing `dict[str, float]` contract;
Rex's rewrite of `compute_topic_scores` consumes the new semantics.

**Assignee:** Nova

**Files touched:**
- `src/agents/nodes/assess.py` — full rewrite
- `src/agents/prompts/assessment.py` — full rewrite
- `src/agents/state.py` — add 4 new fields to `AgentState`
- `src/agents/graph.py` — update conditional edges if `test_mode` changes routing
- `tests/test_assess_node.py` — update and extend for new behavior (no test may assert question-inference behavior)

**Depends on:** Commit 23 (`docs/scoring-model.md` must exist before implementation begins)

**Testing — done when:**
- [ ] Test mode turn: `assess_node` returns a curriculum question in `pending_test_question` with correct `pending_test_slug`
- [ ] Evaluation mode turn: `assess_node` evaluates user answer and returns non-zero `test_answer_score`
- [ ] Score delta is derived from `test_answer_score`, not from question content observation
- [ ] `assessment_error` fallback path still works — graph never terminates on failure
- [ ] All prior `test_assess_node.py` tests updated; no test asserts the old Q&A-observation behavior
- [ ] `AgentState` has all 4 new fields with correct types
