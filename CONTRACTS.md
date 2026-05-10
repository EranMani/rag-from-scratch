# CONTRACTS.md — Project-wide interface contracts

> Maintained by Viktor after each gate pass that validates or extends a pattern.
> Read by the pre-commit linter (Step 7.5) before the gate wave fires.
> Agents: load this file when building a new node, service function, or async route.
> Last updated: 2026-05-10 — Commit 12

---

## Node Interface

Every LangGraph node must conform to this signature:

```python
async def [name]_node(state: AgentState) -> dict:
```

- Parameter: `state: AgentState` — exactly one, typed
- Return: `dict` — keys must be a subset of `AgentState` fields only
- Async: required for all nodes that call an LLM or perform I/O
- Sync-only nodes (pure computation, no I/O): acceptable, but uncommon

## LLM Invocation

```python
# Correct — async, per-invocation provider lookup
llm = get_provider().get_llm()        # called inside the node body
response = await llm.ainvoke(messages)

# Banned — module-level singleton
llm = get_provider().get_llm()        # at module level ← BANNED: freezes before CB changes

# Banned — synchronous invoke
response = llm.invoke(messages)       # ← BANNED: breaks streaming, stalls event loop
```

`get_provider()` must be called inside the node function body on every invocation.

## Blocking I/O in Async Contexts

```python
# Correct — dispatched off the event loop, hoisted outside generators
result = await asyncio.to_thread(blocking_fn, arg1, arg2)

# Correct — hoisted before the async generator starts
user_level = await asyncio.to_thread(get_user_level, user_id)
async def generate_stream():
    async for event in rag_graph.astream_events(...):   # no blocking calls in here
        ...

# Banned — blocking call inside async generator body
async def generate_stream():
    data = blocking_fn(arg)   # ← BANNED: stalls event loop, breaks token streaming
```

## State Key Constraints

| Key | Valid values | Enforced by |
|---|---|---|
| `user_level` | `novice`, `beginner`, `intermediate`, `advanced`, `expert` | `Pydantic Literal` in `AssessmentOutput` |
| `cache_hit` | `hit`, `miss`, `bypass` | `Pydantic Literal` in `AgentState` |
| `retrieval_source` | `chroma`, `bm25` | Set by `retrieve_node` only |

No value outside these sets may be written to these keys. LLM output that produces an out-of-range value raises `ValidationError` at parse time — this is by design.

## Error Handling — Assessment-class Nodes

```python
# Correct — try/except wraps the entire output construction block
try:
    result = AssessmentOutput(...)     # parse failures are real failure modes
    state_update = {"topic_scores_delta": result.topic_scores_delta, ...}
except Exception:
    state_update = {"assessment_error": True, "topic_scores_delta": {}, ...}
    # fallback — does NOT raise; turn completes gracefully

# Wrong — wrapping only the LLM call misses construction failures
try:
    raw = await llm.ainvoke(...)       # ← insufficient scope
except Exception:
    ...
output = AssessmentOutput(**raw)       # ← parse failures escape the handler
```

## Dynamic SQL

```python
# Correct — frozenset guard before any SQL runs
_ALLOWED_X_COLUMNS: frozenset[str] = frozenset({"col1", "col2", "col3"})

def update_x(id: str, **fields) -> None:
    invalid = set(fields) - _ALLOWED_X_COLUMNS
    if invalid:
        raise ValueError(f"update_x: unknown column(s) {invalid!r}")
    # ... build SET clause, execute
```

Every function that builds SQL dynamically from caller-supplied keys **must** have a
module-scoped `_ALLOWED_X_COLUMNS` frozenset. System-managed columns (`updated_at`,
`created_at`) are excluded from all caller-facing allowlists.

This is the project-wide standard established in Commit 05 (Decision #27).

## SSE Event Schema (locked from Commit 10)

```json
// Token event — emitted per LLM token
{ "type": "token", "content": "<text>" }

// Done event — emitted once at graph end
{ "type": "done", "user_level": "<level>", "assessed_topics": { "<slug>": <float> } }
```

The public key is `assessed_topics` — **never** `topic_scores_delta`.
This contract is locked. Aria's Commit 19 render depends on it.

## Auth Dependencies

| Scenario | Dependency | Behavior |
|---|---|---|
| No anonymous use case | `Depends(get_current_user)` | Returns 401 if no valid JWT |
| Anonymous + authenticated | `Depends(current_user_optional)` | Returns `None` if no token |

Never accept `user_id` as a request parameter. Always extract from verified JWT:
```python
user_id: str = current_user["id"]   # correct — from JWT
user_id = request.query_params["user_id"]  # ← BANNED — caller-controlled
```

## AgentState Type Introspection

```python
# Correct — preserves Annotated wrapper (required for add_messages reducer)
from typing import get_type_hints
hints = get_type_hints(AgentState, include_extras=True)

# Wrong — strips Annotated, loses add_messages reducer silently
hints = get_type_hints(AgentState)
```

Any code that introspects `AgentState` annotations must pass `include_extras=True`.
`from __future__ import annotations` stores annotations as strings; without
`include_extras=True`, `get_type_hints()` returns `list[BaseMessage]` instead of
`Annotated[list[BaseMessage], add_messages]`, and the graph builder silently receives
an undecorated type.
