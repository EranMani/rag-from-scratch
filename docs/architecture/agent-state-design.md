# Agent State Design — Field Selection Criteria

## Core Concept

The `AgentState` is the **contract** that binds every node in the LangGraph graph. Choosing which fields belong in the state is one of the most critical architectural decisions when building an agent — get it wrong and you face cascading schema changes, broken node interfaces, and invisible data flow bugs.

This document captures the criteria used to decide what enters `AgentState` and why.

## Decision Criteria

### 1. Lifecycle Stage Ownership

Every field maps to a specific phase in the request lifecycle. Fields are grouped by when they are **produced** and when they are **consumed**:

| Stage | Fields | Produced By | Consumed By |
|-------|--------|-------------|-------------|
| Input | `messages`, `question`, `user_id`, `user_level` | API layer / graph entry | retrieve_node, generate_node |
| Intermediate | `docs`, `retrieval_source` | retrieve_node | generate_node |
| Output & Assessment | `answer`, `topic_scores_delta`, `identified_gaps` | generate_node, assess_node | profile_update_node, SSE response |
| Test Flow | `test_mode`, `pending_test_question`, `pending_test_slug`, `test_answer_score` | assess_node | assess_node (next turn) |
| Observability | `trace_id`, `latency_ms`, `cache_hit` | instrumentation layer | logging, monitoring |

The question to ask: **does a downstream node need this value?** If a piece of data is produced and consumed entirely within one function, it stays local to that function. It enters the state only when it must cross a node boundary.

### 2. Cross-Turn Persistence Requirements

Some fields must survive between conversation turns. LangGraph's checkpointer (keyed by `thread_id`) serialises and restores the full state. Fields that require persistence:

```python
test_mode: bool
pending_test_question: str | None
pending_test_slug: str | None
```

These are critical because they let the agent "remember" it is in the middle of a test, even though the HTTP API is stateless. Without them in the state, the graph would lose context between the turn that poses a question and the turn that evaluates the answer.

Conversely, `session_id` is deliberately **not** a state field — it exists only in the invocation config (`thread_id`), because no node ever reads or writes it.

### 3. LLM Provider Constraints (Structured Output Compatibility)

Technical limitations of AI providers directly shape state-adjacent schemas:

```python
class TopicScoresDelta(BaseModel):
    vector_databases: float = 0.0
    retrieval_methods: float = 0.0
    # ... one explicit field per valid slug
```

A natural design would be `dict[str, float]`. However, OpenAI's structured output endpoint rejects any schema containing `additionalProperties`, which is what a generic dict serialises to. The explicit-field approach generates a **closed object schema** that passes validation.

This constraint propagates into `AgentState`: the `topic_scores_delta` field is typed as `dict[str, float]` (the sparse, filtered version), while the LLM output uses the explicit `TopicScoresDelta` class. The conversion happens in `assess_node` before writing to state.

### 4. Observability Without Side Effects

Fields that don't influence the user-facing answer but are essential for operating the system in production:

| Field | Purpose |
|-------|---------|
| `trace_id` | Correlates logs across nodes for a single request |
| `latency_ms` | Measures end-to-end performance; surfaces bottlenecks |
| `cache_hit` | Tracks retrieval cache effectiveness |
| `assessment_error` | Signals assess_node failure; triggers fallback routing |

These fields make the system **debuggable**. Without them in the state, you'd need external correlation mechanisms or instrumentation wrappers around every node.

## The Checklist

When considering whether a new field belongs in `AgentState`:

1. **Cross-node dependency** — Does a future node need this data? → Add to state.
2. **Cross-turn memory** — Must this persist to the next conversation turn? → Add to state.
3. **Operational visibility** — Is this needed for logging, metrics, or debugging? → Add to state.
4. **Provider compatibility** — Does the schema satisfy LLM structured output constraints?
5. **Single-node scope** — Is the data produced and consumed within one node? → Keep it local.

## Why Declare Everything Upfront

From the module docstring:

> All Phase 4 fields are declared here to avoid retroactive schema changes cascading through the compiled graph.

LangGraph compiles the graph at startup. Adding a field later means every node that touches the state must be re-validated, every test fixture must be updated, and every checkpoint in the database becomes structurally incompatible. Declaring the full schema upfront — even fields not yet consumed — prevents this cascade.

## Key Takeaway

`AgentState` is not a grab bag of variables. It is a deliberately designed contract where every field earns its place by satisfying at least one of: cross-node data flow, cross-turn persistence, observability, or provider compatibility. The goal is a schema that is **complete from day one** — stable enough that adding new nodes never requires touching the state definition.
