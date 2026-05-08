# DECISIONS.md — RAG from Scratch

> Maintained by Claude. Every non-obvious design choice made during this project
> is logged here with the reason it was made.
> Last updated: 2026-05-08

---

## Stack Decisions (made during /init, 2026-05-08)

### Python 3.11 + uv
- **Date:** 2026-05-08
- **Commit:** during /init
- **Decided by:** Team Lead
- **Decision:** Python 3.11 as runtime; uv as package manager.
- **Consequences:** LangGraph, LangChain, FastAPI all have stable 3.11 support. uv is significantly faster than pip for installs.

### FastAPI + NiceGUI (co-mounted)
- **Date:** 2026-05-08
- **Commit:** during /init
- **Decided by:** Team Lead
- **Decision:** FastAPI as API layer; NiceGUI mounted on the same app via `ui.run_with()`.
- **Alternatives considered:** Separate frontend service; React.
- **Consequences:** Python-only stack — no Node.js toolchain required. NiceGUI → Node.js migration is explicitly deferred to a future phase.

### LangChain + LangGraph
- **Date:** 2026-05-08
- **Commit:** during /init
- **Decided by:** Team Lead
- **Decision:** LangChain for RAG (retrieval, document loading, LCEL chains); LangGraph for the adaptive agent graph.
- **Consequences:** LangGraph's stateful graph execution is required for the assess → update_profile feedback loop. LangChain provides mature integrations for all data layer components.

### SQLite with PostgreSQL migration path
- **Date:** 2026-05-08
- **Commit:** during /init
- **Decided by:** Team Lead
- **Decision:** SQLite3 with raw queries, no ORM, for this phase. PostgreSQL is the stated future target.
- **Alternatives considered:** PostgreSQL from the start; SQLAlchemy ORM.
- **Consequences:** Schema is designed to be migration-ready (JSON string columns → JSONB, TEXT UUIDs → UUID, ISO-8601 strings → TIMESTAMPTZ). Raw SQL makes the migration explicit and learnable. WAL mode added to handle LangGraph thread concurrency.

### HuggingFace local embeddings
- **Date:** 2026-05-08
- **Commit:** during /init
- **Decided by:** Team Lead
- **Decision:** sentence-transformers running locally, not OpenAI embeddings.
- **Alternatives considered:** OpenAI text-embedding-3-small.
- **Consequences:** No API key required for embeddings. Cheaper at scale. Consistent embedding space regardless of OpenAI availability.

### OpenAI primary + Ollama fallback
- **Date:** 2026-05-08
- **Commit:** during /init
- **Decided by:** Team Lead
- **Decision:** OpenAI (gpt-4o, configurable) as primary LLM; Ollama (gemma3:4b) as circuit-breaker fallback.
- **Consequences:** System remains operational if OpenAI API is unavailable. OPENAI_MODEL should be updated by Team Lead when target model ID is confirmed.

