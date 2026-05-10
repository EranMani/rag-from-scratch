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

### `build_graph()` factory pattern — no module-level compiled graph singleton
- **Date:** 2026-05-10
- **Commit:** 10
- **Decided by:** Nova (applied) + commit spec (Claude)
- **Decision:** `src/agents/graph.py` exposes `build_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph`. The checkpointer is injected as a parameter; the graph is compiled and returned. No module-level `graph = build_graph(...)` singleton.
- **Alternatives considered:** Module-level singleton compiled at import time; singleton with a default `MemorySaver()` argument.
- **Reason:** A module-level singleton makes the checkpointer invisible to tests — every test run would share one `MemorySaver` instance and bleed state between threads. The factory pattern lets each test construct an isolated graph with its own checkpointer. It also makes the swap to `SqliteSaver` or `PostgresSaver` a one-line change in `lifespan`, not a surgery on `graph.py`.
- **Consequences:** Callers (currently only `lifespan` in `main.py`) are responsible for constructing the checkpointer and calling `build_graph()`. Tests construct fresh graphs per test class. The `BaseCheckpointSaver` type parameter is the correct abstraction — it accepts any LangGraph-compatible checkpointer.

### `assessed_topics` as the SSE public key for `topic_scores_delta`
- **Date:** 2026-05-10
- **Commit:** 10
- **Decided by:** Nova (applied) + Mira (flagged for documentation)
- **Decision:** The final SSE `done` event exposes `topic_scores_delta` from `AgentState` under the key `assessed_topics`: `{"type": "done", "user_level": ..., "assessed_topics": {...}}`. The internal `AgentState` field name (`topic_scores_delta`) is not exposed in the SSE schema.
- **Reason:** `topic_scores_delta` describes implementation detail (a sparse delta, not the full score). `assessed_topics` is closer to the consumer's mental model (which topics were just assessed). The renaming at the serialization boundary keeps the internal state field name accurate while giving the SSE consumer a more stable, intention-revealing name.
- **Consequences:** Any consumer of the `done` event must use `assessed_topics`, not `topic_scores_delta`. This is the locked SSE contract from Commit 10 forward. Commit 19 (Aria) will render `user_level` from this event — if `assessed_topics` is also needed there, Aria must use this key name. A future rename would require coordinated changes in `chat.py` and all SSE consumers.

### `add_conditional_edges` with both paths to the same node (Commit 12)
- **Date:** 2026-05-10
- **Commit:** 12
- **Decided by:** Nova (applied) + Viktor (gate-fix pass)
- **Decision:** `_route_after_assess` in `graph.py` uses `add_conditional_edges` even though both branches (assessment_error True and False) route to the same destination (`update_profile_node`). The routing function returns `"update_profile"` unconditionally — no dead conditional.
- **Alternatives considered:** Plain `builder.add_edge("assess", "update_profile")` — technically correct and simpler; `add_conditional_edges` with a redundant `if` statement — rejected by Viktor as dead code.
- **Reason:** `add_conditional_edges` makes the fallback pattern visible in LangGraph's graph inspector (`.get_graph()` shows two labeled edges from `assess` instead of one). The named function `_route_after_assess` is independently testable. When Commit 15 potentially diverges the paths, the routing logic lives in an established function — no structural change to `build_graph` required.
- **Consequences:** The routing function must never contain a dead `if` statement (Viktor hard block). Both paths must be listed in the mapping dict passed to `add_conditional_edges`. Future commits that extend the conditional must update only `_route_after_assess` — not the graph wiring.

