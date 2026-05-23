# Commit 52 Spec — `ai-question-generation`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**
> **Note:** New commit added in replan 2026-05-23 — the AI synthesis layer. Bank must have 5/tier depth (C51) before this commit runs.

---

### Commit 52 — `ai-question-generation`

**Commit message:** `feat(EranMani): LLM-synthesized question generation layer in select_test_question`

**Body:**
Requested by Eran Mani, our team lead: extend `select_test_question()` with an LLM synthesis layer that generates hybrid questions referencing the existing question bank. Each session, the LLM reads the bank for the current slug and mastery level, synthesizes N new questions, validates output structure, and caches the result for the session. Falls back to bank questions silently on failure. This is the "AI tailors to you" feature — non-deterministic by design.

**Assignee:** Nova

**Files touched:**
- `src/rag/graph/nodes/test_delivery.py` — insert synthesis call between slug selection and delivery
- `src/rag/graph/state.py` — add `generated_question_pool: dict[str, list] | None` to `AgentState`
- `src/rag/graph/nodes/question_generation.py` (new) — LLM call, prompt, output validation, fallback logic
- `tests/test_question_generation.py` (new) — generation success, validation failure + fallback, session caching

**Depends on:** 51 (bank must have ≥ 5 questions per tier as quality anchors before generation is useful)
**Parallel-eligible with:** 51 (C52 is code-only; C51 is content-only — no shared files)

**Design (from Nova's prior assessment):**

Integration point — NOT a new LangGraph node. Extend `select_test_question()`:
```
select_test_question()
  → select slug                           [existing]
  → check generated_question_pool cache   [new]
  → if cache miss: load bank + call LLM   [new]
  → validate generated output             [new]
  → store in generated_question_pool      [new]
  → sample from pool                      [new]
  → deliver question                      [existing]
```

LLM prompt structure:
- SYSTEM: "You are a curriculum question writer for a RAG learning platform."
- Provide the existing bank questions for (slug, mastery_level) as examples
- Request N=3 new questions that synthesize, reframe, or extend the existing ones
- Enforce: same difficulty tier, same topic slug, MCQ format with 4 options
- Require: "Why X is wrong" explanation for each distractor
- Forbid: verbatim copies, topics outside the slug, hints at the correct answer in the stem

Output format: structured JSON list of question objects (question, options, correct, explanations)

Validation (reject and fall back if any check fails):
- [ ] Exactly 4 options (A–D)
- [ ] Exactly 1 correct answer key
- [ ] "Why wrong" explanation present for all 3 distractors
- [ ] No distractor explanation that is circular (repeats the question stem)
- [ ] Topic slug present and matches requested slug

Caching:
- Key: `f"{slug}:{mastery_level}"` stored in `AgentState.generated_question_pool`
- Cache is session-scoped — persists across questions in the same session, regenerated on next session
- Cache populated on first question delivery for a slug, reused for subsequent questions in the same session

Fallback:
- If LLM call fails, times out, or output fails validation → fall through to bank question silently
- No error surfaced to user
- Log the failure for observability

**AgentState changes:**
```python
generated_question_pool: dict[str, list] | None = None
```
Key format: `"slug:mastery_level"` → list of generated question dicts

**Viktor will check:**
- `generated_question_pool` typed correctly (`dict[str, list] | None`, not bare `dict`)
- Fallback path is explicitly tested (not just happy path)
- Session cache does not persist across sessions (cleared on new conversation thread)
- No blocking LLM call on the async event loop

**Testing — done when:**
- [ ] Generated questions served when LLM call succeeds and output validates
- [ ] Fallback to bank question when validation fails — no error raised
- [ ] `generated_question_pool` persists within a session (second question from same slug uses cache)
- [ ] Cache cleared on new session (new `thread_id`)
- [ ] All existing tests still pass
