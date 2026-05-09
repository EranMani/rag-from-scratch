# Commit 11 Spec — `langgraph-graph-smoke-test`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 11 — `langgraph-graph-smoke-test`

**Commit message:** `test: smoke test for assembled LangGraph graph end-to-end`

**Body:**
Minimal integration test that exercises the full assembled graph and verifies
output shape and state population. This commit exists specifically to gate Phase 4
— no adaptive intelligence is built on an untested graph.

Test asserts:
- Graph accepts a valid `AgentState` input and returns a state dict
- `answer` is a non-empty string
- `docs` is a list (may be empty in test environment)
- `retrieval_source` is set to `"chroma"` or `"bm25"`
- `conversation_history` threading: a second invocation with the same session_id
  receives non-empty history

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `tests/test_graph_smoke.py` (new)

**Depends on:** 10

**Viktor Hard Block resolved:** This test gate was flagged as a required blocker before
Phase 4 builds on the assembled graph. Phase 4 (commits 12–17) does not begin until
this commit passes.

**Testing — done when:**
- [ ] `pytest tests/test_graph_smoke.py` passes with no errors
- [ ] Test does not require a live OpenAI key (use Ollama or mock the provider)
