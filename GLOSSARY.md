# GLOSSARY.md — RAG from Scratch

> Maintained by Claude. Domain-specific terms used in this project's code,
> commits, and agent communication are defined here.
> Last updated: 2026-05-08

---

## Project Terms

### RAG (Retrieval-Augmented Generation)
**Meaning on this project:** A technique where relevant documents are retrieved from a knowledge base and injected into an LLM prompt before generation. The LLM answers based on retrieved context rather than parametric knowledge alone. Prevents hallucination for domain-specific questions.
**Used in:** `src/rag/`, commit names, README
**Introduced in:** existing codebase

### Knowledge Base
**Meaning on this project:** The 6 Markdown modules covering RAG architecture, vector databases, LangChain, chunking, retrieval methods, and production patterns. Stored in `data/knowledge_base/`, indexed into ChromaDB at startup.
**Distinct from:** The ChromaDB vector store (which indexes the knowledge base, but is not itself the KB).
**Used in:** `src/rag/pipeline/indexer.py`, `data/knowledge_base/`
**Introduced in:** existing codebase

### AgentState
**Meaning on this project:** The TypedDict that carries all data through the LangGraph graph for a single user turn. Key field: `messages: Annotated[list[BaseMessage], add_messages]` — the full conversation history managed by LangGraph's `add_messages` reducer. `session_id` is NOT a field — it is passed as `thread_id` in the graph config. Designed for the full Commits 07–17 arc.
**Distinct from:** A Python dict (AgentState is typed, and `messages` uses a reducer — not plain assignment).
**Used in:** `src/agents/state.py`, all node files
**Introduced in:** Commit 07

### Node (LangGraph)
**Meaning on this project:** A single step in the agent graph. A Python function that receives `AgentState`, does one thing, and returns a partial state update. Nodes in this project: `retrieve_node`, `generate_node`, `assess_node`, `update_profile_node`.
**Distinct from:** A graph edge (which defines control flow between nodes).
**Used in:** `src/agents/nodes/`
**Introduced in:** Commit 08

### User Profile
**Meaning on this project:** A per-user record in the `user_profiles` SQLite table tracking learning state: topic scores, mastery level, identified strengths and gaps, interaction count. Read by the agent before generating a response; updated after each turn.
**Distinct from:** The auth user record in the `users` table (which stores credentials only).
**Used in:** `src/app/profile/`, `src/agents/nodes/update_profile.py`
**Introduced in:** Commit 04

### Topic Score
**Meaning on this project:** A float (0.0–1.0) representing a user's demonstrated understanding of a specific knowledge base module. Stored as a JSON dict in `user_profiles.topic_scores`. Keys are module slugs (see below).
**Distinct from:** A raw LLM confidence value (topic scores are computed and smoothed, not raw).
**Used in:** `src/app/profile/scoring.py`, `src/agents/state.py`
**Introduced in:** Commit 14

### Mastery Level
**Meaning on this project:** A human-readable label derived deterministically from the average of all topic scores: `novice` (< 0.2), `beginner` (0.2–0.4), `intermediate` (0.4–0.6), `advanced` (0.6–0.8), `expert` (≥ 0.8). Used to select the adaptive prompt template.
**Distinct from:** A topic score (which is per-module); mastery level is the aggregate.
**Used in:** `src/app/profile/scoring.py`, `src/agents/prompts.py`, `src/agents/state.py`
**Introduced in:** Commit 14

### TopicScoreUpdate
**Meaning on this project:** A TypedDict returned by `compute_topic_scores()` in `src/app/profile/scoring.py`. The typed interface contract between Rex's profile service and Nova's `update_profile_node`. Contains: full updated `topic_scores`, `strengths`, `gaps`, and `mastery_level`.
**Distinct from:** `AssessmentOutput` (which is raw LLM output); `TopicScoreUpdate` is the computed result after merging the delta into existing scores.
**Used in:** `src/app/profile/scoring.py`, `src/agents/nodes/update_profile.py`
**Introduced in:** Commit 14

### AssessmentOutput
**Meaning on this project:** A Pydantic model returned by the LLM via `.with_structured_output()` in `assess_node`. Contains `topic_scores_delta` (sparse dict of modules assessed this turn), `identified_gaps`, and `user_level`. Validated by Pydantic before the graph uses it.
**Distinct from:** `TopicScoreUpdate` (which is the result after merging the delta into the full profile).
**Used in:** `src/agents/state.py`, `src/agents/nodes/assess.py`
**Introduced in:** Commit 07 (schema), Commit 13 (implementation)