### `update_profile_node` stub in `graph.py`, not a separate file (Commit 12)
- **Date:** 2026-05-10
- **Commit:** 12
- **Decided by:** Nova (applied) + commit spec (Claude)
- **Decision:** The passthrough stub for `update_profile_node` is declared as a function directly in `src/agents/graph.py` — not in a separate `src/agents/nodes/update_profile.py` file.
- **Alternatives considered:** Creating `src/agents/nodes/update_profile.py` with a stub that will be replaced in Commit 15.
- **Reason:** A separate file for a 1-line passthrough implies it is a permanent resident. Keeping the stub in `graph.py` with a `# STUB (Commit 12)` docstring clearly signals its temporary status and prevents Commit 15 from needing to restructure file ownership. Commit 15 will replace the inline stub with a real implementation and move it to its own file at that point.
- **Consequences:** Commit 15 will create `src/agents/nodes/update_profile.py`, import it, and replace the inline stub in `graph.py`. This is a deliberate two-step — the stub in `graph.py` is not meant to grow in place.

### Assessment prompt in `src/agents/prompts/` — not inlined in the node (Commit 13)
- **Date:** 2026-05-10
- **Commit:** 13
- **Decided by:** Nova (applied) + identity file standard
- **Decision:** The assessment `ChatPromptTemplate` lives in `src/agents/prompts/assessment.py`, not inside `assess.py`. The module exposes a single `assessment_prompt` constant imported by the node.
- **Reason:** Prompts are code — they need version control, independent review, and testability as a unit. Inlining the prompt in the node conflates two concerns: the graph contract (node inputs/outputs) and the LLM interface design (what the model sees). The prompts module is the established home for all future prompt templates.
- **Consequences:** Any commit that changes the assessment prompt must touch `src/agents/prompts/assessment.py`. The node file remains stable — it only changes when the chain interface (not the prompt wording) changes.

### `user_level` not written back to `AgentState` from `assess_node` (Commit 13)
- **Date:** 2026-05-10
- **Commit:** 13
- **Decided by:** Nova (applied) + commit spec
- **Decision:** `AssessmentOutput.user_level` is used inside the assessment chain call but is intentionally discarded — `assess_node` returns only `topic_scores_delta`, `identified_gaps`, and `assessment_error`. It does not write `user_level` back to `AgentState`.
- **Reason:** `user_level` is currently a "turn input" field loaded from the profile before graph entry. If `assess_node` overwrites it mid-graph, the next node sees an assessed level rather than the stored level — a circular update where the LLM's assessment of this turn immediately shifts the context for the next. This is deferred to the Commit 15 design review where the full profile-update cycle is wired.
- **Consequences:** The `user_level` in `AgentState` does not update within a turn. `update_profile_node` (Commit 15) is responsible for recomputing `mastery_level` from the updated `topic_scores` and writing it back — at turn boundaries, not mid-graph.

### LangChain chain mock via `assessment_prompt.__or__` patch (Commit 13)
- **Date:** 2026-05-10
- **Commit:** 13
- **Decided by:** Nova (discovered in testing)
- **Decision:** Tests mock `assess_node`'s LangChain chain by patching `assessment_prompt.__or__ = MagicMock(return_value=mock_chain)`, not by patching `llm.with_structured_output()` and expecting `RunnableSequence` to propagate it.
- **Reason:** The pipe operator (`|`) in `assessment_prompt | llm.with_structured_output(AssessmentOutput)` produces a `RunnableSequence` at the object level. A `MagicMock` returned from `with_structured_output()` is not a `Runnable` — it has no `ainvoke()` protocol that `RunnableSequence` can call. Patching `__or__` on the prompt object intercepts before `RunnableSequence` is constructed, giving full chain control without touching `RunnableSequence` internals.
- **Consequences:** This is the established mock pattern for any future test of a LangChain LCEL chain in this project. Any test that needs to control the output of a `prompt | llm.method()` chain should patch `prompt.__or__` to return a mock that exposes `ainvoke()`.

