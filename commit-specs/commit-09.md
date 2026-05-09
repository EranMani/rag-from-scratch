# Commit 09 Spec — `langgraph-generate-node`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 09 — `langgraph-generate-node`

**Commit message:** `feat: LangGraph generate_node with native message history and streaming-ready design`

**Body:**
Wraps LLM generation as a LangGraph node. Reads `messages` from `AgentState` for
full conversation history — no separate `conversation_history` string, no `{history}`
template slot. The `add_messages` reducer in `AgentState` means the full prior
conversation is already in `state["messages"]` when this node runs; the node prepends a
`SystemMessage` with context and user_level, then passes the full messages list to the LLM.

This node is streaming-ready by design: because it calls `llm.ainvoke()` on a standard
messages list, `graph.astream_events()` (Commit 10) will automatically emit
`on_chat_model_stream` events as the LLM generates each token — no changes to this node
are needed when streaming is wired.

**Node signature and behaviour:**
```python
from langchain_core.messages import SystemMessage, AIMessage

async def generate_node(state: AgentState) -> dict:
    context = "\n\n".join(doc.page_content for doc in state["docs"])
    user_level = state.get("user_level", "novice")
    # [user_level starts as "novice" — adaptive depth wired in Commit 17]

    system_msg = SystemMessage(content=(
        "You are an expert on RAG systems. Answer using ONLY the provided context.\n"
        f"Adapt your explanation depth to the user's level: {user_level}.\n\n"
        f"Context:\n{context}"
    ))

    # state["messages"] contains the full conversation: prior AIMessages + current HumanMessage
    response = await llm.ainvoke([system_msg] + list(state["messages"]))

    return {
        "messages": [response],   # add_messages appends AIMessage — does not replace
        "answer": response.content,  # kept for assess_node and SSE done event
    }
```

The `question` convenience field is NOT used here — the current user question is already
the last `HumanMessage` in `state["messages"]`. `question` exists only for `retrieve_node`.

Node uses `get_provider()` — respects the OpenAI circuit breaker → Ollama fallback.

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/nodes/generate.py` (new)

**Depends on:** 07

**Parallel with:** 08

**Testing — done when:**
- [ ] Node receives state with `docs`, `question`, `messages: [HumanMessage("...")]` and returns dict with `answer` set and `messages` containing the new `AIMessage`
- [ ] `add_messages` contract verified: returned `messages` list contains both the original `HumanMessage` and the new `AIMessage` (not just the AIMessage)
- [ ] Node works correctly on first turn (single `HumanMessage` in `messages`, no prior history)
- [ ] Node works correctly on second turn (prior `HumanMessage` + `AIMessage` in `messages`)
- [ ] Node uses `get_provider()` (respects OpenAI circuit breaker → Ollama fallback)
