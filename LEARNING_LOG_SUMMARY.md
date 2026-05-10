# Learning Log Summary
*Always-loaded companion to LEARNING_LOG.md. Updated by Ryan each commit — one line per entry.*
*Full entries: LEARNING_LOG.md | Eviction archive: learning-log-archive-era*.md*

---

- **C01** auth-gate-on-ingest — guard-clause auth + two-layer path confinement + asyncio.to_thread; establishes blocking I/O pattern for all future async routes
- **C02** config-and-naming-cleanup — atomic rename of two misspelled identifiers across all call sites
- **C03** wire-conversation-history — history injected post-retrieval, not pre; retrieval stays query-pure; LLM cache key excludes history (accepted permanent gap)
- **C04** user-profile-db-schema — user_profiles in same SQLite file as users; WAL mode; FK ON DELETE CASCADE; JSON fields stored as TEXT strings
- **C05** user-profile-service — frozenset allowlist closes dynamic SQL injection path in update_profile; TOCTOU-safe get_or_create_profile via IntegrityError absorption; old JSON profile store deleted
- **C06** user-profile-api — GET /api/profile/me behind JWT; create_profile (not get_or_create) at registration — registration is the creation event; static 404 detail prevents CWE-209
- **C07** langgraph-state-schema — AgentState designed for full C07–C17 arc; add_messages reducer; Literal enforcement on user_level/cache_hit; from __future__ + include_extras=True gotcha documented
- **C08** langgraph-retrieve-node — pre/post chroma_cb.is_available() inspection detects retrieval backend without modifying retrieve() signature; covers all 3 CB state transitions
- **C09** langgraph-generate-node — per-invocation get_provider() (never module singleton); await llm.ainvoke() async-by-design for streaming; add_messages accumulates history automatically
- **C10** langgraph-graph-assembly — build_graph(checkpointer) factory pattern; blocking I/O (get_user_level) hoisted outside async generator; graph.astream_events(v2) + SSE StreamingResponse; SessionMemory deleted
- **C11** langgraph-graph-smoke-test — 14 smoke tests gate Phase 4; fresh MemorySaver per test class prevents state bleed between test runs
- **C12** langgraph-assessment-scaffold — stub pattern proves wiring before real LLM call; try/except wraps construction not just LLM call; add_conditional_edges with named routing hook _route_after_assess