### Invalid slug filter by value type, not curriculum allowlist (Commit 14)
- **Date:** 2026-05-10
- **Commit:** 14
- **Decided by:** Rex
- **Decision:** `compute_topic_scores` silently drops entries in `assessed_topics` where the value is not `isinstance(score, (int, float))`. Unknown-but-numeric slugs are stored. Non-numeric values are dropped.
- **Alternatives considered:** Validating slug names against a known curriculum allowlist (e.g., a `frozenset` of module names).
- **Reason:** An allowlist couples the scoring service to the curriculum definition. When Nova adds new assessment topics in a future commit before the allowlist is updated, valid scores would be silently dropped with no error signal. Value-type filtering is the correct invariant — the scoring contract is "numeric values for any slug name," not "only slugs from a known list."
- **Consequences:** The scoring service will accumulate entries for topic slugs that don't exist in any curriculum. Consumers (UI, profile display) must handle unexpected keys gracefully. If curriculum enforcement is needed in the future, it belongs at the LangGraph node boundary (Nova's `assess_node`), not in the scoring service.

### Silent score clamping to [0.0, 1.0] (Commit 14)
- **Date:** 2026-05-10
- **Commit:** 14
- **Decided by:** Rex (defensive addition, not in spec)
- **Decision:** `compute_topic_scores` clamps any numeric score from `assessed_topics` to `max(0.0, min(1.0, score))` before merging. Out-of-range values (e.g., 1.2 from a hallucinating LLM) are stored as 1.0 rather than propagating upstream.
- **Reason:** The scoring service is the last writeable boundary before profile persistence. Out-of-range scores would cause `get_mastery_level` to return correct-looking results that violate the documented threshold invariants. The LLM is the source of `assessed_topics` — defensive clamping prevents malformed LLM output from corrupting the profile.
- **Consequences:** Spec-compliant callers (scores in [0.0, 1.0]) observe no change. Clamping is silent — there is no warning log when a value is clamped. If monitoring of out-of-range values is needed later, a log call should be added here.

### `DEFAULT_PROMPT` is separate from `PROMPT_TEMPLATES` dict (Commit 17)
- **Date:** 2026-05-10
- **Commit:** 17
- **Decided by:** Nova (applied)
- **Decision:** `DEFAULT_PROMPT` is a standalone `ChatPromptTemplate` object — not a key in `PROMPT_TEMPLATES`. Callers use `PROMPT_TEMPLATES.get(user_level, DEFAULT_PROMPT)` to resolve the correct template with a single call.
- **Alternatives considered:** Including `DEFAULT_PROMPT` as `PROMPT_TEMPLATES["default"]` and using `.get(user_level, PROMPT_TEMPLATES["default"])`.
- **Reason:** A `"default"` key would silently pass if an unknown level string matched exactly (e.g., `None` or `""`). Keeping `DEFAULT_PROMPT` outside the dict makes the fallback contract explicit at the call site and prevents callers from accidentally indexing the dict directly without a fallback.
- **Consequences:** All callers must use `.get(user_level, DEFAULT_PROMPT)` — not `PROMPT_TEMPLATES[user_level]`. The `DEFAULT_PROMPT` import is always required alongside `PROMPT_TEMPLATES`. Any new level added to `PROMPT_TEMPLATES` does not affect the fallback behavior.

### Single `{context}` variable per adaptive template (Commit 17)
- **Date:** 2026-05-10
- **Commit:** 17
- **Decided by:** Nova (applied)
- **Decision:** Each template in `PROMPT_TEMPLATES` (and `DEFAULT_PROMPT`) has exactly one input variable: `{context}`. The user question is not a template variable — it is already present in `state["messages"]` as a `HumanMessage`.
- **Alternatives considered:** Two-variable templates with both `{context}` and `{question}` for explicit question repetition in the system prompt.
- **Reason:** The question is in the message list that the LLM already sees. Injecting it again as a template variable would duplicate it in the system prompt, potentially confusing the model about which occurrence to prioritize. The only thing not already in the conversation that the template must inject is the retrieved context.
- **Consequences:** `generate_node` calls `template.format_messages(context=context)` with exactly one argument. Passing any other variable raises a `KeyError` from `ChatPromptTemplate`. Tests verify this single-variable contract for all 5 levels and the default.