### Monitoring stack in production
- **Date:** 2026-05-08
- **Commit:** during /init
- **Decided by:** Team Lead (explicit override of Adam's recommendation)
- **Decision:** Prometheus, Grafana, ELK stack present in `docker-compose.prod.yml` — not dev-only.
- **Reason:** Portfolio decision — the project must demonstrate production-grade self-evaluation and metrics visibility. This is part of the portfolio story.
- **Consequences:** EC2 instance must be t3.xlarge (16 GB RAM). Monitoring services proxied through nginx with auth — not publicly exposed. Dashboard configuration deferred to a later commit.

---

## Architecture Decisions (made during /init + archaeology, 2026-05-08)

### AgentState designed for full arc in Commit 07
- **Date:** 2026-05-08
- **Commit:** 07
- **Decided by:** Nova (flagged) + Claude (accepted)
- **Decision:** Design the complete `AgentState` TypedDict in Commit 07 including all Phase 4 fields (`topic_scores_delta`, `user_level`, `identified_gaps`, `assessment_error`, `conversation_history`, `retrieval_source`).
- **Reason:** LangGraph compiles the graph against the TypedDict. Retroactive state schema changes require recompiling and cascade through all downstream nodes. One careful design is cheaper than multiple breaking changes across commits 07–17.

### Synchronous graph.invoke() inside asyncio.to_thread()
- **Date:** 2026-05-08
- **Commit:** 10
- **Decided by:** Nova (flagged) + Claude (accepted)
- **Decision:** LangGraph graph runs synchronously (`graph.invoke()`), dispatched via `asyncio.to_thread()` — same pattern as the existing `run_rag_pipeline`.
- **Alternatives considered:** Async graph with `graph.astream()`.
- **Consequences:** All synchronous node I/O (ChromaDB, LLM calls) works without modification. Moving to `graph.astream()` in the future would require rewriting every node that calls synchronous I/O.

### User profiles in SQLite, not JSON files
- **Date:** 2026-05-08
- **Commit:** 04
- **Decided by:** Claude (archaeology finding)
- **Decision:** Move user profiles from `data/user_profiles/*.json` to the `user_profiles` table in `data/app_users.db`.
- **Reason:** The JSON directory is not mounted as a Docker volume — profile data is silently deleted on container restart. SQLite is persistent, transactional, and migration-ready.

### Cache key incorporates user_level (Commit 17+)
- **Date:** 2026-05-08
- **Commit:** 17
- **Decided by:** Nova (flagged) + Claude (accepted)
- **Decision:** Redis query cache key = `sha256(question + user_level)` for authenticated users. For anonymous users, behavior unchanged.
- **Reason:** Two users at different mastery levels asking the same question must receive different responses. The existing `sha256(question)` key would serve the same cached response to both.

### asyncio.to_thread as the project-wide blocking I/O bridge
- **Date:** 2026-05-08
- **Commit:** 01
- **Decided by:** Rex (applied) + Viktor (confirmed)
- **Decision:** `asyncio.to_thread(fn, *args)` is the standard pattern for running synchronous blocking calls inside async FastAPI routes. No lambda wrappers — pass callable and arguments separately.
- **Alternatives considered:** Making blocking libraries async-native; running a separate thread pool manually.
- **Consequences:** All blocking I/O (ChromaDB, SQLite, LLM calls) runs off the event loop without rewriting the underlying libraries. The pattern is now applied in `chat.py` (run_rag_pipeline), `documents.py` (ingest_documents), and `deps.py` (get_user_by_id). Every new blocking call in an async route must follow this pattern.

### Mandatory vs. optional auth dependency
- **Date:** 2026-05-08
- **Commit:** 01
- **Decided by:** Rex
- **Decision:** Two auth dependencies exist — `get_current_user` (raises 401 if no token) and `current_user_optional` (returns None if no token). Use `get_current_user` when unauthenticated access has no legitimate use case. Use `current_user_optional` when the route supports both authenticated and anonymous usage (governed by a feature flag like `allow_anonymous_chat`).
- **Consequences:** The selection criterion is explicit: does an anonymous request have a valid code path through this route? If no → mandatory. If yes → optional. Applied first in Commit 01 (ingest: mandatory — no anonymous use case exists).

### Tests interspersed, not end-batched
- **Date:** 2026-05-08
- **Commit:** 05, 11, 14, 23
- **Decided by:** Viktor (flagged) + Claude (accepted)
- **Decision:** Unit tests ship with the code they test (Commits 05 and 14). Graph smoke test gates Phase 4 (Commit 11). Integration tests at Commit 23.
- **Reason:** Tests written after integration are archaeology — by that point, the tested code has been consumed by multiple downstream components. Tests written before integration are the contract those downstream components build against.

### @ui.refreshable profile panel from Commit 18
- **Date:** 2026-05-08
- **Commit:** 18
- **Decided by:** Aria (flagged)
- **Decision:** Profile panel built as a `@ui.refreshable` function from the first commit it appears in.
- **Reason:** Retrofitting `@ui.refreshable` after the fact requires structural surgery on the NiceGUI layout. Building it correctly in Commit 18 means Commit 19 calls `.refresh()` with one line.

### nginx proxy_read_timeout 86400
- **Date:** 2026-05-08
- **Commit:** 21
- **Decided by:** Adam (flagged)
- **Decision:** nginx `proxy_read_timeout` must be set to 86400 seconds.
- **Reason:** NiceGUI holds a long-lived WebSocket connection. Default nginx timeout is 60 seconds — without this override, the UI silently disconnects every minute causing visible flickering and broken reactive state.

### EC2 t3.xlarge (16 GB RAM)
- **Date:** 2026-05-08
- **Commit:** 22
- **Decided by:** Adam (recommendation) + monitoring-in-prod decision
- **Decision:** t3.xlarge over t3.large for the production instance.
- **Reason:** Ollama (~3.5 GB) + ELK (~2 GB) + app+Redis+Chroma (~1 GB) + OS (~0.5 GB) = ~7-8 GB active with headroom needed. t3.large (8 GB) is insufficient with the full monitoring stack.

---

## Deferred Decisions

| Decision | Why deferred | Revisit at |
|---|---|---|
| PostgreSQL migration | SQLite sufficient for portfolio scale; schema is ready | Future phase |
| Node.js frontend | NiceGUI sufficient for demo; full Node.js is a separate project | Future phase |
| Redis/Celery async queue | Not needed until multi-user concurrent load is demonstrated | Future phase |
| LangGraph streaming (Option B: asyncio.Queue callbacks) | Requires graph callback design decision before UI can use it | Future phase |
| Prometheus/Grafana dashboard configuration | Infrastructure present; dashboards need production data to tune | Post-deployment |
| LLM fine-tuning | Requires evaluation data from production interactions | Future phase |
| A/B testing framework | Requires production traffic | Future phase |
| Subscription/billing | Out of scope for portfolio | Future phase |
| Exact OpenAI model ID | Team Lead to confirm when target model is available | Commit 02 or later |

*Last updated: 2026-05-08 — Commit 01 complete*
