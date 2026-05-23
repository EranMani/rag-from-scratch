# Commit 49 Spec — `langgraph-curriculum`
> **Project:** rag-from-scratch · **Assignee:** Lara · **Load only for the active commit.**
> **Note:** New commit added in replan 2026-05-23 — adds langgraph_fundamentals as a Phase 3 topic. Former documentation (old 49) renumbered to 56.

---

### Commit 49 — `langgraph-curriculum`

**Commit message:** `feat(EranMani): add langgraph_fundamentals as Phase 3 topic in curriculum-map and gates`

**Body:**
Requested by Eran Mani, our team lead: add `langgraph_fundamentals` as a required Phase 3 topic. The app itself is built on LangGraph — learners should understand the architecture of the system that is teaching them. Topic is concepts-only: state machines, nodes, edges, conditional routing, graph compilation, and checkpointing. No Python API content.

**Assignee:** Lara (knowledge-base only — no src/ files)

**Files touched:**
- `knowledge-base/curriculum/curriculum-map.md` — add langgraph_fundamentals to Phase 3
- `knowledge-base/curriculum/gates.md` — add langgraph_fundamentals to Phase 3 gate at 0.75 threshold

**Depends on:** 48 (document_ingestion questions complete)

**langgraph_fundamentals topic spec (for curriculum-map.md):**
- **Phase:** 3
- **Description:** Understand graph-based agent architectures — what a directed graph is in computation, how state flows between nodes, how conditional routing enables branching behavior, and why graph compilation is necessary before execution. This is the conceptual layer behind adaptive RAG systems, including this one.
- **Prerequisites:** Phase 2 gate passed (requires solid understanding of RAG components before learning how to orchestrate them as an agent)
- **Learning objectives:**
  1. Explain what a directed graph is in computation and how nodes and edges map to agent behavior
  2. Describe what "state" means in a graph agent — what it carries, how it is updated at each node, and why it flows rather than being mutated globally
  3. Explain conditional routing: how a graph edge can branch on state values and what this enables that a sequential chain cannot do
  4. Describe graph compilation: what it produces, why the graph must be compiled before running, and what happens at compile time
  5. Explain checkpointing: how state is persisted across turns in a multi-turn agent and why this enables conversation memory without manual state management
- **Typical misconceptions:**
  - "A LangGraph graph is just a more complicated chain." (A graph adds state, branching, cycles, and persistence — it is a different execution model, not a stylistic choice.)
  - "Conditional routing requires writing if-statements in each node." (Routing logic lives on the edges — nodes are pure state transformers; edges decide where to go next based on state.)
  - "Graph compilation is just syntax checking." (Compilation validates the graph topology, resolves edge conditions, and produces an execution plan — it is semantically meaningful, not just validation.)
  - "Checkpointing is the same as caching." (Checkpointing persists intermediate state at each node for resumability and multi-turn memory — cache stores results to avoid recomputation.)

**Phase 3 gate update (for gates.md):**
```
phase_3_passed = (
    score["evaluation_and_metrics"] >= 0.75
    AND score["production_patterns"] >= 0.75
    AND score["langgraph_fundamentals"] >= 0.75
)
```

**Testing — done when:**
- [ ] `curriculum-map.md` contains a complete `langgraph_fundamentals` entry under Phase 3
- [ ] `gates.md` Phase 3 gate includes `langgraph_fundamentals >= 0.75`
- [ ] Topic description is concepts-only — no Python syntax, no framework API references
- [ ] No `src/` files touched