### Scoring-derived `gaps` written to DB, not LLM `identified_gaps` (Commit 15)
- **Date:** 2026-05-10
- **Commit:** 15
- **Decided by:** Nova (discovered in implementation)
- **Decision:** `update_profile_node` writes `score_update["gaps"]` (the scoring-service-derived set of slugs with score ≤ 0.3) to the `gaps` column in `user_profiles` — not `state["identified_gaps"]` (the raw LLM output from `assess_node`).
- **Alternatives considered:** Persisting `identified_gaps` directly from `AgentState`; writing both fields independently.
- **Reason:** `AgentState.identified_gaps` is the LLM's per-turn raw assessment — sparse, noisy, and not reflecting the user's full learning history. `score_update["gaps"]` is derived from the fully merged `topic_scores` after this turn's delta is applied — it reflects cumulative mastery, not just this turn's interaction. Persisting the LLM's raw gaps would overwrite prior gap history with a single-turn signal. The scoring-derived gaps are the correct long-term state.
- **Consequences:** `identified_gaps` in `AgentState` is transient context for the current turn only. It is passed to `compute_topic_scores` (the interaction_count signature), but the field that reaches the DB is always the score-derived set. Any UI or downstream consumer must read gaps from the profile, not from the SSE event.

### Fast-exit order in `update_profile_node`: `user_id` before `assessment_error` (Commit 15)
- **Date:** 2026-05-10
- **Commit:** 15
- **Decided by:** Nova (ordering decision)
- **Decision:** `update_profile_node` checks `user_id is None` first, then `assessment_error`. If both conditions are true, the function returns at the `user_id` check without calling `get_profile_by_user_id`.
- **Reason:** An anonymous user can never have a profile to fetch. Checking `assessment_error` first would require `user_id` to be present before skipping — for anonymous users, a DB lookup attempt would be made with `user_id=None` before the error flag is checked. Ordering `user_id` first eliminates any DB round-trip for anonymous users under all conditions.
- **Consequences:** Tests must verify `get_profile_by_user_id` is never called when `user_id=None`, regardless of other state fields. The fast-exit pattern is standard for all future node implementations where user identity is a precondition.

### Null-byte separator in query cache key (`f"{question}\x00{user_level}"`) (Commit 18)
- **Date:** 2026-05-10
- **Commit:** 18
- **Decided by:** Viktor (flagged) + Sage (confirmed) + Nova (applied)
- **Decision:** The composite cache key for `get_query`/`set_query` is `SHA-256(f"{question}\x00{user_level}")`, not `SHA-256(question + user_level)`.
- **Alternatives considered:** JSON serialization (`json.dumps([question, user_level])`); length-prefix encoding; naive concatenation.
- **Reason:** Naive string concatenation is not injective: `("foobar", "expert")` and `("foo", "barexpert")` produce identical pre-hash input and therefore identical cache keys. A cross-level cache collision causes a novice user to receive an expert-framed cached answer (or vice versa) — a silent correctness failure. The null byte `\x00` cannot appear in UTF-8 question text or the valid level strings (`novice`, `beginner`, `intermediate`, `advanced`, `expert`), making the separator a reliable field delimiter. The fix is simpler than JSON serialization and produces an unambiguous two-field composite key.
- **Consequences:** Cache keys for the same question at different mastery levels are guaranteed distinct. Test `test_ambiguous_inputs_do_not_collide` in `tests/test_cache.py` verifies the specific collision pair that motivated the fix. Any future composite key in this codebase should use a null-byte separator or equivalent non-ambiguous encoding — not raw concatenation.

### `ChatResponse` as a typed Pydantic schema for the SSE `done` event (Commit 18)
- **Date:** 2026-05-10
- **Commit:** 18
- **Decided by:** Nova (applied) + Viktor (gate recommendation)
- **Decision:** The SSE `done` event is serialized from `ChatResponse(BaseModel)` via `.model_dump()`. `ChatResponse` is the single source of truth for the wire format: `answer: str`, `user_level: str | None`, `assessed_topics: dict[str, float]`.
- **Alternatives considered:** Continuing to hand-construct the `done` dict inline in `chat.py` (`{"type": "done", "user_level": ..., "assessed_topics": ...}`).
- **Reason:** A hand-constructed dict has no type enforcement. If `AgentState` renames `topic_scores_delta`, the inline dict construction silently breaks the wire format — no static error, no test failure unless the consumer notices. A Pydantic model at this boundary means field renames or type changes produce an error at the `build_chat_response(state)` call site, not in the client. The model also serves as the living documentation of the `done` event schema — the docstring and field types are authoritative.
- **Consequences:** All SSE consumers must use `ChatResponse` field names (`answer`, `user_level`, `assessed_topics`). Adding or removing fields from the `done` event requires changing `ChatResponse` — this is intentional, as it forces a conscious decision about wire-format stability. Commit 19 (Aria) consumes these fields directly.

