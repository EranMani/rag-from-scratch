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

`graph.py` exposes a factory function — it does not create a module-level singleton:
```python
# src/agents/graph.py
from langgraph.checkpoint.base import BaseCheckpointSaver

def build_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    ...
    return graph.compile(checkpointer=checkpointer)
```

The checkpointer is instantiated in the server lifespan alongside every other service
(`init_user_db`, `init_profile_db`, `set_bm25_fallback`). Lifespan is the single place
where all service dependencies are visible:
```python
# src/app/main.py lifespan
from langgraph.checkpoint.memory import MemorySaver
from agents.graph import build_graph

checkpointer = MemorySaver()
app.state.rag_graph = build_graph(checkpointer)
```

`chat.py` accesses the graph via `request.app.state.rag_graph` — no module-level import.

`MemorySaver` is in-process and sufficient for portfolio/single-instance deployments.
To swap to `SqliteSaver` (persists across restarts) or `PostgresSaver` (multi-instance),
change one line in `lifespan` — nothing else.

**Streaming SSE in `chat.py`:**
```python
from fastapi.responses import StreamingResponse
import json

@router.post("/chat")
async def chat(req: ChatRequest, request: Request, current_user = Depends(current_user_optional)):
    rag_graph = request.app.state.rag_graph
    session_id = req.session_id or str(uuid.uuid4())
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
        async for event in rag_graph.astream_events(initial_state, config=config, version="v2"):
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
