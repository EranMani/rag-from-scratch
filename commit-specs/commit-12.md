# Commit 12 Spec — `langgraph-assessment-scaffold`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 12 — `langgraph-assessment-scaffold`

**Commit message:** `feat: assessment_node scaffold — contracts, fallback edge, stub LLM call`

**Body:**
Adds `assess_node` to the LangGraph graph. This commit ships the node structure,
input/output contract wiring, and a conditional fallback edge. The LLM call is
stubbed (returns a deterministic empty `AssessmentOutput`) — the real assessment
prompt is in Commit 13.

The fallback edge is non-negotiable for LangGraph: if `assess_node` sets
`assessment_error: True` in state, the graph routes directly to `update_profile_node`
with an empty delta (skips the error, profile is not updated). If `assessment_error`
is False, the graph continues normally. Both paths must compile cleanly.

Graph flow after this commit:
`retrieve_node → generate_node → assess_node → [conditional] → update_profile_node`
(update_profile_node is a stub at this stage — wired in Commit 15)

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/nodes/assess.py` (new)
- `src/agents/graph.py` (add node + conditional edge)

**Depends on:** 11

**Testing — done when:**
- [ ] Graph compiles without error after node is added
- [ ] Stub `assess_node` sets `assessment_error: False` and populates empty `AssessmentOutput`
- [ ] Conditional edge routes correctly on `assessment_error: True` (fallback path)
- [ ] Existing smoke test still passes
