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
- **C13** langgraph-assessment-llm — assess_node real LangChain chain: assessment_prompt | llm.with_structured_output(AssessmentOutput); prompt in src/agents/prompts/; prompt.__or__ patch pattern for LCEL chain tests; user_level not written mid-graph to avoid circular turn-update
- **C14** topic-scoring-service — TopicScoreUpdate TypedDict is Rex→Nova domain contract; compute_topic_scores pure function merges delta, clamps to [0,1], computes mastery; value-type filter (not allowlist) decouples scoring from curriculum; silent clamping defends against out-of-range LLM output
- **C17** adaptive-prompt-templates — 5 mastery-level `ChatPromptTemplate` objects + `DEFAULT_PROMPT` fallback; single `{context}` variable per template; `DEFAULT_PROMPT` kept outside dict for clean `.get(user_level, DEFAULT_PROMPT)` pattern; full template library before wiring (C18)
- **C18** adaptive-graph-integration — three `user_level` consumers updated atomically (prompt selection, cache key, response schema); null-byte separator makes composite cache key injective; `ChatResponse` Pydantic model replaces hand-constructed SSE done dict; `user_level: str | None` — `None` means assessment did not run, not novice
- **C19** profile-ui-panel — nested `@ui.refreshable` closes over HTTP client and auth headers; two-column layout (280px sidebar + flex:1 chat); all 6 topics render as progress bars (missing default to 0.0); duplicate 37-line login form removed; null-safe rendering with `.get(key) or "—"` pattern
- **C20** dynamic-chat-ui — cycling stage labels replace static spinner; `profile_panel.refresh()` in `finally` keeps sidebar live; adaptation badge surfaces `user_level` in response card; `stage_active` flag + `finally` ordering prevents timer callback use-after-delete race
- **C21** production-compose — separate prod Compose file with no bind mounts, `expose:`-only ports, `x-logging` rotation anchor, memory caps; three gate-fix bugs: bash healthcheck → curl, CHROMA_PORT 8001→8000 in prod env, ANNONYMOUS → ANONYMOUS typo
- **C22** rag-curriculum-design — 8-topic RAG curriculum across 3 phases; spaced repetition scoring (0.7×current + 0.3×best_prior); Phase 2 dual gate (per-topic 0.70 + mean 0.75); null vs. 0.0 for unassessed topics; 64 rubric-structured questions in `knowledge-base/`
- **C23** scoring-model-product-spec — canonical implementation contract for Nova (C24) and Rex (C25); assessment triggers at topic score 0.60 or 5 content turns; no score decay; `user_level` driven by phase gate state not score average; transparent assessment with one deferral per topic per session
- **C25** profile-scoring-rewrite — spaced-repetition formula (0.7×current + 0.3×best), cumulative phase gates, session history in profile row, crash-safe idempotent DB migration
- **C26** ui-foundation — NiceGUI per-page HTML isolation requires font injection in every `@ui.page` function; Quasar post-render style override requires `!important` on gradient CTA; Google Fonts CDN accepted (LOW, self-hosting is the hardened path)
- **C27** ui-header — CSS gradient text with fallback color + SVG path stroke (not text fill) for reliable cross-browser rendering; CWE-79 fixed in email badge by replacing `ui.html()` with escaping `ui.label()`; *full entry* (FULL: SVG rendering technique, XSS fix, gradient fallback pattern)
- **C28** ui-chat — Chat area style redesign: gradient user bubbles, blue left-border accent on AI cards, indigo glow on Knowledge Check cards, indigo thinking indicator — visual continuity with auth page aesthetic (`src/app/ui.py`)
- **C29** ui-sidebar-admin — Profile sidebar and admin dashboard visual polish: color-coded mastery chips, topic score pills with progress bars, red-tinted gap badges, stat card gradients, health status chips — CSS-only redesign via `<style>` block overrides and semantic `ui.label()` classes (`src/app/ui.py`)
