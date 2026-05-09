# Commit 07 Spec — `langgraph-state-schema`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 07 — `langgraph-state-schema`

**Commit message:** `feat: AgentState TypedDict and AssessmentOutput model for LangGraph graph`

**Body:**
Defines the full state schema for the LangGraph graph. This TypedDict is designed for
the entire arc (commits 07–17) — all Phase 4 fields are present from the start.
Retroactive state schema changes cascade through the compiled LangGraph graph; designing
it completely here prevents that.

Architecture redesigned by Eran Mani ahead of Commit 07: uses LangGraph's native message
management (`Annotated[list[BaseMessage], add_messages]`) instead of a plain
`conversation_history: str` — this is the prerequisite for production-grade streaming
responses via `graph.astream_events()` (wired in Commit 10). `session_id` is removed
from state entirely — it is passed as `thread_id` in the graph config, letting LangGraph's
`MemorySaver` checkpointer handle cross-turn persistence automatically.

`AgentState` fields:
- `messages: Annotated[list[BaseMessage], add_messages]` — LangGraph native message list;
  the `add_messages` reducer appends incoming messages rather than replacing. Replaces
  `conversation_history: str`. The current user question arrives here as a `HumanMessage`
  before graph entry; prior turns are reconstructed from the checkpointer via `thread_id`.
- `question: str` — current user question, convenience field so `retrieve_node` can
  query without unpacking `messages[-1].content`
- `user_id: str | None` — from JWT; `None` = anonymous
- `docs: list` — retrieved LangChain Documents
- `retrieval_source: str` — `"chroma"` or `"bm25"`
- `answer: str` — complete generated answer (written by `generate_node`, read by `assess_node`
  and included in the SSE `done` event)
- `user_level: str` — `"novice"` | `"beginner"` | `"intermediate"` | `"advanced"` | `"expert"`;
  loaded from profile before graph entry
- `topic_scores_delta: dict[str, float]` — sparse dict of assessed modules this turn
- `identified_gaps: list[str]` — module slugs where understanding is low
- `assessment_error: bool` — True if `assess_node` failed (triggers fallback edge)
- `trace_id: str`
- `latency_ms: int`
- `cache_hit: str`

**`session_id` is NOT a field.** It is passed as the graph invocation config:
```python
config = {"configurable": {"thread_id": session_id}}
graph.astream_events(initial_state, config=config, version="v2")
```

`AssessmentOutput` Pydantic model (used by `assess_node` for structured LLM output parsing):
```python
class AssessmentOutput(BaseModel):
    topic_scores_delta: dict[str, float]
    identified_gaps: list[str]
    user_level: str
```
This is a per-turn LLM delta — it captures what the LLM assessed this turn, not a DB read.
`profile_update_node` (Commit 15) applies these deltas to the persistent `user_profiles` table.

Module slugs (the valid keys for `topic_scores_delta`):
`rag_fundamentals`, `vector_databases`, `langchain`, `chunking_strategies`,
`retrieval_methods`, `production_patterns`

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/__init__.py` (new, empty)
- `src/agents/state.py` (new)
- `src/agents/nodes/__init__.py` (new, empty)

**Depends on:** 04 (profile schema must be defined before designing state fields)

**Testing — done when:**
- [ ] `from agents.state import AgentState, AssessmentOutput` imports without error
- [ ] All required fields are present and typed correctly
- [ ] `messages` is typed as `Annotated[list[BaseMessage], add_messages]` — verify with `get_type_hints(AgentState)`
- [ ] `session_id` is NOT present in `AgentState` (it must not exist as a field)
- [ ] `add_messages` reducer accumulates correctly: passing `[HumanMessage("hello")]` then `[AIMessage("world")]` results in a list of both messages, not a replacement
- [ ] `AssessmentOutput` validates correctly with a sample LLM response dict
- [ ] `AssessmentOutput` raises `ValidationError` on missing required fields
