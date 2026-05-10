# Decisions Index
*Always-loaded companion to DECISIONS.md. One-liner per decision — full prose in DECISIONS.md.*
*Last updated: 2026-05-10 — Commit 14*

---

## Stack (made during /init)
1. **Python 3.11 + uv** — 3.11 for LangGraph/LangChain stability; uv for install speed
2. **FastAPI + NiceGUI co-mounted** — Python-only stack; Node.js migration explicitly deferred
3. **LangChain + LangGraph** — LangGraph required for the assess→update_profile feedback loop
4. **SQLite + PostgreSQL migration path** — raw SQL, WAL mode, JSON-as-TEXT columns; schema is migration-ready
5. **HuggingFace local embeddings** — no API key required; consistent embedding space regardless of OpenAI availability
6. **OpenAI primary + Ollama fallback** — circuit-breaker-guarded; per-invocation `get_provider()` is non-negotiable
7. **Monitoring in prod** — Prometheus + Grafana + ELK in prod compose; portfolio requirement; forces t3.xlarge

## Architecture
8. **AgentState designed for full C07–C17 arc** — LangGraph compiles against TypedDict; design once to prevent retroactive cascade changes
9. ~~**Synchronous graph.invoke()**~~ — SUPERSEDED by #10
10. **graph.astream_events() + SSE StreamingResponse** — streaming is a hard production requirement; tokens stream as `on_chat_model_stream` events
11. **add_messages reducer replaces conversation_history: str** — appends turns automatically; `session_id` is `thread_id` in config, not an AgentState field; `SessionMemory` deleted C10
12. **MemorySaver replaces SessionMemory** — in-process, lost on restart; swap to `SqliteSaver` for persistence (one-line change in lifespan)
13. **User profiles in SQLite, not JSON files** — JSON files were not mounted as a Docker volume; data was silently lost on container restart
14. **Cache key += user_level from C17** — same question at different mastery levels must produce different answers; `sha256(question + user_level)`
15. **asyncio.to_thread as blocking I/O bridge** — project-wide standard for all blocking calls in async routes; no lambda wrappers
16. **Mandatory vs optional auth** — use `get_current_user` when no anonymous use case exists; `current_user_optional` when route supports both
17. **Tests interspersed, not end-batched** — tests as contracts for downstream consumers; C05, C11, C14, C23
18. **@ui.refreshable from first appearance (C18)** — retrofitting requires structural surgery; build correctly once
19. **nginx proxy_read_timeout 86400** — NiceGUI holds a long-lived WebSocket; default 60s causes visible UI flickering
20. **EC2 t3.xlarge** — Ollama (3.5GB) + ELK (2GB) + app stack; t3.large (8GB) is insufficient

## Data Layer
21. **History injected post-retrieval** — retrieval stays query-pure; history only influences generation, not document selection
22. **Both tables in same SQLite file** — FK enforcement requires same connection/file; single lifespan init
23. **_connect() duplicated in auth/ and profile/** — domain separation; refactor candidate if duplication spreads to a 3rd module
24. **topic_scores as flat dict[str, float]** — 8+ commit specs built around this shape; nested format would require reopening all of them
25. **JSON strings for topic_scores/strengths/gaps** — service layer owns serialize/deserialize; avoids SQLite JSON function dependency; portable to PostgreSQL JSONB
26. **Conversation history excluded from LLM cache key** — accepted permanent limitation; session-aware cache namespace deferred

## Security Patterns
27. **Frozenset allowlist for dynamic SQL** — column names cannot be parameterized; this is the project-wide standard; every future dynamic SQL function needs `_ALLOWED_X_COLUMNS`
28. **Column allowlist in update_profile** — guards kwargs before SET clause; immutable frozenset cannot be runtime-patched by a caller
29. **get_or_create_profile absorbs IntegrityError** — UNIQUE constraint is the race guard; unconditional re-fetch always returns the winner
30. **create_profile at registration (not get_or_create)** — registration is the creation event; silent absorption here would hide data integrity bugs

## Graph Patterns (C07–C17)
31. **retrieval_source from CB state inspection** — pre/post `chroma_cb.is_available()` detects backend without modifying `retrieve()` signature; covers all 3 CB state transitions
32. **get_provider() per-invocation** — module-level singleton freezes before CB state changes; per-invocation sees current CB state and activates Ollama fallback correctly
33. **build_graph(checkpointer) factory** — no module-level singleton; each test constructs isolated `MemorySaver`; swap checkpointer in lifespan to change persistence backend
34. **assessed_topics as SSE public key** — internal state field is `topic_scores_delta`; SSE consumers see `assessed_topics` (intention-revealing); this is the locked contract from C10
35. **add_conditional_edges with named routing hook** — both paths route to same node today (C12); diverges in C15; routing function `_route_after_assess` is independently testable
36. **update_profile_node stub in graph.py** — one-commit temporary placement; C15 creates `src/agents/nodes/update_profile.py` and moves it
37. **Assessment prompt in `src/agents/prompts/`** — prompts are code; separate module = independent versioning, testability, and review surface (C13)
38. **user_level not written from assess_node to AgentState** — avoids circular turn-update; user_level ownership deferred to update_profile_node in C15
39. **LangChain chain mock via `prompt.__or__` patch** — `MagicMock` is not a `Runnable`; patching `__or__` intercepts before `RunnableSequence` construction; established pattern for LCEL chain tests (C13)

## Scoring Service Patterns (C14)
40. **Invalid slug filter by value type, not allowlist** — allowlist couples scoring to curriculum; value-type check (`isinstance(score, (int, float))`) is the correct scoring invariant; unknown-but-numeric slugs stored; enforcement belongs at Nova's assess_node boundary
41. **Silent score clamping to [0.0, 1.0]** — defensive last-writeable boundary before profile persistence; LLM may produce out-of-range values; no log on clamp (add later if monitoring needed)
