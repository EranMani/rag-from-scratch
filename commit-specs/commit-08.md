# Commit 08 Spec — `langgraph-retrieve-node`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 08 — `langgraph-retrieve-node`

**Commit message:** `feat: LangGraph retrieve_node wrapping existing retriever`

**Body:**
Wraps the existing `retrieve()` function from `src/rag/pipeline/retriever.py` as a
LangGraph node. Reads `question` from `AgentState`, writes `docs` and
`retrieval_source` back into state. `retrieval_source` is set to `"chroma"` or
`"bm25"` based on which path was taken (readable from circuit breaker state).

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/nodes/retrieve.py` (new)

**Depends on:** 07

**Parallel with:** 09

**Testing — done when:**
- [ ] Node receives an `AgentState` with a `question` and returns state with `docs` populated
- [ ] `retrieval_source` is set to `"chroma"` or `"bm25"` on every invocation
- [ ] Node does not raise on an empty question (returns empty docs list)
