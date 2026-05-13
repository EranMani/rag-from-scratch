# LangGraph State Machine — Stateful Agent Orchestration

## Core Concept

LangGraph turns a stateless HTTP request into a stateful, multi-step agent pipeline. Instead of writing one function that does everything, you design a **State Machine** where each node performs one focused task and passes its results forward through a shared state envelope.

## StateGraph & AgentState

```python
builder: StateGraph = StateGraph(AgentState)
```

- `StateGraph` creates a directed graph of nodes connected by edges.
- `AgentState` (a `TypedDict`) is the single state object that passes through every node and conditional edge.
- A node **reads** specific keys from state and **writes** specific keys back — it never side-effects on keys it doesn't own.

## The State Envelope Pattern

`AgentState` groups fields by lifecycle stage:

| Stage | Keys |
|-------|------|
| Turn input | `messages`, `question`, `user_id`, `user_level` |
| Retrieval | `docs`, `retrieval_source` |
| Generation | `answer` |
| Assessment | `topic_scores_delta`, `identified_gaps`, `assessment_error`, `test_mode`, `pending_test_question`, `pending_test_slug`, `test_answer_score` |
| Observability | `trace_id`, `latency_ms`, `cache_hit` |

Each node declares its own contract (what it reads, what it writes). This makes the system composable — you can add/remove nodes without cascading changes.

## The `add_messages` Reducer

```python
messages: Annotated[list[BaseMessage], add_messages]
```

The `add_messages` annotation tells LangGraph to **append** returned messages to the existing list, rather than replacing it. This is how conversation history accumulates across turns without explicit bookkeeping.

## Persistence via Checkpointers

```python
graph.astream_events(initial_state, config=config, version="v2")
# where config = {"configurable": {"thread_id": session_id}}
```

- `thread_id` replaces a traditional session_id. LangGraph's `MemorySaver` checkpointer uses it to persist and replay state across turns.
- This brings **stateful memory to traditionally stateless web applications** — the graph can be paused, saved, and resumed at any point.
- `session_id` is NOT a field in AgentState. It exists only in the invocation config.

## Node Contract Design

Every node follows the same pattern:

1. Read specific keys from `AgentState`
2. Perform its computation (LLM call, DB query, scoring)
3. Return a dict with **only** the keys it owns
4. Never modify keys belonging to other nodes

This ensures nodes are independently testable, replaceable, and composable.

## Edges & Routing

- **Static edges** (`add_edge`): unconditional A → B transitions.
- **Conditional edges** (`add_conditional_edges`): a router function inspects state and returns the next node name. Used when the path depends on runtime values (e.g., `assessment_error`).

## Recursion Limit

```python
.with_config({"recursion_limit": 10})
```

A defensive guard against infinite loops from graph wiring bugs or future conditional edge cycles. In a linear 4-node graph this can never be reached legitimately.

## Key Takeaway

As an AI Engineer building with LangGraph, you aren't writing a monolithic handler — you're designing a state machine where:
- State is explicit and typed
- Each node has clear ownership boundaries
- Persistence is built-in (not bolted on)
- The graph topology is inspectable and visualizable