### Module Slug
**Meaning on this project:** A snake_case identifier for a knowledge base module, used as keys in `topic_scores`. The canonical set:
- `rag_fundamentals` — Module 1: Information Retrieval
- `vector_databases` — Module 2: Vector Databases
- `retrieval_methods` — Module 3: RAG Architecture
- `chunking_strategies` — Module 4: Chunking
- `langchain` — Module 5: LangChain and Agents
- `production_patterns` — Module 6: Production RAG
**Used in:** `src/app/profile/scoring.py`, `src/agents/state.py`
**Introduced in:** Commit 07

### asyncio.to_thread
**Meaning on this project:** A Python stdlib function (`asyncio.to_thread(fn, *args)`) that runs a synchronous callable in a thread pool executor and returns an awaitable. Used throughout this project to prevent blocking I/O (ChromaDB, SQLite, LLM calls) from stalling the async event loop. Called as `await asyncio.to_thread(fn, arg1, arg2)` — not wrapped in a lambda.
**Distinct from:** `asyncio.run_in_executor` (lower-level; `asyncio.to_thread` is the idiomatic modern replacement).
**Used in:** `src/app/api/routes/documents.py`, `src/app/api/routes/chat.py`, `src/app/auth/deps.py`
**Introduced in:** Commit 01 (extended from pattern already present in chat.py)

### Circuit Breaker
**Meaning on this project:** A resilience pattern that stops sending requests to a failing service. Three states: CLOSED (normal), OPEN (failing — reject immediately), HALF_OPEN (probing — allow one test request). This project has circuit breakers for ChromaDB (`chroma_cb`), OpenAI (`openai_cb`), and Redis (`redis_cb`).
**Used in:** `src/rag/resilience/circuit_breaker.py`
**Introduced in:** existing codebase

### BM25 Fallback
**Meaning on this project:** Keyword-based retrieval using the BM25 algorithm. Activated automatically when the ChromaDB circuit breaker is OPEN. Less semantically accurate than vector search but keeps the system operational.
**Distinct from:** ChromaDB semantic search (primary retrieval path).
**Used in:** `src/rag/resilience/degradation.py`, `src/rag/pipeline/retriever.py`
**Introduced in:** existing codebase

### Session Memory
**Meaning on this project:** An in-process conversation buffer per session, keyed by session_id. Stores the last N message turns. Not persisted to disk — lost on app restart. Previously injected into chain.py as a `conversation_history` string.
**Status:** Deleted in Commit 10. Replaced by LangGraph's `MemorySaver` checkpointer, which manages conversation history natively via `thread_id` in the graph config. No application code needed for history injection after Commit 10.
**Distinct from:** User Profile (which is persistent in SQLite and tracks understanding, not conversation).
**Was in:** `src/rag/memory/conversation.py` (deleted in Commit 10)
**Introduced in:** existing codebase

### add_messages (reducer)
**Meaning on this project:** A LangGraph reducer function used as `Annotated[list[BaseMessage], add_messages]` on `AgentState.messages`. When a node returns `{"messages": [new_message]}`, the reducer *appends* the new message to the existing list rather than replacing it. This is what makes multi-turn conversation work without manual list management.
**Distinct from:** A plain `list[BaseMessage]` TypedDict field (which would replace the entire list on every update).
**Used in:** `src/agents/state.py`, `langgraph.graph.message`
**Introduced in:** Commit 07

### MemorySaver (checkpointer)
**Meaning on this project:** LangGraph's built-in in-process checkpointer. When the graph is compiled with `graph.compile(checkpointer=MemorySaver())` and invoked with `config={"configurable": {"thread_id": session_id}}`, LangGraph automatically saves and restores `AgentState` (including `messages`) between turns. The conversation history is reconstructed transparently — no application code required.
**Distinct from:** `SessionMemory` (the custom in-process buffer deleted in Commit 10); `SqliteSaver`/`PostgresSaver` (disk-persistent checkpointers for multi-instance deployments).
**Used in:** `src/agents/graph.py` (Commit 10), LangGraph internals
**Introduced in:** Commit 10

