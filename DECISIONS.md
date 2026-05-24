# DECISIONS.md — RAG from Scratch

> Maintained by Claude. Every non-obvious design choice made during this project
> is logged here with the reason it was made.
> Last updated: 2026-05-24

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

## Curriculum Design (Commit 22 — Lara)

### Phase 2 dual gate (per-topic 0.70 AND mean 0.75)
- **Date:** 2026-05-11
- **Commit:** 22
- **Decided by:** Lara
- **Decision:** Phase 2 requires each of its four topics to reach 0.70 individually AND their mean to reach 0.75. Phase 1 and Phase 3 have only per-topic minimums.
- **Reason:** Phase 2 topics (chunking, vector databases, retrieval methods, context and prompting) are interdependent — a learner who aces vector databases but barely passes retrieval methods will struggle in Phase 3 where both are assumed as fluent foundation. The mean floor ensures balanced competency, not just that each topic crosses the bare minimum.

### Phase 3 minimum raised to 0.75
- **Date:** 2026-05-11
- **Commit:** 22
- **Decided by:** Lara
- **Decision:** Phase 3 topics (`evaluation_and_metrics`, `production_patterns`) require 0.75 per-topic, not 0.70.
- **Reason:** Phase 3 represents operational competency — knowledge errors here (e.g., misunderstanding cache invalidation or index staleness) have downstream consequences in a production system. The 0.75 floor reflects higher stakes for production knowledge.

### Spaced repetition scoring: `0.7 × current + 0.3 × best_prior`
- **Date:** 2026-05-11
- **Commit:** 22
- **Decided by:** Lara
- **Decision:** Topic score formula: `topic_score = 0.7 × current_session_score + 0.3 × best_prior_session_score`. Best prior is the highest session score ever achieved for that topic, not the most recent.
- **Alternatives considered:** Simple current-session average; running mean across all sessions.
- **Reason:** The 0.7/0.3 split primarily reflects current performance (most recent knowledge state) while rewarding persistence — a learner who scores 0.80 after a 0.60 start is not identical to one who scored 0.80 first try. Running mean would penalize early struggle indefinitely.

### Null vs. 0.0 for unassessed topics
- **Date:** 2026-05-11
- **Commit:** 22
- **Decided by:** Lara
- **Decision:** Topics with no completed sessions have score `null`, not `0.0`. Gate logic must treat `null` as failing — `null >= 0.70` is `false`.
- **Reason:** `0.0` means the learner attempted assessment and scored zero. `null` means they have not attempted it. These are meaningfully different states for remediation logic: a learner at 0.0 needs different support than one who hasn't tried yet. Conflating them would also risk a gate-passing bug where a null topic satisfies no threshold check.

### Minimum 3 questions per session for a valid score update
- **Date:** 2026-05-11
- **Commit:** 22
- **Decided by:** Lara
- **Decision:** Sessions with fewer than 3 questions produce no score update. The existing score is unchanged and the incomplete session is discarded.
- **Reason:** A single question can score 0.0, 0.5, or 1.0 — each anchors the score to an extreme. Three questions is the minimum for a score with meaningful granularity (nine distinct outcomes from all-correct to all-incorrect with partial credit). Fewer questions produce misleadingly high or low scores from a single unlucky/lucky answer.

---

## Scoring Model Product Spec (Commit 23 — Mira + Lara)

### Assessment trigger: readiness score 0.60 OR 5 content turns
- **Date:** 2026-05-11
- **Commit:** 23
- **Decided by:** Mira (product) + Lara (curriculum)
- **Decision:** Assessment mode triggers when (A) the user's topic score reaches 0.60 or above, or (B) the user has exchanged 5+ content turns on a topic with no prior assessment. Explicit user request ("quiz me") is always honored immediately.
- **Reason:** 0.60 sits above chance-correct territory and below the gate minimum (0.70) — testing here is timely, not premature. The 5-turn engagement rule catches first-time learners who are ready by depth of interaction even without a prior score. Neither trigger alone covers all entry paths.

### No score decay
- **Date:** 2026-05-11
- **Commit:** 23
- **Decided by:** Mira
- **Decision:** Topic scores do not decrease due to inactivity. Scores persist until a new valid assessment session updates them.
- **Alternatives considered:** Time-based decay (score drops each week of inactivity); event-triggered decay (downweight prior score after N days away).
- **Reason:** The 0.7/0.3 spaced-repetition formula already handles recency — a poor current session at 0.7 weight reduces the score even without explicit decay. Time-based decay punishes learners who pause for personal reasons (illness, work deadlines) without reflecting any change in their actual knowledge. Decay is an output of new assessment, not a time-based penalty.

### `user_level` mapped to phase gate state, not score average
- **Date:** 2026-05-11
- **Commit:** 23
- **Decided by:** Mira (product) + Lara (curriculum)
- **Decision:** `user_level` is determined entirely by phase gate state (`phase_1_passed`, `phase_2_passed`, `phase_3_passed`), not by score average. Evaluation order: `expert` → `advanced` → `intermediate` → `beginner` → `novice`.
- **Alternatives considered:** Average-based mapping (current implementation): novice <0.2, beginner 0.2–0.4, intermediate 0.4–0.6, advanced 0.6–0.8, expert ≥0.8.
- **Reason:** Score-average mapping conflates "scored high on two topics" with "scored adequately across eight." A learner who passed Phase 1 at 0.70 each and hasn't touched Phase 2 would read as `advanced` under the average formula (mean = 0.70 on two topics). Phase gate state is the correct unit of curriculum position for the adaptive prompt system.

### One deferral per topic per session (bounded avoidance)
- **Date:** 2026-05-11
- **Commit:** 23
- **Decided by:** Mira
- **Decision:** The user may defer assessment once per topic per session. A second deferral in the same session is not honored — the agent delivers the first question anyway. Deferral state resets at the start of each new session.
- **Alternatives considered:** Unlimited deferrals; no deferral allowed.
- **Reason:** Unlimited deferrals create an avoidance loop where a user never gets assessed despite trigger conditions continuously firing. No deferral would feel coercive for a learner who genuinely needs more time. One deferral balances respect for learner readiness with prevention of indefinite avoidance.

### Transparent assessment — no mid-session numeric exposure
- **Date:** 2026-05-11
- **Commit:** 23
- **Decided by:** Mira
- **Decision:** Assessment is fully transparent (the agent announces when it is testing the user, names the topic, and reports results after the session). The agent does not expose numeric score thresholds (e.g., "you need 0.70 to pass") or per-question score deltas mid-session.
- **Reason:** Hidden assessment erodes trust in an educational tool where users can see their profile scores — a fully opaque system would be internally inconsistent. Showing thresholds during assessment creates gaming: learners calibrate answers to hit a number rather than demonstrate understanding. The post-session summary is the correct reveal point.

---

## Assessment Engine Implementation (C24)

### `EvaluationOutput` as a separate Pydantic model from `AssessmentOutput` (Commit 24)
- **Date:** 2026-05-11
- **Commit:** 24
- **Decided by:** Nova
- **Decision:** `assess_node` evaluation mode uses a new `EvaluationOutput` model (`verdict: str`, `confidence: float`, `identified_gaps: list[str]`, `user_level: str`) with `.with_structured_output(EvaluationOutput)` — not `AssessmentOutput`.
- **Alternatives considered:** Repurposing `AssessmentOutput` by adding a `verdict` field.
- **Reason:** `AssessmentOutput` uses `TopicScoresDelta` for its `topic_scores_delta` field, which Rex's Commit 25 depends on as a stable contract. Adding a `verdict` field to `AssessmentOutput` would change the schema that the rest of the graph and Rex's downstream code references. A separate `EvaluationOutput` is the surgical option: no downstream contract touches it, and `AssessmentOutput`/`TopicScoresDelta` remains unchanged for Rex.
- **Consequences:** `assess_node` now imports `EvaluationOutput`, not `AssessmentOutput`, in evaluation mode. `AssessmentOutput` is not currently used in `assess_node` after this commit — Rex's Commit 25 may choose to retain or remove it when rewriting the scoring layer.

### `_is_evaluation_mode()` uses last-message type inspection, not a state boolean (Commit 24)
- **Date:** 2026-05-11
- **Commit:** 24
- **Decided by:** Nova
- **Decision:** Mode detection in `assess_node` inspects `state["messages"][-1]` type: evaluation mode requires both `pending_test_question` set AND last message is a `HumanMessage`. A separate `evaluation_mode: bool` state flag was not added.
- **Alternatives considered:** Adding `evaluation_mode: bool` to `AgentState` and setting it when injecting a test question.
- **Reason:** The last message being a `HumanMessage` is ground-truth — if the user sent a message, they answered. A separate boolean flag would require a second write on every test-mode turn and creates a consistency risk: `evaluation_mode=True` with no `HumanMessage` last (e.g., a re-invocation mid-session after a bug) would call the LLM with no answer to evaluate. Inspecting the message list is self-consistent and cannot be stale.
- **Consequences:** Test mocks must include at least one `HumanMessage` in `state["messages"]` for evaluation mode tests to trigger correctly.

