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
- **Date:** 2026-05-08 · **Updated:** 2026-05-09 (Eran Mani — streaming architecture)
- **Commit:** 07
- **Decided by:** Nova (flagged) + Claude (accepted) · **Updated by:** Eran Mani
- **Decision:** Design the complete `AgentState` TypedDict in Commit 07 including all Phase 4 fields. Updated 2026-05-09: `conversation_history: str` replaced with `messages: Annotated[list[BaseMessage], add_messages]`; `session_id` removed from state (passed as `thread_id` in graph config).
- **Reason:** LangGraph compiles the graph against the TypedDict — one careful design prevents breaking changes across commits 07–17. Native message management is required for production streaming (`graph.astream_events()`). `session_id` in state was redundant — LangGraph's `MemorySaver` checkpointer uses `thread_id` from config, not a state field.

### ~~Synchronous graph.invoke() inside asyncio.to_thread()~~ — SUPERSEDED
- **Date:** 2026-05-08 · **Superseded:** 2026-05-09
- **Commit:** 10
- **Decided by:** Nova (original) · **Superseded by:** Eran Mani
- **Original decision:** LangGraph graph runs synchronously (`graph.invoke()`), dispatched via `asyncio.to_thread()`.
- **Why superseded:** This is a production system — streaming responses are a hard requirement. See streaming decision below.

### `graph.astream_events()` + SSE `StreamingResponse` (Commit 10)
- **Date:** 2026-05-09
- **Commit:** 10
- **Decided by:** Eran Mani
- **Decision:** LangGraph graph is invoked with `graph.astream_events()` (not `graph.invoke()`). `chat.py` returns `StreamingResponse(media_type="text/event-stream")`. Tokens arrive as `on_chat_model_stream` events; the final `done` event carries `user_level` and `assessed_topics`.
- **Alternatives considered:** `graph.invoke()` inside `asyncio.to_thread()` (synchronous, no streaming); asyncio.Queue callback pattern (complex, non-idiomatic).
- **Consequences:** The frontend receives tokens as they are generated — no wait for the full response. All LangGraph nodes must use `async` I/O or be dispatched with `asyncio.to_thread()` for blocking calls. `chat.py` and any API tests must be updated to consume SSE rather than a JSON dict. `ui.py` (NiceGUI) streaming display is addressed in Commit 18.

### `Annotated[list[BaseMessage], add_messages]` replaces `conversation_history: str`
- **Date:** 2026-05-09
- **Commit:** 07
- **Decided by:** Eran Mani
- **Decision:** `AgentState.messages` is typed as `Annotated[list[BaseMessage], add_messages]`. The `add_messages` reducer appends incoming messages rather than replacing the list. Conversation history is reconstructed automatically from the `MemorySaver` checkpointer when `thread_id` is passed in graph config — no application code needed.
- **Alternatives considered:** Keeping `conversation_history: str` formatted from `SessionMemory.format_history()` before graph entry.
- **Consequences:** `session_id` is no longer an `AgentState` field — it is the `thread_id` in `{"configurable": {"thread_id": session_id}}`. `SessionMemory` class (`src/rag/memory/conversation.py`) is deleted in Commit 10. `generate_node` receives full prior conversation in `state["messages"]` and prepends a `SystemMessage` with context before calling the LLM. The Commit 03 handoff about `format_history()` is obsolete and removed from open handoffs.

