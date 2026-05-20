# Learning Log Archive — Era 1 (Commits 01–20)

> Compressed from LEARNING_LOG.md on 2026-05-20 (eviction threshold reached at C41).
> Covers the foundational backend, LangGraph graph assembly, and first UI panels.
> Full entry detail in git history: `git log --oneline` for commit context.

---

## Era 1 — Foundations · Commits 01–20 · 2026-05-08 to 2026-05-10

### What this era built

The complete backend stack, the LangGraph agent graph, the topic scoring service, the first adaptive prompts, and the first UI panels (profile sidebar + dynamic chat).

### Commit summaries (compressed)

| Commit | Name | Agent | Tag | Key decision |
|---|---|---|---|---|
| C01 | auth-gate-on-ingest | Rex | security | Mandatory auth on `/ingest`; two-layer path confinement (`Path.name` + `is_relative_to`); `asyncio.to_thread` pattern established for blocking I/O |
| C02 | config-and-naming-cleanup | Rex | chore | Fixed two misspelled identifiers (`allow_annonymous_chat`, `load_knoweldge_base`) atomically across all call sites |
| C03 | wire-conversation-history | Rex | architectural | Replaced `format_history(session_id)` with LangGraph's `add_messages` reducer; `session_id` becomes `thread_id` in graph config, not AgentState field |
| C04 | user-profile-db-schema | Rex | architectural | SQLite `user_profiles` table; WAL mode; FK ON DELETE CASCADE; `topic_scores`/`strengths`/`gaps` as JSON TEXT columns; service layer owns serialize/deserialize |
| C05 | user-profile-service | Rex | architectural/security | CRUD service (`get_profile_by_user_id`, `update_profile`, `get_or_create_profile`); `get_or_create` absorbs `IntegrityError` — UNIQUE constraint is the race guard |
| C06 | user-profile-api | Rex | new feature | `GET /api/profile/me` + `GET /api/profile/{user_id}` (admin only); `UserProfileOut` Pydantic response model; `current_user_optional` pattern for anonymous users |
| C07 | langgraph-state-schema | Nova | architectural | `AgentState` TypedDict designed for full C07–C17 arc; `messages: Annotated[list[BaseMessage], add_messages]` reducer; `TopicScoresDelta` as Pydantic model |
| C08 | langgraph-retrieve-node | Nova | architectural | `retrieve_node`: ChromaDB primary, BM25 fallback; `retrieval_source` detected by pre/post `chroma_cb.is_available()` inspection without modifying `retrieve()` signature |
| C09 | langgraph-generate-node | Nova | architectural | `generate_node`: `SystemMessage` + retrieved docs + conversation history; no inline formatting of history (LangGraph handles it via `messages` field) |
| C10 | langgraph-graph-assembly | Nova | architectural | `graph.astream_events(version="v2")` + SSE `StreamingResponse`; `MemorySaver` checkpointer; `session_id` passed as `thread_id`; `assess → update_profile → END` wired |
| C11 | langgraph-graph-smoke-test | Nova | test | 8 smoke tests confirming graph wiring (nodes reachable, SSE events emitted, `MemorySaver` preserves state across turns) |
| C12 | langgraph-assessment-scaffold | Nova | architectural | `assess_node` stub; `_route_after_assess` conditional edge; `assessment_error: bool` field in `AgentState` as error signal; both paths route to `update_profile_node` |
| C13 | langgraph-assessment-llm | Nova | new feature | LLM-based structured output via `chain | llm.with_structured_output(AssessmentOutput)`; `EvaluationOutput` Pydantic model; LangChain LCEL chain mock via `prompt.__or__` patch |
| C14 | topic-scoring-service | Rex | new feature | `compute_topic_scores()` pure function; additive merge with clamp; `get_mastery_level()` from phase gate state; `TopicScoreUpdate` TypedDict as cross-domain contract |
| C15 | profile-update-node | Nova | new feature | `update_profile_node` reads `user_id`, `assessment_error`, `topic_scores_delta`; fast-exit order: `user_id` before `assessment_error`; scoring-derived gaps written to DB, not LLM gaps |
| C16 | fix-score-delta-semantics | Rex | fix | Corrected `topic_scores_delta` semantics: values are absolute session scores (0–1), not cumulative deltas to add |
| C17 | adaptive-prompt-templates | Nova | new feature | 5 `ChatPromptTemplate` objects keyed by mastery level (`novice`→`expert`); `DEFAULT_PROMPT` fallback; single `{context}` variable; `PROMPT_TEMPLATES.get(user_level, DEFAULT_PROMPT)` pattern |
| C18 | adaptive-graph-integration | Nova | architectural | `generate_node` now reads `user_level` from state; null-byte separator in cache key (`\x00` between `question` and `user_level`); `ChatResponse` typed schema for SSE `done` event |
| C19 | profile-ui-panel | Aria | architectural | `@ui.refreshable async def profile_panel()` nested inside `index()` to close over `http()`; fetches `GET /api/profile/me`; handles all user states; `profile_panel.refresh()` after each turn |
| C20 | dynamic-chat-ui | Aria | architectural | `send()` with `ui.timer(2.5, _advance)` stage labels; `stage_active = [True]` mutable list flag guards `_advance` against use-after-delete; adaptation badge from `done_data["user_level"]` |

### Patterns established in Era 1

| Pattern | First applied | Used throughout project |
|---|---|---|
| `asyncio.to_thread` for blocking I/O | C01 | All blocking DB/LLM calls in async routes |
| Mandatory vs optional auth dependency | C01/C06 | All authenticated routes |
| `AgentState` TypedDict covers full arc | C07 | All LangGraph nodes C07–C41+ |
| LangChain chain mock via `prompt.__or__` | C13 | All assess_node tests using LCEL chains |
| `session_id` as `thread_id` in config | C10 | All graph invocations |
| `@ui.refreshable` from first appearance | C19 | Profile panel, onboarding wizard |
| Mutable list `[False]` for closure mutation | C20 | Timer/async UI patterns throughout |
| Phase gate state → mastery level | C14 | All adaptive prompt selection |

---

*Archived from LEARNING_LOG.md — original entries C01–C20 removed to stay under 40-entry limit.*
