# Commit 10 Spec — `langgraph-graph-assembly`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 10 — `langgraph-graph-assembly`

**Commit message:** `feat: assemble LangGraph graph with MemorySaver, SSE streaming, and remove SessionMemory`

**Body:**
Wires `retrieve_node` and `generate_node` into a compiled LangGraph graph.
Replaces `run_rag_pipeline()` in `chain.py` with `graph.astream_events()`.
Deletes the `SessionMemory` class entirely — LangGraph's `MemorySaver` checkpointer
handles cross-turn persistence via `thread_id`.

Architecture redesigned by Eran Mani: this is a production system and streaming
responses are a hard requirement. `graph.astream_events()` emits `on_chat_model_stream`
events as the LLM generates each token. `chat.py` returns a `StreamingResponse`
(SSE, `text/event-stream`) so the frontend receives tokens in real time.

**Graph compilation:**
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)
```

`MemorySaver` is in-process and sufficient for portfolio/single-instance deployments.
For multi-instance production, swap to `SqliteSaver` (persists across restarts) or
`PostgresSaver` — the call site in `chain.py` is the only change needed.

**Streaming SSE in `chat.py`:**
```python
from fastapi.responses import StreamingResponse
import json

@router.post("/chat")
async def chat(request: ChatRequest, current_user = Depends(current_user_optional)):
    session_id = request.session_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None
    user_level = await asyncio.to_thread(get_user_level, user_id)

    initial_state = {
        "messages": [HumanMessage(content=request.question)],
        "question": request.question,
        "user_id": user_id,
        "user_level": user_level,
        "docs": [],
        "retrieval_source": "",
        "answer": "",
        "topic_scores_delta": {},
        "identified_gaps": [],
        "assessment_error": False,
        "trace_id": str(uuid.uuid4()),
        "latency_ms": 0,
        "cache_hit": "miss",
    }
    config = {"configurable": {"thread_id": session_id}}

    async def generate_stream():
        final_state = {}
        async for event in app.astream_events(initial_state, config=config, version="v2"):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
            elif event["event"] == "on_chain_end" and event.get("name") == "LangGraph":
                final_state = event["data"].get("output", {})
        yield f"data: {json.dumps({'type': 'done', 'user_level': final_state.get('user_level', 'novice'), 'assessed_topics': final_state.get('topic_scores_delta', {})})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")
```

**SessionMemory deletion:**
- `src/rag/memory/conversation.py` is deleted. The file must not exist after this commit.
- Any import of `SessionMemory` in `chain.py` or elsewhere must be removed.
- `format_history(session_id)` calls are removed — LangGraph reconstructs message history
  from the checkpointer automatically when `thread_id` is passed in config.

**`chain.py` changes:**
- `run_rag_pipeline()` is removed.
- `chain.py` may be reduced to a thin module or removed entirely if no other logic lives there.
  Document the decision in the worklog.

**Cache strategy:**
The existing query-level Redis cache is retained for this commit. Cache key invalidation
per user profile is addressed in Commit 17 when adaptive responses are active.
For commits 10–16, cached responses may be shared across users with different profiles —
this is a known temporary limitation, logged explicitly.

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/graph.py` (new — graph wiring + MemorySaver compilation)
- `src/rag/chain.py` (update — remove `run_rag_pipeline`, remove `SessionMemory` import)
- `src/app/api/routes/chat.py` (update — replace dict response with SSE `StreamingResponse`)
- `src/rag/memory/conversation.py` (delete — `SessionMemory` removed entirely)

**Depends on:** 08, 09

**Testing — done when:**
- [ ] End-to-end: POST `/api/chat` returns `Content-Type: text/event-stream`
- [ ] Token events arrive before the `done` event (streaming confirmed, not buffered)
- [ ] `done` event contains `user_level` and `assessed_topics` keys
- [ ] Second turn: same `session_id` → `thread_id` → prior `HumanMessage` + `AIMessage` present in state `messages`; LLM response is context-aware
- [ ] `src/rag/memory/conversation.py` does not exist — no import of `SessionMemory` remains anywhere
- [ ] Graph handles ChromaDB circuit breaker OPEN (falls back to BM25 via `retrieve_node`)
