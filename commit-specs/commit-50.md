# Commit 50 Spec — `langgraph-questions`
> **Project:** rag-from-scratch · **Assignee:** RAG Specialist · **Load only for the active commit.**
> **Note:** New commit added in replan 2026-05-23 — question bank for the new langgraph_fundamentals Phase 3 topic.

---

### Commit 50 — `langgraph-questions`

**Commit message:** `feat(EranMani): add question bank for langgraph_fundamentals topic (MCQ + open)`

**Body:**
Requested by Eran Mani, our team lead: write the full question bank for the `langgraph_fundamentals` Phase 3 topic. Concepts only — no Python API questions. Minimum 5 questions per difficulty tier per format.

**Assignee:** RAG Specialist (knowledge-base only — no src/ files)

**Files touched:**
- `knowledge-base/curriculum/questions/mcq/langgraph_fundamentals.md` (new)
- `knowledge-base/curriculum/questions/langgraph_fundamentals.md` (new)

**Depends on:** 49 (langgraph_fundamentals slug is live in curriculum-map before questions are written)

**Content requirements:**

Topics to cover across all tiers:
- Directed graphs in computation: nodes as operations, edges as data flow, acyclic vs. cyclic graphs
- State: what it is in a graph agent, how it flows, why nodes read-and-write state rather than passing arguments
- Conditional routing: how edges branch on state values, what makes graph routing different from if-statements in node code
- Graph compilation: what it validates, what it produces, why runtime invocation requires a compiled graph
- Checkpointing and memory: how state is persisted across turns, how a compiled graph can resume from any checkpoint, why this enables multi-turn agents
- Agentic behavior: what a graph can do that a sequential chain cannot (cycles, self-correction, conditional retrieval, parallel branches)
- The relationship between graph topology and LLM behavior: the graph is the architecture; the LLM is a node within it

Difficulty calibration:
- **Novice**: recognition — define node, edge, state; identify the phases of graph execution
- **Intermediate**: mechanism — explain how state flows, what conditional routing means, what compilation validates
- **Advanced**: application — given a graph description, trace the execution path; identify what state change triggers a routing decision
- **Expert**: diagnosis — given a broken graph behavior (e.g., infinite cycle, state not persisting, routing always taking one branch), identify the structural cause

Hard constraint — NO Python in any question or answer criterion:
- Do not reference `.add_node()`, `.add_edge()`, `StateGraph`, `CompiledGraph`, or any Python API
- Questions must be answerable by someone who understands the concepts but has never used LangGraph
- Correct answer criteria must describe behavior, not code

MCQ requirements:
- Exactly 4 options (A–D), 1 correct answer
- "Why X is wrong" per distractor — must identify the specific misconception
- ≥ 5 questions per tier: novice, intermediate, advanced, expert

Open question requirements:
- Rubric-based with correct/partial/incorrect criteria
- ≥ 5 questions per tier: novice, intermediate, advanced
- Expert tier strongly encouraged

**Testing — done when:**
- [ ] `knowledge-base/curriculum/questions/mcq/langgraph_fundamentals.md` exists with ≥ 5 questions per tier
- [ ] `knowledge-base/curriculum/questions/langgraph_fundamentals.md` exists with ≥ 5 questions per tier
- [ ] Zero Python syntax anywhere in either file (questions, answer criteria, or explanations)
- [ ] Every MCQ distractor has a "Why X is wrong" explanation targeting a named misconception
- [ ] File headers include tier count summary
