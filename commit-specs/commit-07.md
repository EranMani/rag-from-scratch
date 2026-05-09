# Commit 07 Spec — `langgraph-state-schema`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 07 — `langgraph-state-schema`

**Commit message:** `feat: AgentState TypedDict and AssessmentOutput model for LangGraph graph`

**Body:**
Defines the full state schema for the LangGraph graph. This TypedDict is designed for
the entire arc (commits 07–17) — all Phase 4 fields are present from the start.
Retroactive state schema changes cascade through the compiled graph; designing it
completely here prevents that.

`AgentState` fields:
- `question: str`
- `session_id: str`
- `user_id: str | None`
- `conversation_history: str` — formatted from `SessionMemory` before graph entry
- `docs: list` — retrieved LangChain Documents
- `retrieval_source: str` — `"chroma"` or `"bm25"`
- `answer: str`
- `user_level: str` — `"novice"` | `"beginner"` | `"intermediate"` | `"advanced"` | `"expert"`
- `topic_scores_delta: dict[str, float]` — sparse dict of assessed modules this turn
- `identified_gaps: list[str]` — module slugs where understanding is low
- `assessment_error: bool` — True if assess_node failed (triggers fallback edge)
- `trace_id: str`
- `latency_ms: int`
- `cache_hit: str`

`AssessmentOutput` Pydantic model (used by `assess_node` for structured LLM output parsing):
```python
class AssessmentOutput(BaseModel):
    topic_scores_delta: dict[str, float]
    identified_gaps: list[str]
    user_level: str
```

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
- [ ] `AssessmentOutput` validates correctly with a sample LLM response dict