### `MemorySaver` checkpointer replaces `SessionMemory` class
- **Date:** 2026-05-09
- **Commit:** 10
- **Decided by:** Eran Mani
- **Decision:** LangGraph's built-in `MemorySaver` checkpointer handles cross-turn persistence. `src/rag/memory/conversation.py` (the `SessionMemory` class) is deleted in Commit 10 and must not be referenced anywhere afterward.
- **Alternatives considered:** Keeping `SessionMemory` and formatting history as a string before each graph invocation; using `SqliteSaver` for disk persistence from the start.
- **Consequences:** `MemorySaver` is in-process — history is lost on app restart. This is acceptable for portfolio/single-instance deployment. When multi-instance or restart-persistence is needed, swap to `SqliteSaver(conn)` or `PostgresSaver` — the only change is the `checkpointer=` argument at graph compile time. The Redis query-level cache is independent and unaffected.

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
| LangGraph streaming — UI token display (NiceGUI) | SSE wired in Commit 10; NiceGUI reactive display deferred | Commit 18 |
| Prometheus/Grafana dashboard configuration | Infrastructure present; dashboards need production data to tune | Post-deployment |
| LLM fine-tuning | Requires evaluation data from production interactions | Future phase |
| A/B testing framework | Requires production traffic | Future phase |
| Subscription/billing | Out of scope for portfolio | Future phase |
| Exact OpenAI model ID | Team Lead to confirm when target model is available | Commit 02 or later |

### History injection after retrieval, not before
- **Date:** 2026-05-09
- **Commit:** 03
- **Decided by:** Commit spec (Claude)
- **Decision:** `format_history(session_id)` is called after `retrieve()` — the retrieved docs are selected using the raw user question, not a history-augmented query.
- **Alternatives considered:** Prepending history to the query before retrieval (history-aware retrieval).
- **Consequences:** Retrieval stays fast and cache-friendly (same question always hits the same docs). History influences only what the LLM says, not what is retrieved. A follow-up question like "explain that differently" will retrieve on those three words, not on the full context — this is a known limitation of the current pipeline, resolved when the LangGraph graph replaces chain.py.

### Both tables in the same SQLite file (`app_users.db`)
- **Date:** 2026-05-09
- **Commit:** 04
- **Decided by:** Rex (applied) + Viktor (confirmed)
- **Decision:** `user_profiles` lives in `data/app_users.db` alongside `users` — not a separate database file.
- **Reason:** SQLite FK enforcement only works across tables in the same connection/file. Splitting into two files would require application-level cascade logic instead of `ON DELETE CASCADE`. A single connection also avoids coordinating two lifespan init calls.
- **Consequences:** Both `auth/db.py` and `profile/db.py` open the same file path. Init order matters: `init_user_db()` must run before `init_profile_db()` so the `users` table the FK references exists.

### `_connect()` duplicated across `auth/db.py` and `profile/db.py`
- **Date:** 2026-05-09
- **Commit:** 04
- **Decided by:** Rex (applied) + Sage (flagged as refactor candidate)
- **Decision:** Both modules contain an identical `_connect()` rather than sharing one from `src/app/core/db.py`.
- **Reason:** Domain separation — `auth/` and `profile/` are independent modules. The duplication is intentional at this stage to keep each module self-contained.
- **Consequences:** Any future security hardening added to one `_connect()` must also be applied to the other. Tracked as an architecture debt. Refactor to `src/app/core/db.py` is a named candidate for a future commit if the duplication spreads to a third module.

### `topic_scores` stored as flat `dict[str, float]` — no per-topic interaction counts
- **Date:** 2026-05-09
- **Commit:** 04
- **Decided by:** Team Lead
- **Decision:** `topic_scores` JSON format is `{"module_slug": float}` — not `{"module_slug": {"score": float, "n": int}}`.
- **Alternatives considered:** Nested format with per-topic interaction count to support confidence-weighted display ("only show a score after ≥3 interactions on this module").
- **Reason:** The entire protocol (Commits 07–19) is specced around `dict[str, float]`. Changing the format would require reopening 8+ commit specs. For a 6-module portfolio demo, flat scores are sufficient — the aggregate `interaction_count` column can proxy any threshold logic needed. The nested format is better for a production learning platform; flat is the right call here.
- **Consequences:** Per-topic interaction counts are not tracked. If confidence-weighted display is added later, it requires a JSON migration on the `topic_scores` TEXT column. This is a known permanent limitation, not an oversight.