### SSE (Server-Sent Events)
**Meaning on this project:** A one-way HTTP streaming protocol where the server pushes events to the client over a persistent connection. `Content-Type: text/event-stream`. Each event is a line of the form `data: <json>\n\n`. Used in this project to stream LLM tokens from `POST /api/chat` as they are generated, so the client receives tokens progressively rather than waiting for the full answer.
**Distinct from:** WebSocket (bidirectional); chunked transfer encoding (raw bytes, no event structure); HTTP/2 push (server-initiated, not response-streaming).
**Used in:** `src/app/api/routes/chat.py` (`StreamingResponse(media_type="text/event-stream")`), `src/app/ui.py` (httpx SSE consumer)
**Introduced in:** Commit 10

### CompiledStateGraph
**Meaning on this project:** The type returned by `graph.compile(checkpointer=...)` in LangGraph. A fully wired, executable graph object. In this project produced by `build_graph(checkpointer)` in `src/agents/graph.py` and stored on `app.state.rag_graph` during lifespan. Exposes `astream_events()` for async streaming invocation.
**Distinct from:** `StateGraph` (the builder object used to define nodes and edges before compilation).
**Used in:** `src/agents/graph.py`, `src/app/main.py`
**Introduced in:** Commit 10

### thread_id (graph config)
**Meaning on this project:** The key within `{"configurable": {"thread_id": value}}` passed to `graph.astream_events()`. LangGraph's checkpointer uses this value to identify which conversation thread to save and restore. In this project, `session_id` from the request is used as `thread_id`. Each unique `session_id` → independent conversation thread with its own `AgentState` history.
**Distinct from:** `session_id` in the HTTP request body (which is the source value); `user_id` from JWT (which identifies the user, not the conversation thread).
**Used in:** `src/app/api/routes/chat.py` (`config = {"configurable": {"thread_id": session_id}}`)
**Introduced in:** Commit 10

### assessment_error
**Meaning on this project:** A boolean field in `AgentState`. Set to `True` by `assess_node` when the LLM call or structured-output parsing fails during assessment. When `True`, the conditional edge `_route_after_assess` in `graph.py` routes to `update_profile_node` with empty deltas — the profile is not updated but the graph continues cleanly to END. When `False`, the normal path applies the assessment delta to the profile.
**Distinct from:** A Python exception (which is caught inside `assess_node`; `assessment_error` is the state-level signal emitted after the exception is handled).
**Used in:** `src/agents/state.py`, `src/agents/nodes/assess.py`, `src/agents/graph.py`
**Introduced in:** Commit 12

### assessed_topics (SSE schema key)
**Meaning on this project:** The key name for `topic_scores_delta` in the final SSE `done` event: `{"type": "done", "user_level": ..., "assessed_topics": {...}}`. Renamed at the serialization boundary to better reflect consumer intent (which topics were assessed this turn) rather than implementation detail (the delta values). Values are `dict[str, float]` — same structure as `topic_scores_delta` in `AgentState`.
**Distinct from:** `topic_scores_delta` (the internal `AgentState` field name — a sparse per-turn delta, not exposed directly in SSE).
**Used in:** `src/app/api/routes/chat.py` (emitted in `generate_stream()`), `tests/test_chat_route.py`
**Introduced in:** Commit 10

### WAL Mode
**Meaning on this project:** SQLite Write-Ahead Logging journal mode. Enables concurrent reads during a write operation. Enabled via `PRAGMA journal_mode=WAL` in `_connect()`. Required because the LangGraph agent thread writes profile updates while FastAPI request threads read user data concurrently.
**Used in:** `src/app/auth/db.py`, `src/app/profile/db.py`
**Introduced in:** Commit 04

---

## Agent / Protocol Terms

### Commit
**Meaning on this project:** A single, scoped unit of work assigned to one agent. One concern, one owner. Cannot span agent domains without an explicit cross-domain note in the spec.
**Used in:** `commit-protocol.md`, all worklogs

### Handoff
**Meaning on this project:** A structured note from one agent to another, routed through Claude, carrying context the receiving agent needs before starting work. Currently open: Commit 05 → Nova (Commit 15) re: `last_activity_at` must be set on every profile update.
**Used in:** `project-state.json open_handoffs`

### Hard Block
**Meaning on this project:** A Viktor finding so severe it bypasses the normal quality gate and surfaces directly to the Team Lead before any commit is made. Two Hard Blocks were raised during /init: graph replacement with zero tests (resolved by Commit 11), and untyped cross-agent interface (resolved by Commit 14's typed interface requirement).
**Used in:** `ORCHESTRATION.md`, Viktor reviews

*Last updated: 2026-05-09 — Commit 07 complete*
