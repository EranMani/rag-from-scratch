# Commit 52.1 — `state-mutation-refactor`

**Assignee:** Nova (ai-engineer)
**Depends on:** Commit 52 (ai-question-generation)
**Status:** pending

---

## What This Commit Does

Refactors `_deliver_mcq` in `src/agents/assessment/test_delivery.py` to eliminate the direct
state mutation `state["generated_question_pool"] = pool` introduced in Commit 52. Converts the
function to return a 3-tuple and threads the pool update through the LangGraph-correct return-dict
path. Also tightens the type annotation for `generated_question_pool` in `src/agents/state.py`.

This commit contains no behavior change — the fallback chain, timeout, validation, and session
cache semantics are all identical to C52. The only change is structural: removing a mutation
that violated the LangGraph state-update-via-returned-dict contract.

---

## Background (Viktor Advisory — C52 Gate)

`_deliver_mcq` currently mutates `state["generated_question_pool"] = pool` before returning,
so that `select_test_question` can read the updated pool and include it in its returned dict.
Viktor flagged this as a fragile pattern — LangGraph state updates must flow through the dict
returned by a node, not via in-place mutation of the input state. The mutation is safe in C52
because `generate_questions()` never returns between the mutation and the return, but it obscures
the data flow and sets a wrong precedent for future contributors.

---

## Files to Change

### `src/agents/assessment/test_delivery.py`

**Change `_deliver_mcq` signature and return type:**

Before:
```python
async def _deliver_mcq(
    state: AgentState,
    slug: str,
    q_idx: int,
    mastery_level: str | None,
) -> tuple[str | None, str | None]:
```

After:
```python
async def _deliver_mcq(
    state: AgentState,
    slug: str,
    q_idx: int,
    mastery_level: str | None,
) -> tuple[str | None, str | None, dict[str, list[dict[str, Any]]] | None]:
```

**Remove the state mutation and return the pool instead:**

Remove:
```python
state["generated_question_pool"] = pool  # type: ignore[index]
```

Change the return at the generated-pool branch:
```python
return display_text, q["correct"], pool
```

At the bank-fallback branch and the None/None branch, return `None` as the third element:
```python
return load_mcq_question_for_difficulty(slug, q_idx, mastery_level) + (None,)
# → but simpler to unpack:
text, answer = load_mcq_question_for_difficulty(slug, q_idx, mastery_level)
return text, answer, None
```

**Update the call site in `select_test_question`:**

Before:
```python
display_question_text, correct_answer = await _deliver_mcq(
    state, slug, q_idx, mastery_level
)
```

After:
```python
display_question_text, correct_answer, updated_pool = await _deliver_mcq(
    state, slug, q_idx, mastery_level
)
```

Pass `updated_pool` to `build_selection_result`:
```python
return build_selection_result(
    ...
    generated_question_pool=updated_pool,
)
```

### `src/agents/state.py`

**Tighten type annotation:**

Before:
```python
generated_question_pool: dict[str, list] | None
```

After:
```python
generated_question_pool: dict[str, list[dict[str, Any]]] | None
```

Add `Any` to the import if not already present:
```python
from typing import Annotated, Any, Literal
```

---

## Test Gates

- All existing tests must continue to pass (no behavior change)
- The mock in `tests/test_question_generation.py` for `_deliver_mcq` may need updating to match the new 3-tuple return shape — verify the mock is consistent
- Run: `pytest tests/test_question_generation.py tests/test_mastery_routing.py -v`

---

## Quality Gates

- **Viktor:** new logic change (function signature + return type)
- **Sage:** not triggered — no auth surface, no user input trust boundary
- **Quinn:** not triggered — no new behavior; same paths, same coverage
- **Mira:** not triggered — no user-facing change

---

## Commit Message

```
refactor(EranMani): remove state mutation from _deliver_mcq; return 3-tuple with pool

Requested by EranMani: converts _deliver_mcq to return (display_text, correct_answer,
updated_pool) 3-tuple instead of mutating state["generated_question_pool"] directly.
Also tightens dict[str,list] → dict[str,list[dict[str,Any]]] type annotation.
No behavior change — deferred fix from C52 Viktor advisory.
```