### JSON string storage for `topic_scores`, `strengths`, `gaps`
- **Date:** 2026-05-09
- **Commit:** 04
- **Decided by:** Rex (applied) + Viktor (advisory)
- **Decision:** Store `topic_scores`, `strengths`, and `gaps` as JSON strings in SQLite (`TEXT DEFAULT '{}'`, `TEXT DEFAULT '[]'`). The service layer (Commit 05) owns serialization (`json.dumps`) and deserialization (`json.loads`).
- **Reason:** Avoids SQLite JSON function dependency. Keeps the DB layer responsible only for persistence, not data structure. Portable to PostgreSQL JSONB without schema changes.
- **Consequences:** Every write path must call `json.dumps()` before INSERT/UPDATE. Every read path must call `json.loads()` after SELECT. A missed `json.dumps()` on a Python dict will store a Python-syntax string (single quotes) that `json.loads()` will fail to parse — validated in Commit 05 tests.

### Conversation history not included in LLM cache key
- **Date:** 2026-05-09
- **Commit:** 03
- **Decided by:** Rex (flagged) + Claude (accepted as known gap)
- **Decision:** The LLM response cache key (`question + docs[:100]`) does not include `session_id` or `conversation_history`. A repeated identical question in the same session may be served from cache, ignoring any history change since the first answer.
- **Reason:** Session-aware cache keys would require a per-session Redis namespace and complicate cache invalidation. For a portfolio system this edge case is acceptable. The cache key is partially addressed in Commit 17 (adds `user_level`), but conversation history is not incorporated at any commit — this is a known permanent limitation of the cache strategy.
- **Consequences:** The test gate "asking 'What did I just ask?' returns a response that references the prior turn" must use a question that hasn't been asked before in the same test session, or the cache must be cleared between test runs.

### Column allowlist in `update_profile` — defence-in-depth against injection
- **Date:** 2026-05-09
- **Commit:** 05
- **Decided by:** Sage (flagged) + Viktor (confirmed) + Rex (applied)
- **Decision:** `update_profile` validates kwarg keys against `_ALLOWED_PROFILE_COLUMNS` (a `frozenset`) before building the dynamic SQL SET clause. Unknown keys raise `ValueError` before SQL runs.
- **Reason:** Column names cannot be parameterized in SQL — they must be interpolated as strings. Without a guard, any future caller that passes an attacker-influenced key (e.g., a LangGraph node spreading LLM output into `**kwargs`) creates a structural injection path. The frozenset is immutable and module-scoped — it cannot be patched by a caller at runtime.
- **Consequences:** All callers must use the exact column names in the frozenset. The `updated_at` column is excluded from the allowlist intentionally — it is always set internally by `update_profile`, never by callers.

### Frozenset allowlist is the project-wide standard for all dynamic SQL
- **Date:** 2026-05-09
- **Commit:** 05 (established here — applies to all future commits)
- **Decided by:** Sage (validated) + Rex (applied)
- **Decision:** Any function in this codebase that builds SQL dynamically from caller-supplied keys must validate those keys against a module-scoped `frozenset` before touching the database. This is not specific to the profile service — it applies to every future service with dynamic column updates (scoring queries in Commit 14, any analytics extensions).
- **Reason:** Column names cannot be parameterized — interpolation is unavoidable. A frozenset guard is the only reliable defense at the call boundary. Making this a project-wide rule prevents future agents building dynamic queries from creating injection paths unknowingly.
- **Consequences:** Every future function with dynamic SQL needs a corresponding `_ALLOWED_X_COLUMNS` frozenset defined at module scope. System-managed columns (`updated_at`, `created_at`) are intentionally excluded from caller-facing allowlists.