### `TopicScoresDelta` and `VALID_MODULE_SLUGS` updated to canonical 8-slug set in Commit 24 (Commit 24)
- **Date:** 2026-05-11
- **Commit:** 24
- **Decided by:** Nova (necessary for test correctness)
- **Decision:** The hotfix in Session 11 created `TopicScoresDelta` with the pre-replan 6-slug set (`rag_fundamentals`, `langchain`, etc.). Commit 24 updated both `TopicScoresDelta` and `VALID_MODULE_SLUGS` to the canonical 8-slug set from the 2026-05-11 replan, earlier than Commit 25 (Rex's planned migration).
- **Reason:** Commit 24 loads curriculum files from `knowledge-base/curriculum/questions/<slug>.md` for 8 slugs. With the old `VALID_MODULE_SLUGS` (`rag_fundamentals`, `langchain`), `_select_test_slug()` would never select any of the 8 curriculum slugs — the slug selection falls through to the canonical ordering and all 8 are rejected. The test suite also validates slug membership. Deferring to Commit 25 would leave a broken assessment node that can never select a valid curriculum question.
- **Consequences:** Rex's Commit 25 still handles all scoring-layer changes (`compute_topic_scores`, session formula, phase gates). The only change that arrived early is the slug definition itself in `state.py`. Rex should verify `VALID_MODULE_SLUGS` matches expectations before Commit 25 begins.

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

### `ui.timer` lifecycle: `stage_active` guard + `finally` ordering (Commit 20)
- **Date:** 2026-05-10
- **Commit:** 20
- **Decided by:** Viktor (gate recommendation) + Aria (applied)
- **Decision:** Two cooperating patterns protect the timer-driven stage label from use-after-delete:
  1. `stage_active = [True]` mutable flag (same list-in-closure idiom as `stage_idx`) is checked at the top of `_advance`; set to `False` as the first action in `finally`.
  2. `finally` block sequencing: `stage_active[0] = False` → `stage_timer.cancel()` → `thinking.delete()`. The flag fires before cancel, so any queued callback that arrives after cancel hits the early return and never touches `thinking`.
- **Why not rely on `cancel()` alone:** NiceGUI timers run in the background event loop. `cancel()` prevents future scheduling but cannot guarantee it drains a callback already queued before cancel was called. The flag provides a hard synchronous barrier independent of the event-loop's internal callback queue.
- **Consequences:** This is the project-wide pattern for any `ui.timer` paired with a UI element that may be deleted before the timer's natural expiry. The create → `stage_active=[True]` → `try` → `finally: flag=False / cancel / delete` sequence is the correct lifecycle. Relying on `cancel()` alone without a guard flag is incorrect for NiceGUI's event model.

## Production Compose Patterns (C21)

### Dev monitoring services behind `profiles: [monitoring]` (Commit 21)
- **Date:** 2026-05-10
- **Commit:** 21
- **Decided by:** Adam (applied) + commit spec
- **Decision:** ELK (elasticsearch, logstash, kibana), Prometheus, and Grafana services in `docker-compose.yml` (dev) are placed behind `profiles: [monitoring]`. `docker compose up` runs only the core stack (app, chroma, redis, ollama). `docker compose up --profile monitoring` activates the full stack.
- **Alternatives considered:** Keeping all services always-on in dev (prior behavior); creating a separate `docker-compose.monitoring.yml` override.
- **Reason:** A new contributor should be able to run the application without pulling and starting five additional containers (3.5GB+ combined). The monitoring stack adds friction to `git clone && make up` with no benefit for contributors focused on application code. The profile flag is explicit and discoverable — the overhead is opt-in, not invisible.
- **Consequences:** Operators running full end-to-end logging tests in dev must remember `--profile monitoring`. `Makefile` targets for the monitoring stack should expose this flag (future Commit 22/23 scope).

### CHROMA_PORT: container-internal (8000) vs. dev host mapping (8001:8000) (Commit 21)
- **Date:** 2026-05-10
- **Commit:** 21
- **Decided by:** Viktor (gate finding) + Adam (resolved)
- **Decision:** `config.py` defaults `chroma_port: int = 8001`. This value matches the dev compose host mapping (`ports: "8001:8000"`) for external tooling access. For container-to-container communication (both dev and prod), the correct port is 8000 — the container's listening port. In `docker-compose.prod.yml`, `CHROMA_PORT=8000` is explicitly set in the app service `environment:` block. `.env.prod.example` documents `CHROMA_PORT=8000` with a comment explaining the distinction.
- **Alternatives considered:** Changing the config.py default to 8000; changing the dev compose mapping to `"8000:8000"`.
- **Reason:** The config.py default of 8001 is used for local (host-side) tooling — e.g., connecting a ChromaDB client from a terminal session while compose is running. Changing the default would break that use case. Changing the compose mapping would remove host-side access. The correct fix is to be explicit in prod: the `environment:` override in `docker-compose.prod.yml` takes precedence over `.env.prod` and guarantees the container-internal port regardless of what an operator puts in their env file.
- **Consequences:** Any future prod compose environment that expects to use `CHROMA_PORT` from `.env.prod` will be silently overridden to 8000. This is intentional — the prod compose is authoritative about container topology, and `.env.prod` should not be able to break inter-service connectivity.

## Curriculum Design Decisions (C22)

### Phase 2 dual gate: per-topic minimum AND mean threshold
- **Date:** 2026-05-11
- **Commit:** 22
- **Decided by:** Lara
- **Decision:** Phase 2 advancement requires both (a) each of the four topics ≥ 0.70, AND (b) the mean across all four topics ≥ 0.75. Phase 1 and Phase 3 have per-topic minimums only (0.70 and 0.75 respectively).
- **Reason:** Phase 2 topics (chunking_strategies, vector_databases, retrieval_methods, context_and_prompting) are interdependent — a learner who aces vector databases but barely passes retrieval methods will have fragile foundations in Phase 3 where both domains are assumed fluent. A single per-topic floor allows one weak topic to drag the average without triggering failure. The 0.75 mean floor catches imbalanced mastery without being punitive for learners who genuinely need more time on one topic.
- **Consequences:** Gate logic must compute both the per-topic check AND the mean. Phase 1 and Phase 3 do not use a mean floor — their topics are less interdependent. Fully specified in `knowledge-base/curriculum/gates.md` with a machine-readable JSON block for Nova and Rex.

### Phase 3 minimum threshold raised to 0.75 (vs. 0.70 for Phase 1)
- **Date:** 2026-05-11
- **Commit:** 22
- **Decided by:** Lara
- **Decision:** Both Phase 3 topics (`evaluation_and_metrics`, `production_patterns`) require a per-topic score of ≥ 0.75. Phase 1 topics require ≥ 0.70.
- **Reason:** Phase 3 covers operational competency — measuring quality (RAGAS), identifying failure modes, and making production architecture decisions. A learner who passes at 0.70 may understand concepts without having the judgment to safely operate a production system. The 0.75 floor reflects that production knowledge has higher downstream consequences than foundational knowledge.
- **Consequences:** A learner near the Phase 2/3 boundary who has 0.70-qualified on all Phase 2 topics needs to reach 0.75 on each Phase 3 topic. The higher Phase 3 bar also communicates to the learner that the final phase requires deeper engagement.

### Spaced repetition weighting in topic score formula
- **Date:** 2026-05-11
- **Commit:** 22
- **Decided by:** Lara
- **Decision:** `topic_score = 0.7 × current_session_score + 0.3 × best_prior_session_score`. If no prior session exists: `topic_score = current_session_score`. Uses `best_prior_session_score` (not average of all priors) as the second term.
- **Alternatives considered:** Simple current-session mean (ignores learning arc); running average of all sessions (penalizes early struggle permanently).
- **Reason:** Primarily reflects current performance (0.7 weight) while rewarding learning persistence (0.3 weight on best prior). A learner who scored 0.60 the first time and 0.85 the second time should not be scored identically to one who scored 0.85 on their first attempt. Using `best_prior_session_score` (not average) avoids penalizing repeated attempts with early poor scores.
- **Consequences:** Nova's assessment engine and Rex's scoring service must implement this formula exactly as specified. Any change to the formula requires coordinated updates across `assess_node`, the scoring service, and this document. Specified in `knowledge-base/curriculum/gates.md`.

### Null vs. 0.0 for unassessed topics
- **Date:** 2026-05-11
- **Commit:** 22
- **Decided by:** Lara
- **Decision:** A topic with no completed sessions has score `null`, not `0.0`. Gate logic must treat `null` as failing (null ≥ threshold evaluates to `false`).
- **Reason:** `0.0` conflates two distinct states: "learner attempted and scored zero" versus "learner has not attempted." A system that needs to decide whether to prompt the learner to attempt a topic or to remediate an existing score requires this distinction. An unassessed topic accidentally passing a gate (null treated as 0.0 which could be the default-zero-passing threshold in some comparison implementations) would be a correctness failure.
- **Consequences:** Nova and Rex must explicitly handle `null` in gate logic — not compare `null >= threshold` naively. The distinction also affects UI display: a null topic should not show "0%" progress but rather "not started." Specified with a `"null_topic_passes_gate": false` flag in `knowledge-base/curriculum/gates.md`.

### Minimum 3 questions per session for a valid score update
- **Date:** 2026-05-11
- **Commit:** 22
- **Decided by:** Lara
- **Decision:** An assessment session with fewer than 3 questions produces no topic score update — the topic score is unchanged. Sessions with ≥ 3 questions update normally.
- **Reason:** A single lucky correct answer (score: 1.0) or unlucky wrong answer (score: 0.0) from a 1-question session would produce misleadingly extreme scores with high variance. Three questions is the minimum to produce a session score with meaningful granularity: scores of 0.0, 0.33, 0.67, or 1.0 all represent distinguishable competency levels.
- **Consequences:** Nova's assessment node must track question count per session and skip the score update if count < 3. This prevents a brief off-topic mention of a slug from inappropriately anchoring that topic's score. Specified in `knowledge-base/curriculum/gates.md`.

## Profile Scoring Rewrite (C25)

### Phase gate checks are cumulative in `get_mastery_level` (Commit 25)
- **Date:** 2026-05-12
- **Commit:** 25
- **Decided by:** Rex (original implementation); Claude (gate fix during orchestration)
- **Decision:** `get_mastery_level()` pre-computes three booleans — `p1 = _phase_1_passed(...)`, `p2 = _phase_2_passed(...)`, `p3 = _phase_3_passed(...)` — then checks them cumulatively: `expert` requires `p1 and p2 and p3`; `advanced` requires `p1 and p2`; `intermediate` requires `p1`. The alternative of checking only `p3` for `expert` was rejected.
- **Reason:** Independent gate checks create a corrupt-DB false-positive path: if `topic_scores` were partially corrupted such that Phase 3 topics had high scores but Phase 1/2 topics were null, a p3-only check would incorrectly award `expert`. The cumulative invariant is the only way to guarantee that every rung of the learning ladder was cleared before awarding a higher level. The pre-computed booleans also allow the function to be read in one pass without re-running gate logic for each level.
- **Consequences:** Any caller that needs to know a user's mastery level must call `get_mastery_level()` — never derive a level from a single phase's gate state. New phases added in the future must be inserted into the cumulative chain, not checked independently. The invariant is encoded in the implementation: the function cannot return `expert` without also having confirmed p1 and p2.

### `session_history` persisted in `user_profiles` table (Commit 25)
- **Date:** 2026-05-12
- **Commit:** 25
- **Decided by:** Rex
- **Decision:** Per-topic session score history (`session_history: dict[str, list[float]]`) is stored as a JSON column directly in the `user_profiles` table row — not in a separate `session_events` table. Each entry in a topic's list is the session score from one completed assessment session.
- **Alternatives considered:** A separate `session_events` table with one row per assessment session, joining to `user_profiles` at scoring time.
- **Reason:** The spaced-repetition formula requires only `best_prior_session_score = max(session_history[slug])`. A join-and-aggregate query for every scoring call adds latency and schema complexity for data the model never reads past a single `max()`. Storing the flat list in the profile row keeps scoring O(1) for the common case and co-locates the data a single profile read already fetches.
- **Consequences:** Session history grows unboundedly in the JSON column. For prolific users with many assessment sessions per topic, this column can become large. A cap (keep last N sessions per topic) can be added without schema migration when telemetry warrants it. Cross-topic analysis (e.g., "which topic has the most assessment sessions") is not suited to this schema and would require reading all profiles.

### MCQ loader extracted to `mcq_utils.py` to avoid route→agent circular import (Commit 36)
- **Date:** 2026-05-20
- **Commit:** 36
- **Decided by:** Nova (upfront, before writing any code)
- **Decision:** `_load_mcq_question` was defined in `agents/nodes/assess.py`. When `app/api/routes/onboarding.py` needed the same function, importing it from `assess.py` would create a cross-layer dependency (route layer → agent node). Extracted to `src/agents/mcq_utils.py` — a shared utility module with zero agent state or LLM imports. `assess.py` imports via `from agents.mcq_utils import load_mcq_question as _load_mcq_question`, preserving all existing internal callers and test patch targets at `agents.nodes.assess._load_mcq_question`.
- **Alternatives considered:** Inlining the function directly in `onboarding.py` (code duplication — same file-parsing regex in two places, drift risk); importing from `assess.py` directly (circular import risk if agent layer ever imports from route layer).
- **Consequences:** Any future module needing MCQ file access imports from `agents.mcq_utils`. The function is now public (`load_mcq_question`, no leading underscore) since it's a shared utility. Test patch targets that reference `agents.nodes.assess._load_mcq_question` remain valid because the alias is still in scope in `assess.py`'s namespace.

### Onboarding answers re-verified from source files on every `/complete` call (Commit 36)
- **Date:** 2026-05-20
- **Commit:** 36
- **Decided by:** Nova
- **Decision:** Correct answers are not cached server-side between the `/diagnostic` and `/complete` requests. Every call to `/complete` re-reads the MCQ markdown files and re-extracts correct answers at scoring time.
- **Alternatives considered:** Session-level caching via `app.storage.user` (NiceGUI session storage); in-memory dict keyed by `user_id + slug`.
- **Reason:** The MCQ files are static markdown on disk (~KB each). The re-read cost is negligible (3 files, 3 regex parses) and eliminates: (a) session state management complexity, (b) the stale-cache attack surface (a user modifying session state between requests cannot change what the server considers correct), and (c) NiceGUI storage coupling in a pure FastAPI route. Freshness is free.
- **Consequences:** If MCQ files change between a user's `/diagnostic` and `/complete` calls, they are scored against the new questions' correct answers. This is acceptable — MCQ files are static in production and change only via deployment. No user-visible inconsistency in practice.

### Deterministic level-order comparison for gate crossing detection (Commit 43)
- **Date:** 2026-05-21
- **Commit:** 43
- **Decided by:** Nova
- **Decision:** Gate crossing detection in `update_profile_node` uses a module-level `_LEVEL_ORDER: dict[str, int]` (maps level names to integers 0–4) and `_GATE_THRESHOLDS: dict[str, int]` (maps phase names to their minimum new rank). No LLM involved — pure integer comparison.
- **Alternatives considered:** Using the `get_mastery_level()` function recursively on the old scores to derive old level; LLM-assisted "did the user advance?" inference.
- **Reason:** Gate crossing is a structural invariant — it can be fully expressed as `old_rank < threshold <= new_rank`. LLM inference would add hallucination risk, latency, and cost for a Boolean determination. The level ordering is fixed by the curriculum spec (novice → beginner → intermediate → advanced → expert); mapping to integers makes the comparison transparent and testable.
- **Consequences:** `_LEVEL_ORDER` and `_GATE_THRESHOLDS` are the authoritative constants for gate detection logic. Any future level added to the curriculum must be inserted in the correct ordinal position. The `break` after the first matching gate means a multi-level jump in one session (e.g., novice → expert) emits only the lowest crossed gate — accepted edge-case behavior since scoring is incremental and such jumps are unrealistic in practice.

### `generate_node` as the clearing node for `gate_just_passed` (Commit 43)
- **Date:** 2026-05-21
- **Commit:** 43
- **Decided by:** Nova + Claude (gate review)
- **Decision:** `generate_node` always returns `{"gate_just_passed": None}` — unconditionally. When a gate was crossed, it prepends the announcement; when no gate was crossed, it still writes `None` to clear any stale value. Clearing is not delegated to a separate cleanup node.
- **Alternatives considered:** A dedicated `clear_gate_state_node` at the end of the graph; `update_profile_node` returning `{"gate_just_passed": None}` on the no-crossing path.
- **Reason:** `generate_node` is the only node that reads `gate_just_passed`. Since it reads AND clears in one step, a separate cleanup node would either (a) require an extra graph edge or (b) force LangGraph to schedule two nodes where one suffices. `generate_node` always runs after `update_profile_node` in the normal graph path — it is the natural clearing point. (Viktor Advisory C43: `update_profile_node` should also return `{"gate_just_passed": None}` unconditionally for defensive consistency — deferred to Commit 43.5.)
- **Consequences:** If `generate_node` fails to run in a turn (graph error, circuit breaker), `gate_just_passed` retains its value until the next successful turn. The next successful `generate_node` will then announce the gate — potentially one turn late. This is acceptable for the portfolio context; addressed defensively in Commit 43.5.

### Idempotent migration via per-row sentinel key check (Commit 25)
- **Date:** 2026-05-12
- **Commit:** 25
- **Decided by:** Rex
- **Decision:** `migrate_topic_slugs()` checks each row's existing `topic_scores` JSON for the presence of the `rag_pipeline_architecture` key before migrating that row. If the key is present, the row is skipped. The function is called in the FastAPI lifespan at every startup, after `init_profile_db()`.
- **Alternatives considered:** A global `schema_version` table; a `migrated: bool` column on `user_profiles`.
- **Reason:** A global migration flag requires schema changes before the migration can run — a bootstrapping problem on fresh installs. A `migrated` column would require an ALTER TABLE. The per-row sentinel is self-contained: the presence of `rag_pipeline_architecture` in the existing `topic_scores` JSON proves the row was migrated under the new 8-slug curriculum; its absence proves it has old 6-slug data. No additional column, no separate table, no ALTER TABLE.
- **Consequences:** The sentinel key (`rag_pipeline_architecture`) must never be renamed or removed without updating the migration check. If a future migration requires a different sentinel, a new check function should be written — not the existing one patched. The function is crash-safe: rows migrated before a crash are skipped on resume because the sentinel was already written; in-progress rows are re-migrated (idempotent from-scratch).

## UI Foundation (C26)

### Font injection per `@ui.page` (Commit 26)
- **Date:** 2026-05-17
- **Commit:** 26
- **Decided by:** Aria
- **Decision:** Google Inter font is injected via `ui.add_head_html()` independently in each of the three `@ui.page` functions (`login_page`, `register_page`, `index`). Font links cannot be shared via a single injection point.
- **Reason:** NiceGUI initializes a fresh HTML document for every `@ui.page` route. A `ui.add_head_html()` call in `index()` is scoped to the `/` document only — it has no effect on `/login` or `/register`. Each page function must independently inject its `<link>` tags.
- **Consequences:** Three identical font injection blocks exist (DRY debt). A module-level `_FONT_LINK_HTML` constant would eliminate drift risk if the font URL or weight set changes. Accepted as advisory; the current approach is functionally correct and readable.

### `!important` on Quasar button gradient (Commit 26)
- **Date:** 2026-05-17
- **Commit:** 26
- **Decided by:** Aria
- **Decision:** The CTA button gradient overrides use `background:linear-gradient(...) !important` via NiceGUI's `.style()` method.
- **Reason:** Quasar's button component applies its own `background` inline style via a Vue component after render, overriding NiceGUI's `.style()` string. The `!important` flag is the only reliable override without modifying a shared CSS class in the `<style>` block.
- **Alternatives considered:** Adding a `.q-btn.gradient-cta { background: ... }` rule in the `<style>` block with sufficient specificity. This is the cleaner long-term approach but requires adding a class name to the button element.
- **Consequences:** Any future layered style on these buttons will require `!important` chaining or a refactor to the class-based approach. Noted as tech debt for the next style pass.

### Google Fonts CDN accepted for portfolio app (Commit 26)
- **Date:** 2026-05-17
- **Commit:** 26
- **Decided by:** Team Lead (implicit — no self-hosting requirement stated)
- **Decision:** Inter is loaded from `fonts.googleapis.com` / `fonts.gstatic.com` CDN, not self-hosted.
- **Reason:** Simpler setup for a portfolio project. Self-hosting requires bundling font files and configuring static file serving.
- **Privacy trade-off:** Google receives user IP and browser fingerprint on every page load (CWE-829, flagged by Sage). Accepted for a non-production portfolio app.
- **Consequences:** If this project is used with real users (beyond portfolio), self-host Inter via `@fontsource/inter` and remove the Google Fonts CDN link. No other code change required — same font rendering.

## UI Landing Page (C30)

### NiceGUI container override for full-bleed pages (Commit 30)
- **Date:** 2026-05-19
- **Commit:** 30
- **Decided by:** Aria + Claude (diagnosed during visual review)
- **Decision:** A `@ui.page()` function using only `ui.html()` (no NiceGUI layout primitives like `ui.header()`, `ui.footer()`) must explicitly override `.nicegui-content`, `.q-page`, and `.q-page-container` to achieve full-viewport-width layout.
- **Reason:** NiceGUI wraps all page content in a `.nicegui-content` div that defaults to `display: flex; align-items: center` — this centers child elements horizontally. Without the override, the landing page's `width: 100%` wrapper resolves to the flex parent's alignment width, not the viewport. The fix applies `display: block !important; max-width: 100% !important; align-items: unset !important` via both a `<style>` rule and a `ui.query()` call (belt-and-suspenders for Quasar's load-order variability).
- **Alternatives considered:** Using NiceGUI layout primitives (`ui.page_sticky`, `ui.element`) — rejected because they add Quasar wrapper markup that interferes with custom full-bleed sections.
- **Consequences:** Any future full-bleed `@ui.page()` using `ui.html()` must include the same container override block. The override is scoped to the page that injects it (CSS injects on page load, full reload clears it on navigation to other pages — no cross-page contamination).

### `def` not `async def` for static pages (Commit 30)
- **Date:** 2026-05-19
- **Commit:** 30
- **Decided by:** Aria
- **Decision:** `landing_page()` is a synchronous `def`, not `async def`.
- **Reason:** The landing page makes no `await`-able calls (no API, no storage reads, no auth checks). Using `async def` would be cargo-cult — NiceGUI supports both, but only async functions gain anything from the `async` keyword. Synchronous page functions are simpler and avoid accidental `await` calls being added in future edits.
- **Consequences:** If `/landing` ever needs an API call or storage read, it must be upgraded to `async def`. This is a one-word change with no other side effects.

---

## MCQ Question Banks (C33)

### MCQ as phase-gate advancement instrument, not in-session learning (Commit 33)
- **Date:** 2026-05-19
- **Commit:** 33
- **Decided by:** Lara + Claude (replan decision 2026-05-19)
- **Decision:** MCQ (multiple-choice) questions are used exclusively for phase-gate advancement tests. Open-ended questions remain the primary in-session learning and assessment instrument.
- **Reason:** Phase-gate advancement requires a deterministic, reliable signal — one that does not depend on LLM evaluator accuracy or rubric interpretation. MCQ answer-key comparison is exact: no LLM call, no partial credit ambiguity, no evaluator variance. Open-ended questions are better for learning (they require recall and synthesis) but their rubric-based scoring adds noise at gate decision points.
- **Alternatives considered:** Using open-ended questions for both learning and gates — rejected because LLM evaluator variance could cause a learner to pass or fail a gate based on evaluator inconsistency rather than actual mastery.
- **Consequences:** Two question types coexist in the curriculum. The open-ended scorer will eventually be validated; at that point, MCQ can be supplemented or replaced at gate transitions. Until then, MCQ is the only advancement format.

### Separate `questions/mcq/[slug].md` file tree (Commit 33)
- **Date:** 2026-05-19
- **Commit:** 33
- **Decided by:** Lara
- **Decision:** MCQ files live in `knowledge-base/curriculum/questions/mcq/[slug].md` — a parallel subdirectory to the existing `questions/[slug].md` open-ended banks.
- **Reason:** Keeping MCQ and open-ended questions in separate files prevents format drift (one file, two incompatible formats) and makes the distinction explicit for Nova's Commit 35 (mcq-assessment-engine), which reads only `questions/mcq/`. A mixed file would require parsing to distinguish question types.
- **Consequences:** Nova's assessment engine (Commit 35) imports from `questions/mcq/` exclusively. Onboarding (Commit 36) reads from `questions/mcq/` as a read-only diagnostic source.

### 5 MCQ questions per topic with 2/2/1 difficulty distribution (Commit 33)
- **Date:** 2026-05-19
- **Commit:** 33
- **Decided by:** Lara
- **Decision:** Each topic has exactly 5 MCQ questions: 2 beginner, 2 intermediate, 1 advanced.
- **Reason:** 5 questions satisfies the `min_questions_per_session=3` gate from `gates.md` while keeping advancement tests concise. The 2/2/1 distribution ensures the gate tests foundational knowledge (2 beginner) and practitioner-level application (2 intermediate) before advanced synthesis (1 advanced). A purely uniform distribution (1/1/1/1/1) would underweight the core knowledge the gates are designed to verify.
- **Consequences:** If future data shows 5 questions is insufficient for discriminating mastery, the bank can grow to 8–10. The schema and engine support any bank size — only the minimum 3 is enforced at runtime.

## MCQ Assessment Engine (C35)

### Regex extraction for freeform MCQ answer input (Commit 35)
- **Date:** 2026-05-20
- **Commit:** 35
- **Decided by:** Nova
- **Decision:** `_evaluate_mcq_answer` uses `re.search(r'\b([A-Da-d])\b', user_message.strip())` to extract the user's answer letter from freeform text, rather than requiring an exact single-character match.
- **Reason:** Users naturally write "B", "b", "Option B", or "I think B is correct." Requiring an exact single-character input would fail silently for any of these natural variations. The word-boundary `\b` prevents matching letters embedded in words (e.g. "above" matches 'a' at character level but not at word boundary). Case-insensitive comparison handles "b" vs "B".
- **Alternatives considered:** Strict single-character parse (`user_message.strip().upper()` if length == 1) — rejected because it silently scores 0.0 for users who write natural sentences; requires UX instruction that adds friction.
- **Consequences:** First standalone A–D letter in the message wins. If a user writes "Not A, I think B", the evaluator selects 'A' (first match). This is an accepted edge case — the UI instructions (Commit 37) will guide users to answer with a single letter or option phrase.

### `is_mcq` flag propagated to ChatResponse for rendering branch (Commit 35)
- **Date:** 2026-05-20
- **Commit:** 35
- **Decided by:** Nova + Claude
- **Decision:** `AgentState.is_mcq` is extracted into `ChatResponse.is_mcq` and included in the SSE `done` event. Aria reads this flag in Commit 37 to decide whether to render A–D option buttons or a plain text input.
- **Reason:** The frontend cannot parse `test_question` text to determine whether to render MCQ buttons — it needs a typed signal from the backend. Putting the flag in `ChatResponse` keeps the rendering decision out of the UI layer and makes the API contract explicit.
- **Alternatives considered:** Aria parses the `test_question` text for A/B/C/D options — rejected because parsing free text in the frontend is fragile; a dedicated boolean flag is the correct typed contract for a rendering decision.
- **Consequences:** Aria (Commit 37) uses `done_data["is_mcq"]` as the branch condition. This field must remain in `ChatResponse` as long as MCQ is the assessment format.

### Mutable single-element list for closure mutation in NiceGUI (Commit 37)
- **Date:** 2026-05-20
- **Commit:** 37
- **Decided by:** Aria
- **Decision:** MCQ state uses mutable single-element lists (`_mcq_active = [False]`, `_mcq_opts: list[str]`) rather than `nonlocal` declarations.
- **Reason:** `nonlocal` requires the variable to be declared at the correct enclosing function scope, but NiceGUI's nested `with ui.column():` context manager structure makes scope boundaries ambiguous. Mutable lists allow mutation from nested closures (click handlers, `submit_mcq_option`) without needing to trace the exact enclosing scope.
- **Alternatives considered:** `nonlocal _mcq_active` — fragile when callback handlers are defined after context managers close; `app.storage.user` dict — adds I/O overhead for ephemeral single-session state that doesn't need persistence.
- **Consequences:** `_mcq_active[0]` is always accessed via index. Future code in this closure scope must continue using list indexing for consistency.

### `ob_step_content` is sync `@ui.refreshable`, not async (Commit 38)
- **Date:** 2026-05-20
- **Commit:** 38
- **Decided by:** Aria
- **Decision:** The onboarding wizard's step renderer (`ob_step_content`) is a synchronous `@ui.refreshable def`, not `async def`. Async API calls live in separate handler functions (`_ob_select_level`, `_ob_select_answer`, `_ob_skip`) that mutate mutable-list state then call `ob_step_content.refresh()`.
- **Reason:** NiceGUI refreshable renders UI elements synchronously — `with` context blocks execute synchronously. Wrapping the step renderer as async conflates rendering and I/O without benefit. Separating concerns follows the established `profile_panel` pattern (C19).
- **Alternatives considered:** Async `ob_step_content` — rejected; conflates rendering and I/O. The fetch-mutate-refresh pattern is already established project convention.
- **Consequences:** All async work in the onboarding flow must go through handler functions. Any future step requiring data fetching must follow: fetch in handler → mutate state → call `.refresh()`.

### Phase lookup dicts at module level (Commit 38)
- **Date:** 2026-05-20
- **Commit:** 38
- **Decided by:** Aria + Claude
- **Decision:** `_PHASE_LABELS`, `_PHASE_TOPICS`, and `_ADVANCE_MSG` are defined at module level, not inside `profile_panel()` or `index()`.
- **Reason:** `profile_panel()` is `@ui.refreshable` and fires after every chat turn. Building static dicts on every refresh wastes cycles. Module-level placement is the correct scope for static lookup tables with no dependency on page state.
- **Alternatives considered:** Defining inside `index()` as closures — rejected because they don't reference page-scoped state; module scope is correct and makes them importable and testable without page load.
- **Consequences:** Changes to phase progression model (new phases, topics, thresholds) require updating three module-level dicts in `src/app/ui.py`.

### `ui.element("div")` required for precise flex/grid control in NiceGUI (Commit 38.5)
- **Date:** 2026-05-20
- **Commit:** 38.5
- **Decided by:** Aria + Claude (discovered during implementation)
- **Decision:** All layout-critical wrappers in `profile_panel()` use `ui.element("div")` with inline `display:flex` styles rather than `ui.row()` or `ui.column()`.
- **Reason:** `ui.row()` and `ui.column()` render as Quasar `q-row`/`q-col` components which inject gap and padding classes. These override inner element `flex:1` and `width:100%` styles, preventing progress bars and labels from stretching to full width. `ui.element("div")` renders a plain `<div>` with no Quasar interference.
- **Alternatives considered:** Overriding Quasar gap/padding via `!important` — rejected because it requires per-element overrides and doesn't address `flex:1` breakage; using `ui.row().classes("no-wrap q-pa-none q-ma-none")` — rejected; still adds Quasar `display:flex` with flex-specific defaults that differ from a clean div.
- **Consequences:** Any future layout-sensitive section in `profile_panel()` or equivalent refreshable panels must use `ui.element("div")` as the wrapper. `ui.row()` and `ui.column()` remain appropriate for non-layout-critical groupings only.

### SVG gradient defs injected once in `index()` head (Commit 38.5)
- **Date:** 2026-05-20
- **Commit:** 38.5
- **Decided by:** Aria + Claude
- **Decision:** A hidden SVG block with `<linearGradient id="tg">` is injected into the page `<head>` once via `ui.add_head_html()` in `index()`. Topic row checkmark icons reference it as `fill="url(#tg)"`.
- **Reason:** `profile_panel()` is `@ui.refreshable` and fires after each chat turn, potentially creating hundreds of SVG icon elements. Defining the gradient inline in each icon would duplicate the `<defs>` block on every render. Injecting once in `index()` ensures a single definition reused by all icon instances.
- **Alternatives considered:** Inline `<defs>` per SVG icon — rejected; duplicates gradient on every refresh. CSS `background: linear-gradient` on the icon container — rejected; SVG `fill` cannot reference a CSS gradient; only an SVG `<linearGradient>` referenced by `id` works for SVG path fills.
- **Consequences:** The gradient `id="tg"` is a page-scoped constant. Any future SVG element needing the same gradient can reference `fill="url(#tg)"` without defining a new defs block.

### CSS `::after` pseudo-element for tab underline via injected stylesheet (Commit 38.5)
- **Date:** 2026-05-20
- **Commit:** 38.5
- **Decided by:** Aria + Claude
- **Decision:** The `.sb-tab.active::after` gradient underline is defined in a `<style>` block injected via `ui.add_head_html()` in `index()`, not via NiceGUI's `.style()` method.
- **Reason:** NiceGUI's `.style()` method sets inline CSS on the element itself (`style="..."`). Inline styles cannot define pseudo-elements (`::after`, `::before`). CSS pseudo-elements require class-based rules in a stylesheet context.
- **Alternatives considered:** NiceGUI `.style()` with `::after` — not valid; inline styles don't support pseudo-selectors. Per-element JS injection — overly complex for a simple CSS rule.
- **Consequences:** All pseudo-element styles for sidebar tab indicators must live in the injected `<style>` block inside `index()`. Changes to the tab underline require updating the `ui.add_head_html()` call, not individual element styles.

### `session_question_count: int | None = None` sentinel default in `compute_topic_scores` (Commit 39)
- **Date:** 2026-05-20
- **Commit:** 39
- **Decided by:** Claude
- **Decision:** The new `session_question_count` parameter defaults to `None` rather than `1`. The minimum-session guard (`< 3`) activates only when the caller explicitly passes a count. Existing callers that predate Commit 41 pass nothing and bypass the guard entirely.
- **Alternatives considered:** Default of `1` — rejected. With default `1`, `1 < 3` triggers the early return for all existing callers that omit the parameter, causing zero score updates across the system until Commit 41 wires the real counter. A sentinel of `None` means "guard not yet wired" — Commit 41 will pass the real count.
- **Consequences:** Until Commit 41 wires the session counter from `AgentState`, the minimum-session guard is latent. The default `None` acts as an explicit "not yet wired" marker visible in the signature.

### Passive signals excluded from session_history (Commit 39)
- **Date:** 2026-05-20
- **Commit:** 39
- **Decided by:** Claude
- **Decision:** When `is_passive=True`, `compute_topic_scores` does NOT append `current_session` to `session_history`. Session history is updated only on the active MCQ path.
- **Reason:** `session_history` feeds `best_prior_session_score` in the spaced-repetition formula for future MCQ sessions. A passive delta of 0.2 (from inferred query analysis) would lower the `best_prior` if included, causing a future MCQ score of 0.8 to produce `0.7 × 0.8 + 0.3 × 0.2 = 0.62` instead of the correct first-session result of `0.8`. Passive signals are a weak inference signal; contaminating history with them degrades MCQ scoring accuracy over time.
- **Alternatives considered:** Appending with a lower weight — rejected as complex. A separate `passive_history` dict — rejected as premature abstraction.
- **Consequences:** `session_history` contains only MCQ session scores. Passive signals update `topic_score` directly but leave no trace in history. The spaced-rep formula for future MCQ sessions uses only formal assessment scores as `best_prior`.

### Phase 1 gap remediation scoped to `intermediate` users only (Commit 41)
- **Date:** 2026-05-20
- **Commit:** 41
- **Decided by:** Claude
- **Decision:** `_select_test_slug` in `assess_node` grants Phase 1 gap remediation only when `user_level == "intermediate"`. No other mastery level gets the remediation bypass.
- **Reason:** `intermediate` users have passed Phase 1 once (gate state), but the LLM evaluator may have identified residual Phase 1 gaps in their answers. These users are in Phase 2 territory by score but may have conceptual holes from Phase 1 — the right fix is a targeted Phase 1 question. `beginner` and `novice` users already have Phase 1 as their eligible phase and receive Phase 1 questions normally. `advanced` and `expert` users have passed Phase 1 with high scores; a Phase 1 gap identified by the LLM evaluator at this level is likely a false positive from phrasing, not a genuine knowledge gap — routing them back to Phase 1 would be patronizing and incorrect.
- **Consequences:** Advanced/expert users with apparent Phase 1 gaps are not routed back — they receive questions in their eligible phase (Phase 2/3). If future data shows genuine Phase 1 regression at advanced levels, the guard can be extended.

### `session_question_counts` as an AgentState field (not passed in graph config) (Commit 41)
- **Date:** 2026-05-20
- **Commit:** 41
- **Decided by:** Claude
- **Decision:** The per-topic MCQ answer count is tracked in `AgentState.session_question_counts: dict[str, int]` — emitted by `assess_node` on each evaluation turn and checkpointed by `MemorySaver` across turns within a session.
- **Alternatives considered:** Tracking question count in the graph config; using a separate Redis counter keyed by session_id + slug; passing the count via a separate API field in the chat request body.
- **Reason:** `AgentState` is the single source of truth for per-turn agent data. LangGraph's `MemorySaver` checkpointer automatically persists the field across turns for the same `thread_id`. A Redis counter or API field would require additional infrastructure and coupling. The graph config (`{"configurable": {...}}`) is for router/checkpointer metadata, not mutable agent state.
- **Consequences:** `session_question_counts` is not initialized in `chat.py`'s `initial_state` — the first turn starts with no key, and `assess_node` reads it with `.get("session_question_counts") or {}`. The field accumulates in the MemorySaver checkpoint and resets when a new session (new `thread_id`) begins.

### Proximity hint reads DB in `generate_node`, not carried through `AgentState` (Commit 41)
- **Date:** 2026-05-20
- **Commit:** 41
- **Decided by:** Claude
- **Decision:** `generate_node` reads the user's profile from the DB via `asyncio.to_thread(get_profile_by_user_id, user_id)` to build the proximity hint, rather than adding `topic_scores` to `AgentState` and propagating it through the graph.
- **Reason:** `topic_scores_delta` in `AgentState` is the per-turn delta (sparse float dict), not the absolute stored scores. The proximity hint requires absolute stored scores (e.g., "current score is 0.65") to compute which topics are in the [0.60, 0.70) window. Adding absolute scores to `AgentState` would duplicate the DB state and require a separate DB read node before `generate_node`. A targeted read inside `generate_node` is the minimal-coupling approach — one additional sync call wrapped in `asyncio.to_thread`, consistent with the project-wide blocking I/O pattern.
- **Consequences:** `generate_node` now has a DB dependency (was previously pure agent-state). No new AgentState fields required. If the DB lookup fails or returns `None`, the hint is silently skipped — generation proceeds normally.

---

## Agent Team Design (C42)

### RAG Specialist — Lara interface contract (Commit 42)
- **Date:** 2026-05-20
- **Commit:** 42
- **Decided by:** Claude
- **Decision:** The RAG Specialist owns question depth (`knowledge-base/curriculum/questions/`) within Lara's structure; Lara owns the format definition. The Specialist writes to Lara's slug file format but never modifies the format itself or any Lara-owned structure files.
- **Alternatives considered:** Merging the Specialist's role into Lara's domain; giving the Specialist full ownership of all of `knowledge-base/curriculum/`.
- **Reason:** Lara's ceiling is pedagogically sound but surface-level — she can write "explain cosine similarity" but not "your production system shows faithfulness=0.6, diagnose the three most likely failure modes." The Specialist fills that gap without fragmenting the curriculum structure. Splitting ownership of the slug schema would create format drift: two agents with diverging format assumptions. Single-owner format (Lara) with a writer role (Specialist) is the minimal coupling design.
- **Consequences:** The Specialist may never add topics, move topics between phases, or modify curriculum-map.md, gates.md, or topic-slugs.json. Format changes must go through Lara. If the Specialist identifies a curriculum gap, it is a handoff to Lara — not a self-assigned task.

*Last updated: 2026-05-21 — Commit 44 complete (phase-unlock-ui)*

---

## Phase Unlock UI (C44)

### UI-layer gate crossing detection via `_prev_mastery` mutable list (Commit 44)
- **Date:** 2026-05-21
- **Commit:** 44
- **Decided by:** Aria
- **Decision:** Detect mastery advancement in the UI layer by comparing the incoming `mastery_level` to the previous render's value stored in `_prev_mastery = [None]` (mutable list closure), rather than exposing a `gate_just_passed` field from the profile API.
- **Alternatives considered:** Adding `gate_just_passed` to the `/api/profile/me` response; reading it from a separate endpoint; driving the animation from a WebSocket push.
- **Reason:** `gate_just_passed` is an `AgentState` field that is cleared by `generate_node` after it produces the in-chat announcement. By the time `profile_panel.refresh()` runs (triggered by the SSE done event), the field has already been consumed and set to `None`. The profile API (`/api/profile/me`) returns the user's stored profile only — it does not carry AgentState fields. The closure variable approach is zero-cost: it reuses the same mutable-list idiom already present in three places in `index()` (`_tab_state`, `_ob_step`, `_mcq_active`). Consistent pattern, no new API surface.
- **Consequences:** The animation fires whenever `mastery_level` changes between two consecutive `profile_panel.refresh()` calls. If the page is reloaded mid-session after a gate crossing, the animation will not re-fire (the previous level is lost). This is the correct behavior — the celebration is a real-time moment, not a persistent state.

### `_prev_mastery[0] is not None` guard (Commit 44)
- **Date:** 2026-05-21
- **Commit:** 44
- **Decided by:** Aria
- **Decision:** Gate the `_gate_crossed` check on `_prev_mastery[0] is not None` so the animation does not fire on the first panel load.
- **Reason:** On first invocation, `_prev_mastery[0]` is `None`. Without the guard, `mastery != None` would always be `True` on first load, triggering the unlock animation for every user on every page load. The `is not None` check ensures at least one baseline mastery value has been recorded before a "change" can be detected.

## Interactive UX — Navigation Chips & Formatting (2026-05-21)

### Semantic similarity for navigation-intent detection
- **Date:** 2026-05-21
- **Decided by:** Team Lead + Claude
- **Decision:** Reuse the existing `all-MiniLM-L6-v2` embedder (originally used only for document retrieval) to classify whether an incoming user question is a navigation-intent question ("where do I start?", "I'm not sure where to begin", etc.). Pre-embed 14 representative anchor phrases once at first call (`lru_cache`), then compute max cosine similarity against them for each question. Threshold: 0.52.
- **Alternatives considered:** Keyword matching against a hardcoded phrase list.
- **Why not keywords:** Keyword matching only catches exact or near-exact phrases. "I'm not sure where to begin" shares zero keywords with "what should I learn?" but is semantically identical. A user would have to phrase their question in a way we predicted at write-time to get chips.
- **Why this embedder:** `normalize_embeddings=True` means cosine similarity equals dot product — no division, no extra dependencies. The model is already loaded and warm from document retrieval. Zero marginal startup cost.
- **Consequences:** Any semantically equivalent navigation question triggers chips regardless of phrasing. Threshold is tunable. Anchor phrase set is extensible. First call computes 14 embeddings (one-time ~50ms); all subsequent calls hit the cache.

### Navigation chips scoped to known navigation responses only
- **Date:** 2026-05-21
- **Decided by:** Team Lead (confirmed with Mira)
- **Decision:** Chips are only shown for navigation-intent queries. All other responses (topic explanations, knowledge checks, comparisons) remain as plain markdown text.
- **Reason:** Different list types carry different semantics. A numbered list explaining "3 reasons RAG beats fine-tuning" should not be converted to chips — the items form an argument, not a menu. Generalizing chip rendering to all lists would fragment meaning. The nav query is the one case where a list is genuinely a navigation target.

### Level-filtered chips by mastery_level
- **Date:** 2026-05-21
- **Decided by:** Team Lead (confirmed with Mira)
- **Decision:** Chip list is sliced by phase: novice/beginner see 2 chips (Foundation), intermediate sees 6 (Foundation + Core RAG), advanced/expert sees all 8. Slice happens server-side in the chat route where `user_level` is already in scope.
- **Reason:** Showing a novice all 8 topics including Production Patterns lets them skip the curriculum sequence, which defeats the adaptive learning design. Chips are a navigation accelerator, not a full topic browser — the Knowledge Profile sidebar already shows the full curriculum structure.
- **Consequences:** Users can still ask any question at any level. Only the suggested navigation chips are filtered. A "You'll unlock more topics as you progress." line is shown when fewer than 8 chips are displayed.

### MCQ options moved inline into the chat bubble
- **Date:** 2026-05-21
- **Decided by:** Team Lead
- **Decision:** Remove the pre-built MCQ option panel from the fixed bottom composer area. Create MCQ option rows dynamically inside `response_inner_col` immediately after the knowledge check card, using the same visual style.
- **Alternatives considered:** Keep options at the bottom (original design).
- **Why changed:** Bottom-panel MCQ created a spatial disconnect — the question was in the chat bubble, the answers were floating 400px lower at the screen edge. Users were confused about which question the options belonged to. Inline placement makes the Q+A unit visually coherent.
- **Consequences:** The pre-built `mcq_panel`, `mcq_btns`, `_mcq_active`, and `_mcq_opts` constructs are removed. Options are created on-demand when a MCQ done event arrives. Full option text (not just the letter) is sent as the user message so the conversation history is readable. NiceGUI slot-context is preserved by using direct `async def` handlers instead of `asyncio.ensure_future`.

---

## Question Type Balance (C45.3)

### `select_question_type` as a standalone pure function

- **Date:** 2026-05-22
- **Decided by:** Nova
- **Decision:** Level-based question type selection lives in its own `select_question_type(user_level: str) -> str` function rather than inlined in `select_test_question`.
- **Alternatives considered:** Inline `_OPEN_PROB.get() + random.random()` directly in `select_test_question`.
- **Reason:** A standalone function is independently testable — ratio distribution can be validated with 1000 draws without running the full passive assessment and slug selection pipeline. The caller reads `if question_type == "open"` which matches spec language; inline logic would obscure the decision point. `_OPEN_PROB` constants also stay scoped to `question_selection.py` rather than bleeding into `test_delivery.py`.
- **Consequences:** Ratio constants are co-located with slug selection logic in one file. Future level additions require only a dict entry in `question_selection.py`.

### Explicit 0.0 fast-path for novice/beginner (no random call)

- **Date:** 2026-05-22
- **Decided by:** Nova
- **Decision:** When `_OPEN_PROB` yields 0.0, return `"mcq"` immediately without calling `random.random()`.
- **Alternatives considered:** Single code path: `return "open" if random.random() < prob else "mcq"` for all levels.
- **Reason:** `random.random() < 0.0` always evaluates to False and produces correct behavior. But calling `random` for a deterministic outcome is semantically wrong and could mislead future readers into thinking novice/beginner have a non-zero open probability. The explicit guard makes the pedagogical constraint visible in code, not just in the constant value. Unknown/invalid levels also take this fast-path (default 0.0), conservatively receiving MCQs.
- **Consequences:** The probability draw is only invoked for the three genuinely probabilistic levels (intermediate, advanced, expert).

---

## Agent Architecture (2026-05-22)

### LangGraph nodes are thin routers — logic lives in domain modules

- **Date:** 2026-05-22
- **Decided by:** Team Lead
- **Decision:** When a LangGraph node grows past ~50 lines, its logic moves into named domain modules. The node file imports and delegates; it never owns business logic directly.
- **Pattern:** `assessment/node.py` (~25 lines) routes to `evaluation.py` and `test_delivery.py`. Domain concerns (passive inference, slug selection, rubric loading, result shapes) each live in their own module.
- **Reason:** Nodes are control-flow primitives. Mixing routing with domain logic makes both harder to read and test independently. A thin node is also easier to rewire in the graph without touching business logic.
- **Rule of thumb:** If you can't read the full node in one screen, it's holding logic it shouldn't.
- **Consequences:** All future node files must stay thin. When a node accumulates logic, extract to a sibling domain module (`src/agents/assessment/`, `src/agents/generation/`, etc.) before the node grows past ~50 lines.

---

## Question Difficulty Degradation (C45.4)

### Keyword-based difficulty signal detection — no LLM (Commit 45.4)
- **Date:** 2026-05-23
- **Commit:** 45.4
- **Decided by:** Nova (spec) + Claude (validation)
- **Decision:** `_is_difficulty_signal(message: str) -> bool` uses simple substring matching against a conservative `_DIFFICULTY_PHRASES` tuple. No LLM call involved.
- **Alternatives considered:** LLM-based intent classification ("does this message signal difficulty?"); semantic similarity against anchor phrases.
- **Reason:** Difficulty detection is a routing decision — it determines which code path fires, not what content to generate. Routing decisions that can be handled deterministically should never use an LLM. A keyword list is transparent, testable with one-line assertions, and has zero latency. False negatives (user signals difficulty but keywords don't match) are safer than false positives (a real answer incorrectly triggers simplification). The conservative phrase list covers all natural formulations without over-matching.
- **Consequences:** Users who signal difficulty in unusual phrasings (e.g., non-English, or highly idiomatic expressions not in the list) will have their message evaluated as a normal answer. This is the correct conservative default.

### Step 3 reveals via clearing `pending_test_question` — no new mechanism (Commit 45.4)
- **Date:** 2026-05-23
- **Commit:** 45.4
- **Decided by:** Nova
- **Decision:** When a user signals difficulty a second time (`question_simplified=True`), the system clears `pending_test_question` to `None`, adds the slug to `identified_gaps`, and returns. No new retrieval mechanism is added. `generate_node` already falls back to RAG retrieval when no pending question is present — this behavior is reused verbatim.
- **Alternatives considered:** Introducing a new `reveal_mode` flag; calling `retrieve_node` directly from `evaluate_answer`; adding a new graph edge for the reveal path.
- **Reason:** The system already has a well-tested path where `pending_test_question=None` causes `generate_node` to run the standard RAG pipeline. Reusing this invariant keeps the degradation path free of new infrastructure — no new AgentState fields for the reveal, no additional LangGraph edges. The slug in `identified_gaps` ensures the profile update node records it as a knowledge gap regardless of how the question was resolved.
- **Consequences:** The RAG reveal uses the user's original question text (from `question` in state) as the retrieval query. This is appropriate — the user's question is what they were trying to understand. If the topic has poor knowledge base coverage, the reveal may be less helpful; this is a curriculum quality issue, not a system design issue.

## Mastery Level Simplification (2026-05-23)

### Remove `beginner` level — merge into `novice` (2026-05-23)
- **Date:** 2026-05-23
- **Decided by:** Team Lead
- **Decision:** The `beginner` mastery level is removed. The four remaining levels are `novice`, `intermediate`, `advanced`, `expert`. Users who were `beginner` (Phase 1 in progress) are now `novice` (Phase 1 not yet passed).
- **Alternatives considered:** Keeping both and adding a badge design for `beginner`; renaming `beginner` to something other than `novice`.
- **Reason:** `beginner` and `novice` were semantically identical from a user perspective — both represented Phase 1 in-progress work — and `beginner` had no badge design. Maintaining two levels for the same curriculum phase added complexity with no user-facing payoff: distinct prompt templates, separate dict entries across 10+ files, and a self-report option that was confusing rather than clarifying. `novice` already captured the intent; `beginner` was dead weight.
- **Consequences:** `get_mastery_level()` now returns `novice` for any user who has not passed Phase 1, regardless of whether any Phase 1 topics have been scored. `_LEVEL_ORDER` is renumbered (0–3). `_GATE_THRESHOLDS` adjusted accordingly (phase_1 threshold = 1). The onboarding self-report now offers Novice / Intermediate / Expert. Question difficulty labels in the knowledge base are renamed `novice` (previously `beginner`).

---

## Prompt Quality — Wave H (C45.5 / 2026-05-23)

### Floor-first RESPONSE FORMAT in all 5 prompts (Commit 45.5)
- **Date:** 2026-05-23
- **Commit:** 45.5
- **Decided by:** Nova
- **Decision:** RESPONSE FORMAT block in all 5 prompt templates (`_DEFAULT_SYSTEM`, `_NOVICE_SYSTEM`, `_INTERMEDIATE_SYSTEM`, `_ADVANCED_SYSTEM`, `_EXPERT_SYSTEM`) rewritten from permissive conditional rules ("only if/when/for") to mandatory floor rules: (1) every response must bold the first technical term it introduces; (2) responses longer than 3 sentences must use at least one structural element (bold, list, or heading); (3) single-sentence answers may use plain prose.
- **Alternatives considered:** Keeping conditional rules but making them stronger ("prefer to bold..."); adding examples for each format type.
- **Reason:** LLMs treat "only if" and "when appropriate" as withheld permission, not granted permission — the model interprets permission not taken as a correct choice and defaults to plain prose. A mandatory floor removes the permission question entirely. The single-sentence escape hatch prevents forced structure on trivially short answers while ensuring all multi-sentence responses carry a formatting signal.
- **Consequences:** Advanced and expert users may encounter slightly more structured responses than strictly necessary. Mira flagged this as worth monitoring; plain prose preference in those levels can be restored per-prompt if users report over-formatting.

### Explicit persona declaration in `_NOVICE_SYSTEM` (Commit 45.5)
- **Date:** 2026-05-23
- **Commit:** 45.5
- **Decided by:** Nova
- **Decision:** `_NOVICE_SYSTEM` opening replaced from audience description ("explaining RAG to someone with no technical background") to explicit persona with negative constraints ("You are an enthusiastic and patient tutor — you never sound like a manual or a search engine").
- **Alternatives considered:** Keeping the description but making it more emphatic; adding a "tone" section at the end of the prompt.
- **Reason:** Describing the target audience tells the LLM who it's talking to, not how to behave. Without a declared voice, the model defaults to its trained general-assistant persona, which is formal and manual-like. Negative constraints ("never sounds like a manual or search engine") are operationally stronger than positive descriptions because they give the model a concrete rejection signal it can apply to each generated sentence.

## Welcome Message UX (C45.6 / 2026-05-23)

### `_PROGRESS_PHASES` inline, not reusing `_PHASE_TOPICS` (Commit 45.6)
- **Date:** 2026-05-23
- **Commit:** 45.6
- **Decided by:** Aria
- **Decision:** Progress display in `_build_welcome_message()` uses a locally-defined `_PROGRESS_PHASES` list (hardcoded slugs per phase) rather than the module-level `_PHASE_TOPICS` dict.
- **Alternatives considered:** Reusing `_PHASE_TOPICS` directly; extracting a shared constant for both purposes.
- **Reason:** `_PHASE_TOPICS` maps mastery level → the topics active for question selection at that phase. `_PROGRESS_PHASES` maps phase name → all slugs that belong to that phase for progress counting. These serve different purposes: the first is adaptive (which topics are in scope right now), the second is cumulative (all topics the user might have scored across their journey). They happen to overlap but are not the same concept. Inline constant makes the independence explicit and prevents future callers from conflating them.

### First-time welcome condition: `interaction_count == 0 AND mastery_level == "novice"` (Commit 45.6)
- **Date:** 2026-05-23
- **Commit:** 45.6
- **Decided by:** Aria
- **Decision:** The scaffolded starter-path welcome is shown only to users with both `interaction_count == 0` AND `mastery_level == "novice"`. Non-novice users with `interaction_count == 0` (e.g. self-reported intermediate who skipped onboarding) receive the progress-first returning-user format with 0/N counts.
- **Reason:** The first-time welcome is for users who genuinely don't know where to start. A user who self-identified as intermediate during onboarding already has a declared entry point; offering "Explain RAG like I'm 14" is condescending and incongruent. The returning-user format with 0/5 Core progress still communicates "you haven't started yet" without being tone-deaf about their reported expertise level.

## Markdown Rendering & Prompt Formatting (2026-05-23)

### CSS gradient declarations require `!important` to survive Quasar's cascade (2026-05-23)
- **Date:** 2026-05-23
- **Commit:** hotfix (EranMani request — `fix(EranMani): enforce markdown headers`)
- **Decided by:** Aria / Team Lead
- **Decision:** All five gradient-clip declarations on `.nicegui-markdown h1/h2/h3` use `!important`, plus an explicit `color: transparent !important` guard.
- **Alternatives considered:** Increasing selector specificity (e.g. `body .nicegui-markdown h2`); injecting a `<style>` block directly inside the card that contains `streaming_md`.
- **Reason:** Quasar sets `color` on the body and its component reset CSS cascades that value into block elements. The `-webkit-text-fill-color: transparent` gradient trick only works when the text fill is fully transparent — if Quasar's `color` wins, it bleeds through and the gradient disappears. `!important` on all five declarations is the minimal reliable fix. Selector specificity alone is fragile because Quasar's stylesheet load order relative to `ui.add_head_html()` is not guaranteed across NiceGUI versions.
- **Consequences:** Any future override of heading colors inside `.nicegui-markdown` will also need `!important`. Document this in any PR that touches the chat CSS.

### Mastery-matched routing: fallback to lower tier before higher (Commit 46)
- **Date:** 2026-05-23
- **Commit:** 46
- **Decided by:** Nova
- **Decision:** When a user's target difficulty tier has no questions for a given slug, the fallback order is lower tiers first, then higher. For example: `advanced` → tries `intermediate` before trying `expert`. For `expert`: tries `advanced`, then `intermediate`, then `novice`.
- **Alternatives considered:** Fallback to higher tier first; random selection among available tiers; error/empty return.
- **Reason:** Serving easier material is pedagogically preferable to serving harder material when the target tier is unavailable. A user who is advanced but has no advanced questions on a topic is better served by a consolidation question (intermediate) than a stretch question (expert). An empty return is never acceptable — always deliver something. Higher-first fallback would produce the opposite behavior and create frustration.
- **Consequences:** A novice user with no novice questions on a topic gets intermediate before advanced before expert. The fallback only activates when the question bank has a gap at the target tier.

### Prompt heading rules must be unconditional, not discretionary (2026-05-23)
- **Date:** 2026-05-23
- **Commit:** hotfix (EranMani request — `fix(EranMani): enforce markdown headers`)
- **Decided by:** Team Lead
- **Decision:** All 5 RAG prompt templates now state: "every response longer than one sentence MUST open with a `##` heading — no exceptions." The previous rule ("required when 2+ distinct concepts or paragraphs") was replaced.
- **Alternatives considered:** Keeping the conditional rule but making it louder; post-processing responses to inject a heading if none is found; adding a second LLM call to format the output.
- **Reason:** LLMs treat conditional formatting rules as a permission question they answer per-response. "Required when 2+ concepts" means the model decides on every turn whether that condition is met — and for follow-up questions it consistently decided it wasn't, producing plain prose. An unconditional rule removes the decision entirely. The escape hatch ("single-sentence answers may use plain prose") prevents forced structure on trivially short answers while ensuring every substantive response has at least one visible heading.
- **Consequences:** Responses that would previously have been one short paragraph may now open with a `##` heading. Mira flagged this as worth monitoring for over-formatting; the rule can be relaxed per-level-prompt if users report it as noisy.

---

## Curriculum Restructure (C47)

### `document_ingestion` replaces `langchain_fundamentals` as Phase 2 Core topic (Commit 47)
- **Date:** 2026-05-23
- **Commit:** 47
- **Decided by:** Team Lead (replan 2026-05-23)
- **Decision:** `langchain_fundamentals` is removed from the Phase 2 curriculum and replaced with `document_ingestion`. The LangChain question files are archived to `knowledge-base/curriculum/questions/archive/`, not deleted.
- **Alternatives considered:** Keeping `langchain_fundamentals` alongside `document_ingestion` (10-slug curriculum); deleting the LangChain files entirely.
- **Reason:** The app is named "RAG from scratch" — a dedicated topic slot for LangChain API specifics conflicts with the concept-first identity. LangChain is a convenience layer, not a RAG concept; teaching it as a required Core topic implies the curriculum is about a framework rather than the underlying principles. `document_ingestion` is the actual "from scratch" starting point that was absent: a learner who cannot explain how raw documents flow into a RAG pipeline is missing the first practical step. Files are archived (not deleted) so the content is recoverable if a follow-on "frameworks" track is added later.
- **Consequences:** Phase 2 now covers: `chunking_strategies`, `vector_databases`, `retrieval_methods`, `context_and_prompting`, `document_ingestion`. A parallel C47.1 (Nova) updates the five src/ slug registries (`VALID_MODULE_SLUGS`, `PHASE_2_TOPICS`, `_ORDERED_SLUGS`, Core topics list in ui.py, assessment prompt) to match. `langchain_fundamentals` is orphaned in the archive and will not appear in any user's learning path or scoring calculation after C47.1.

---

## LLM Question Synthesis (C52)

### LLM synthesis integrated into `_deliver_mcq`, not as a new LangGraph node (Commit 52)
- **Date:** 2026-05-24
- **Commit:** 52
- **Decided by:** Nova + commit spec
- **Decision:** `question_generation.py` is called from a new `_deliver_mcq` async helper inside `test_delivery.py`. No new LangGraph node is added. The function tries LLM generation, caches the result in `AgentState.generated_question_pool`, and falls back to the bank silently on any failure.
- **Alternatives considered:** A new `generate_node` in the LangGraph graph (before `test_delivery`); a background pre-generation job that populates a separate cache.
- **Reason:** Adding a node would require a new graph edge, state field for generation status, and error-handling at the graph routing level. The synthesis is a delivery-time enhancement — it belongs in the delivery layer, not the routing layer. `_deliver_mcq` already owns fallback logic; generation is a transparent upgrade to that path. Bank fallback happens silently within the same async call, with no graph topology changes.
- **Consequences:** `_deliver_mcq` is the single point of responsibility for what question text reaches the user. Generation success, pool cache hit, and bank fallback all produce the same return shape — callers are decoupled from the source. The 15s LLM timeout is enforced inside `generate_questions` to prevent the delivery path from hanging.

### Session-scoped question pool in `AgentState` (Commit 52)
- **Date:** 2026-05-24
- **Commit:** 52
- **Decided by:** Nova + commit spec
- **Decision:** `AgentState.generated_question_pool: dict[str, list] | None` is the session cache for LLM-synthesized questions, keyed by `"slug:mastery_level"`. LangGraph's MemorySaver persists it across turns within a thread.
- **Alternatives considered:** External Redis cache (shared across sessions and users); in-memory module-level dict (shared across all threads); not caching (call LLM on every delivery).
- **Reason:** Per-session thread persistence is the correct granularity for generated questions: questions stay fresh for a session but are regenerated across sessions to avoid staleness. Redis would add cross-session coupling without benefit; module-level state would mix user questions. Using LangGraph's existing MemorySaver (already in use for `messages`) is zero additional infrastructure.
- **Consequences:** `generated_question_pool` is None on session start and never saved to the user profile DB. Each new session (new thread_id) begins with a fresh LLM generation call on the first delivery for each `(slug, level)` pair. The pool is included in `build_selection_result`'s returned dict only when not None, following the `messages` optionality pattern.

### State mutation pattern in `_deliver_mcq` — deferred refactor to C52.1 (Commit 52)
- **Date:** 2026-05-24
- **Commit:** 52
- **Decided by:** Team Lead (Option B at gate review)
- **Decision:** `_deliver_mcq` directly mutates `state["generated_question_pool"]` to make the updated pool visible to `select_test_question` for inclusion in the returned dict. This is a deliberate temporary pattern — the C52.1 refactor will make `_deliver_mcq` return a 3-tuple `(display_text, correct_answer, updated_pool)`, removing the mutation.
- **Reason:** Viktor flagged the mutation as a fragile LangGraph pattern — state updates must flow through returned dicts, not in-place mutation. The mutation is currently safe because `generate_questions()` either returns a non-empty list or raises, so no exception can occur between mutation and return. However, the pattern violates the LangGraph state contract and obscures the data flow. Team Lead chose to commit C52 as functionally correct and defer the structural fix to a named follow-up to preserve the gate result and avoid another review cycle on unchanged behavior.
- **Consequences:** C52.1 converts `_deliver_mcq` to return `(str | None, str | None, dict | None)` and threads the pool update through `select_test_question` → `build_selection_result`. Type annotation also tightened: `dict[str, list]` → `dict[str, list[dict[str, Any]]]`.

---

## Auto-Initiated Intro (C52.3)

### Seed prompt routes through the real LangGraph graph — no hardcoded response text (Commit 52.3)
- **Date:** 2026-05-24
- **Commit:** 52.3
- **Decided by:** commit spec (Claude)
- **Decision:** `POST /api/chat/seed` builds a prompt string and feeds it into `rag_graph.astream_events()` — the same graph invocation path as regular `/api/chat`. No hardcoded AI text anywhere in the seed endpoint.
- **Alternatives considered:** Static hardcoded intro text per mastery level (no LLM call); a separate simpler LLM call outside the graph.
- **Reason:** Routing through the real graph ensures the seed response is personalized, mastery-level-adaptive, and subject to the same assessment pipeline. Hardcoded text would drift out of sync with the rest of the app; a separate LLM call would bypass retrieval and assessment. The spec explicitly required "routes through the real LangGraph graph."
- **Consequences:** The seed response undergoes full graph execution including retrieval and assessment. `thread_id` is set to `user_id` (not a per-tab value) so the seed turn persists in the user's thread and can influence their learning history. The initial `AgentState` uses the seed prompt as both `messages[0].content` and `state["question"]`.

### `asyncio.ensure_future()` for fire-and-forget page-load trigger (Commit 52.3)
- **Date:** 2026-05-24
- **Commit:** 52.3
- **Decided by:** Aria + commit spec
- **Decision:** `index()` calls `asyncio.ensure_future(_seed_session())` after all UI elements are defined, gated behind `if bearer_ok`.
- **Alternatives considered:** `await _seed_session()` inline (blocks page render); `ui.timer(0, ..., once=True)` (NiceGUI pattern but adds timer lifecycle management overhead).
- **Reason:** `ensure_future` schedules the coroutine on the running event loop without blocking page render — the page is fully interactive before the seed response arrives. `ui.timer(0, once=True)` works similarly but requires a cancellation guard; `ensure_future` is idiomatic for fire-and-forget coroutines. The `bearer_ok` gate ensures anonymous users never trigger a seed call.
- **Consequences:** Seed runs asynchronously after `index()` returns. If the server is slow, the user sees the page UI first, then the AI bubble appears. Seed failure is silently swallowed (`except Exception: pass`) — chat input, chips, and profile panel remain functional.

### `current_user_optional` + explicit 401 guard for seed endpoint (Commit 52.3)
- **Date:** 2026-05-24
- **Commit:** 52.3
- **Decided by:** Nova
- **Decision:** The seed endpoint uses `Depends(current_user_optional)` and raises `HTTPException(401)` when `current_user is None`, rather than using `Depends(get_current_user)` directly.
- **Alternatives considered:** `Depends(get_current_user)` which auto-raises 401 on missing/invalid token.
- **Reason:** The pattern is consistent with how other endpoints in `chat.py` handle optional auth — `current_user_optional` is the project-wide pattern when the 401 behavior needs to be explicit and controllable at the call site. The seed endpoint has no anonymous use case (Aria's trigger is already gated by `bearer_ok`), but the explicit guard makes the contract clear: seed is always authenticated-only.
- **Consequences:** No behavior difference at runtime — anonymous requests to `/api/chat/seed` always get 401. The explicit guard documents intent more clearly than relying on the dependency auto-raise.

### Seed bubble hidden until first token — `set_visibility` reveal pattern (Commit 52.3)
- **Date:** 2026-05-24
- **Commit:** 52.3
- **Decided by:** Aria
- **Decision:** The AI bubble container is created with `set_visibility(False)` immediately after construction, then `set_visibility(True)` is called on the first SSE token, using a `first_seed_token = [False]` mutable list as the one-shot guard.
- **Alternatives considered:** Creating the bubble element only on the first token (requires partial UI construction); always showing an empty bubble (visible loading flash with no content).
- **Reason:** Pre-building the bubble avoids DOM insertion jitter during streaming. Hiding it until the first real content arrives prevents an empty/skeleton bubble from flashing before the AI starts responding. The mutable list `[False]` pattern is the established NiceGUI closure mutation idiom (same as `stage_active` in `send()`).
- **Consequences:** The `seed_col` element exists in the DOM from page load but is invisible. If the seed call fails before the first token, it stays invisible — clean failure. If the seed call succeeds, it becomes visible exactly when the first word arrives.
