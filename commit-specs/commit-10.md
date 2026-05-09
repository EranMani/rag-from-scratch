# Commit 10 Spec — `langgraph-graph-assembly`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 10 — `langgraph-graph-assembly`

**Commit message:** `feat: assemble LangGraph graph and replace chain.py pipeline`

**Body:**
Wires `retrieve_node` and `generate_node` into a compiled LangGraph graph.
Replaces `run_rag_pipeline()` in `chain.py` with `graph.invoke()`.

Graph invocation is synchronous (`graph.invoke()` inside `asyncio.to_thread()` — same
pattern as the current `run_rag_pipeline` call in `chat.py` and `ui.py`). No change
to the thread dispatch pattern.

The wrapper function preserves the existing return shape:
`{"answer", "cache_hit", "chunks", "latency_ms", "trace_id"}` — `chat.py` and
`ui.py` unpack this directly and must not break.

Cache key strategy: the existing query-level Redis cache is retained for this commit.
Cache key invalidation per user profile is addressed in Commit 17 when adaptive
responses are active. For commits 10–16, cached responses may be shared across users
with different profiles — this is a known temporary limitation, logged here explicitly.

**Handoff consumed from Commit 03:** `conversation_history` threading MUST be wired.
`SessionMemory.format_history(session_id)` is called BEFORE `graph.invoke()` and
passed into the initial `AgentState` as `conversation_history`. This is a named
deliverable of this commit — not optional.

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/graph.py` (new)
- `src/rag/chain.py` (update `run_rag_pipeline` to call `graph.invoke`)

**Depends on:** 08, 09

**Testing — done when:**
- [ ] End-to-end: send a question via `/api/chat`, receive a valid answer
- [ ] `chat.py` and `ui.py` unpack the response without KeyError
- [ ] `conversation_history` is populated in state from `SessionMemory` before graph runs
- [ ] Graph handles ChromaDB circuit breaker OPEN (falls back to BM25 via retrieve_node)
