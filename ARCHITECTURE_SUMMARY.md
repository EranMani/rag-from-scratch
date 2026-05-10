# Architecture Summary
*Always-loaded companion to ARCHITECTURE.md. Updated by Claude when ARCHITECTURE.md changes.*
*Full detail, component map, data flows, known debts: ARCHITECTURE.md*

---

- **API layer**: FastAPI + lifespan-managed services (init_user_db, init_profile_db, build_graph). All shared state on `app.state`. Blocking calls wrapped in `asyncio.to_thread()`.
- **Scoring service**: `src/app/profile/scoring.py` — pure function, no DB. `compute_topic_scores(current_profile, assessed_topics, interaction_count) → TopicScoreUpdate`. Merges deltas, clamps to [0,1], computes mastery level and strengths/gaps. Contract between Rex's profile domain and Nova's `update_profile_node`.
- **Graph**: LangGraph `StateGraph` — retrieve → generate → assess → update_profile → END. `MemorySaver` checkpointer; `session_id` passed as `thread_id` in config. `assess_node` runs a second LLM call via `assessment_prompt | llm.with_structured_output(AssessmentOutput)`; prompts live in `src/agents/prompts/`. `update_profile_node` (C15, synchronous) calls `compute_topic_scores()` then `update_profile()` — fast-exits on `user_id=None` or `assessment_error=True`.
- **Storage**: SQLite (`data/app_users.db`) — `users` + `user_profiles` tables; WAL mode; FK ON DELETE CASCADE; JSON columns as TEXT strings. PostgreSQL migration path: schema is ready.
- **RAG pipeline**: ChromaDB primary, BM25 fallback. Backend detected via pre/post `chroma_cb.is_available()` inspection in retrieve_node.
- **Streaming**: `graph.astream_events(version="v2")` + `SSE StreamingResponse`. Blocking I/O hoisted outside async generator. SSE schema: token events + final done event with `assessed_topics`.
- **LLM providers**: OpenAI primary (gpt-4o, configurable), Ollama fallback (gemma3:4b). Per-invocation `get_provider().get_llm()` — never module-level singleton.
- **Security**: JWT auth via `Depends(get_current_user)` or `current_user_optional`; path confinement on ingest; frozenset allowlist on all dynamic SQL; secrets in env vars only.
- **Deployment**: EC2 t3.xlarge (16GB); nginx reverse proxy (WebSocket, SSL, proxy_read_timeout 86400); Prometheus + Grafana + ELK in both dev and prod.