### `user_level: str | None` in `ChatResponse` — `None` means "assessment unavailable" (Commit 18)
- **Date:** 2026-05-10
- **Commit:** 18
- **Decided by:** Nova (applied) + Viktor (advisory) + Mira (confirmed)
- **Decision:** `ChatResponse.user_level` defaults to `None`, not `"novice"`. `None` carries a specific meaning: assessment did not run (e.g., `assess_node` errored and `assessment_error=True`). The UI (Commit 19) must treat `None` as "assessment unavailable" — not as a fallback level.
- **Alternatives considered:** Defaulting to `"novice"` to match the `get_user_level()` fallback in `chat.py`.
- **Reason:** Using `"novice"` would conflate two distinct states: "user is a novice" and "assessment failed." A UI panel that shows the mastery level must be able to display "unknown" or "—" when assessment didn't run — which requires `None` to be distinguishable from any real level. Collapsing both states to `"novice"` would mislead users whose assessment failed into thinking they have a confirmed novice profile.
- **Consequences:** Any SSE consumer must handle `user_level: null` explicitly. Commit 19 spec must define the null display state before Aria starts. The inline docstring on `ChatResponse.user_level` carries this contract for future maintainers.

### Nested `@ui.refreshable` pattern for profile panel (Commit 19)
- **Date:** 2026-05-10
- **Commit:** 19
- **Decided by:** Aria
- **Decision:** `profile_panel` is defined as a nested `@ui.refreshable async def` inside `index()`. It closes over `http()` and `auth_headers()` without parameter threading.
- **Alternatives considered:** Module-level function accepting the closures as arguments; separate NiceGUI component class.
- **Reason:** NiceGUI's `@ui.refreshable` decorator requires the function to be in scope of the caller that invokes `.refresh()`. Nesting it inside `index()` gives it access to all request-scoped closures (`http()`, `auth_headers()`, `session`) without passing them as arguments. A module-level function would require argument threading or global state — both add coupling. The nested pattern is the idiomatic NiceGUI approach for per-page refreshable components.
- **Consequences:** `profile_panel.refresh()` must be called from within `index()` — Commit 20's `send()` closure has access because it is also nested in `index()`. The function is not independently testable without a NiceGUI test harness.

### All 6 topic modules always rendered in profile panel (Commit 19)
- **Date:** 2026-05-10
- **Commit:** 19
- **Decided by:** Aria
- **Decision:** When `topic_scores` is non-empty, all 6 modules in `_MODULE_LABELS` are rendered as progress bars. Modules with no score yet default to `0.0`.
- **Alternatives considered:** Only render modules where the user has a non-zero score (progressive disclosure).
- **Reason:** Showing all 6 modules sets the user's expectations about the full scope of the curriculum. A user who has explored only 2 topics can see exactly which 4 remain — supporting goal-directed learning. Hiding unvisited modules would require a second "Topics to explore" list or tooltip, adding UI complexity for little gain.
- **Consequences:** A fresh user who has interacted at least once (so `topic_scores` is non-empty) will see 4 bars at 0.0 alongside 2 partial bars. Mira flagged this as potentially discouraging — accepted tradeoff. If telemetry suggests users disengage at this point, move to progressive disclosure in a future commit.

*Last updated: 2026-05-10 — Commit 19 complete (profile sidebar panel; layout refactor; @ui.refreshable pattern)*