### `get_or_create_profile` absorbs `IntegrityError` on concurrent creation
- **Date:** 2026-05-09
- **Commit:** 05
- **Decided by:** Viktor (flagged) + Rex (applied)
- **Decision:** `get_or_create_profile` wraps `create_profile()` in a `try/except sqlite3.IntegrityError: pass` block and always re-fetches after the block, regardless of whether the insert succeeded or was lost to a race.
- **Reason:** A function named `get_or_create` must never surface `IntegrityError` to its callers. The UNIQUE constraint on `user_id` prevents duplicate rows — the `except` block absorbs the race, and the unconditional re-fetch returns whichever row won.
- **Consequences:** On a concurrent first-creation race, one `create_profile` call is silently discarded. The caller always receives the correct row. The loser of the race incurs one extra SELECT — acceptable cost.

### `create_profile` (not `get_or_create_profile`) at registration
- **Date:** 2026-05-09
- **Commit:** 06
- **Decided by:** Rex (applied) + Viktor (advisory)
- **Decision:** The `register` route calls `create_profile(user_id)` directly — not `get_or_create_profile`. A `sqlite3.IntegrityError` on a concurrent duplicate is caught and swallowed; any other exception propagates as 500.
- **Reason:** Registration is the profile's creation event. Using `get_or_create_profile` would mask accidental double-creation by silently returning an existing row — obscuring whether the registration flow ran correctly. Using `create_profile` makes the intent explicit: this is the moment the profile is born.
- **Consequences:** If `create_profile` fails for a non-race reason (e.g., disk full), the user row persists without a profile (see ARCHITECTURE.md Known Debts — non-atomic insert). A future commit may wrap both operations in a shared SQLite transaction on the same connection to prevent orphaned users.

### `retrieval_source` inferred from circuit breaker state inspection around `retrieve()`
- **Date:** 2026-05-09
- **Commit:** 08
- **Decided by:** Nova
- **Decision:** `retrieve_node` calls `chroma_cb.is_available()` immediately before and immediately after calling `retrieve()`. If available both sides → `retrieval_source = "chroma"`. Otherwise → `retrieval_source = "bm25"`.
- **Alternatives considered:** Modifying `retrieve()` to return a path signal alongside the docs; duplicating the routing condition from `retriever.py` inside the node.
- **Reason:** `retrieve()` returns only `list[Document]` — there is no path signal in its return value. Altering the signature would cross a domain boundary (`retriever.py` is the pipeline layer; `retrieve_node` is the graph layer). Duplicating the routing condition would create silent drift the moment `retriever.py` changes. CB state inspection is the only approach that leaves `retrieve()` untouched and gives the node accurate source attribution.
- **Consequences:** The two `is_available()` calls are cheap and idempotent. The pattern handles all three CB states correctly: CLOSED→CLOSED (Chroma ran), OPEN before call (BM25 ran directly), CLOSED→OPEN mid-call (Chroma failed, BM25 fallback activated). This pattern is the established approach for any future node that needs to observe which fallback path ran.

### `get_provider()` called per-invocation in `generate_node`, not at module level
- **Date:** 2026-05-09
- **Commit:** 09
- **Decided by:** Nova
- **Decision:** `generate_node` calls `get_provider().get_llm()` inside the function body on every invocation — not as a module-level singleton.
- **Alternatives considered:** Module-level `llm = get_provider().get_llm()` resolved at import time.
- **Reason:** A module-level singleton freezes the provider at import time. If the OpenAI circuit breaker opens after startup, the module-level `llm` would still point to the OpenAI instance. Per-invocation resolution means every LLM call observes the current CB state — the Ollama fallback actually activates when needed.
- **Consequences:** One extra function-call overhead per generation turn (negligible vs LLM latency). This is the correct pattern for any node that uses a circuit-breaker-guarded provider. All future nodes using `get_provider()` must follow the same pattern.

*Last updated: 2026-05-09 — Commit 09 complete (generate_node per-invocation provider pattern)*
