# Commit 09 Spec — `langgraph-generate-node`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 09 — `langgraph-generate-node`

**Commit message:** `feat: LangGraph generate_node with history-aware prompt template`

**Body:**
Wraps `generate()` as a LangGraph node. Uses `conversation_history` from `AgentState`
to inject prior conversation context into the prompt. Uses `docs` from state for
retrieved context. The prompt template includes a `{history}` slot from day one —
this avoids a breaking change when adaptive prompts are wired in Commit 17.

The prompt template here is the evolution of the one modified in Commit 03:
```
System: You are an expert on RAG systems. Answer using ONLY the provided context.
        Adapt your explanation depth to the user's level: {user_level}.
        [user_level starts as "novice" — adaptive depth is wired in Commit 17]

Context: {context}
History: {history}
Question: {question}
```

Writes `answer` back into `AgentState`.

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/nodes/generate.py` (new)

**Depends on:** 07

**Parallel with:** 08

**Testing — done when:**
- [ ] Node receives state with `docs`, `question`, `conversation_history` and returns state with `answer` set
- [ ] Node works correctly with empty `conversation_history` (first turn)
- [ ] Node uses `get_provider()` (respects OpenAI circuit breaker → Ollama fallback)
