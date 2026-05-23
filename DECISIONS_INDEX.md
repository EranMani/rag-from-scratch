# Decisions Index
*Always-loaded companion to DECISIONS.md. One-liner per decision — full prose in DECISIONS.md.*
## MCQ Question Banks (C33)
71. **MCQ as phase-gate advancement instrument** — binary answer-key comparison (no LLM evaluator); eliminates evaluator variance at gate decision points; open-ended questions remain for in-session learning
72. **Separate `questions/mcq/[slug].md` file tree** — parallel to open-ended banks; prevents format drift; gives Nova (C35) a clean, unambiguous import path
73. **5 MCQs per topic, 2/2/1 distribution** — satisfies `min_questions_per_session=3`; weights foundational knowledge (beginner) before practitioner application (intermediate) before synthesis (advanced)

## Phase Gate Enforcement (C34)
74. **`_LEVEL_TO_PHASE` dict with `PHASE_1_TOPICS` fallback** — dict lookup (`_LEVEL_TO_PHASE.get(user_level, PHASE_1_TOPICS)`) over if/elif; unknown/invalid levels fall through to the most restrictive gate (Phase 1); O(1) vs O(n); all 5 Literal values covered explicitly

## MCQ Assessment Engine (C35)
75. **Regex extraction for freeform MCQ answers** — `\b([A-Da-d])\b` captures first standalone letter; accepts "B", "Option B", "I think B"; word boundary prevents matching 'a' in "above"; first match wins
76. **`is_mcq` flag in `ChatResponse`** — typed boolean in SSE done event so Aria knows to render A–D buttons vs. plain input; parsing test_question text in the frontend is fragile; explicit field is the correct typed contract

## UI Foundation (C26)
68. **Font injection per `@ui.page`** — NiceGUI creates a fresh HTML document per route; font links must be injected in each page function independently
69. **`!important` on Quasar button gradient** — Quasar re-applies its own background after render; `!important` is the reliable override; class-based approach is the clean future fix
70. **Google Fonts CDN accepted (portfolio)** — privacy trade-off logged (CWE-829); self-host `@fontsource/inter` if real users added

## Question Type Balance (C45.3)
85. **`select_question_type` as standalone pure function** — inlining in `select_test_question` would make ratio-distribution testing require full pipeline mocking; standalone function keeps the decision point visible and testable independently
86. **Explicit 0.0 fast-path for novice/beginner** — `random.random() < 0.0` is always False but semantically misleading; explicit guard makes the pedagogical constraint visible in code, not just the constant value

## Prompt Quality (C45.5)
87. **Floor-first RESPONSE FORMAT (all 5 prompts)** — "only if/when" → mandatory floor; LLM treats permissive as withheld permission → plain prose; floor forces minimum structure signal
88. **Explicit persona in `_NOVICE_SYSTEM`** — audience description → declared voice + negative constraints; abstract label gives LLM no behavioral anchor

## Welcome Message UX (C45.6)
89. **`_PROGRESS_PHASES` inline (not `_PHASE_TOPICS`)** — display phase uses hardcoded slug lists; selection phase uses mastery-keyed dict; two concerns, same slugs, different semantics — independence explicit
90. **First-time path: `interaction_count == 0 AND mastery_level == "novice"`** — non-novice first-timers get returning-user format (handles 0/N gracefully); first-time path for users who genuinely don't know where to start

*Last updated: 2026-05-23 — Commit 45.6*

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

## Adaptive Prompt Library (C17)
44. **DEFAULT_PROMPT separate from PROMPT_TEMPLATES dict** — enables `PROMPT_TEMPLATES.get(user_level, DEFAULT_PROMPT)`; prevents `None` key in dict; makes fallback intent explicit at every call site
45. **Single `{context}` variable per template** — question is already in `state["messages"]` as HumanMessage; double injection would confuse model priority; only retrieved context needs injection

## Dynamic Chat UI (C20)
52. **`ui.timer` lifecycle: `stage_active` flag + `finally` ordering** — flag set to `False` before `cancel()` in `finally`; guards `_advance` against use-after-delete race; project-wide pattern for timers paired with deletable UI elements

## Production Compose Patterns (C21)
53. **Dev monitoring behind `profiles: [monitoring]`** — `docker compose up` runs core stack only; monitoring opt-in; reduces cold-start friction for contributors
54. **CHROMA_PORT=8000 in prod compose env block** — container listens on 8000; config.py default of 8001 is for dev host-side tooling only; prod `environment:` overrides `.env.prod` to guarantee correct port

## Scoring Model Product Spec (C23)
60. **Assessment trigger: 0.60 readiness OR 5 content turns** — 0.60 is above chance, below gate minimum; 5 turns catches first-time learners ready by engagement depth; explicit "quiz me" always honored
61. **No score decay** — spaced repetition formula handles recency; time-based decay punishes paused learners without reflecting real knowledge change
62. **user_level by phase gate state, not score average** — average conflates "high on few topics" with "adequate across many"; gate position is the correct adaptive-prompt signal
63. **One deferral per topic per session** — unlimited deferrals create avoidance loops; zero deferrals is coercive; one balances learner readiness with anti-avoidance
64. **Transparent assessment, no mid-session numeric exposure** — hidden testing erodes trust; showing thresholds during assessment invites gaming; post-session summary is the correct reveal point

## Profile UI Panel (C19)
50. **Nested `@ui.refreshable` for profile panel** — nested inside `index()` to close over request-scoped `http()`/`auth_headers()` without parameter threading; idiomatic NiceGUI pattern
51. **All 6 modules always rendered (missing → 0.0)** — shows full curriculum scope; progressive disclosure deferred if telemetry shows disengagement

## Adaptive Graph Integration (C18)
46. **Null-byte separator in query cache key** — `f"{question}\x00{user_level}"` before SHA-256; naive concatenation (`question + user_level`) is not injective and allows cross-level cache collisions
47. **ChatResponse typed schema over hand-constructed dict** — single source of truth for SSE `done` wire format; Pydantic enforces types; field renames cause compile-time errors not silent wire breaks
48. **`user_level: str | None = None` with `None` = "assessment unavailable"** — not a level value; UI must treat null as "assessment did not run"; falsy-as-novice would mask assessment failures
49. **Three wiring changes bundled atomically in C18** — shared invariant: once `user_level` is in `AgentState`, prompt selection, cache key, and response schema must all update together; splitting would create a window of cross-level cache correctness bug

## Scoring Service Patterns (C14)
40. **Invalid slug filter by value type, not allowlist** — allowlist couples scoring to curriculum; value-type check (`isinstance(score, (int, float))`) is the correct scoring invariant; unknown-but-numeric slugs stored; enforcement belongs at Nova's assess_node boundary
41. **Silent score clamping to [0.0, 1.0]** — defensive last-writeable boundary before profile persistence; LLM may produce out-of-range values; no log on clamp (add later if monitoring needed)

## Profile Update Node (C15)
42. **Scoring-derived gaps, not LLM identified_gaps, written to DB** — `AgentState.identified_gaps` is per-turn LLM noise; `score_update["gaps"]` reflects cumulative merged mastery (≤ 0.3 threshold); persisting LLM gaps would overwrite history with a single-turn signal
43. **Fast-exit order: user_id before assessment_error** — anonymous user has no profile to fetch; checking assessment_error first would attempt a DB lookup with user_id=None before the guard triggers

## Curriculum Design (C22)
55. **Phase 2 dual gate (per-topic 0.70 AND mean 0.75)** — Phase 2 topics are interdependent; mean floor prevents imbalanced mastery from advancing; Phase 1 and Phase 3 have per-topic minimums only
56. **Phase 3 minimum 0.75 (vs 0.70 for Phase 1)** — production knowledge has higher downstream stakes; operational judgment requires deeper competency than foundational understanding
57. **Spaced repetition scoring: `0.7 × current + 0.3 × best_prior`** — primarily reflects current performance; rewards learning persistence without penalizing early struggle; `best_prior` not running average
58. **Null vs 0.0 for unassessed topics** — null explicitly fails gate checks; preserves "hasn't attempted" vs "attempted and scored 0" distinction; prevents unassessed-topic-as-passing bug
59. **Minimum 3 questions per session for valid score update** — prevents single lucky/unlucky answer from anchoring extreme scores; 3 is minimum for meaningful granularity

## Profile Scoring Rewrite (C25)
65. **Phase gate checks are cumulative in `get_mastery_level`** — `expert` requires p1 AND p2 AND p3 (not just p3); avoids corrupt-DB false expert
66. **`session_history` persisted in user_profiles table** — best_prior requires cross-session access; JSON array column in profile row, not a separate session events table

## MCQ Chat UI (C37)
67. **Mutable list `[False]` for closure mutation (not `nonlocal`)** — NiceGUI `with` context manager nesting makes `nonlocal` scope fragile; single-element mutable list lets click handlers and async callbacks mutate shared state without scope tracking
67. **Idempotent migration: per-row sentinel key check** — `rag_pipeline_architecture` presence guards row; no global migration flag; supports partial crash-resume

## Progression UI (C38)
68. **`ob_step_content` is sync `@ui.refreshable`, async work in separate handlers** — NiceGUI refreshable renders UI elements synchronously; API calls happen in `_ob_select_level`/`_ob_select_answer`/`_ob_skip` which mutate state then call `.refresh()`
69. **Phase lookup dicts at module level, not inside `profile_panel()`** — `profile_panel` refreshes after every chat turn; rebuilding `_PHASE_LABELS`/`_PHASE_TOPICS`/`_ADVANCE_MSG` on each call adds overhead for purely static data

## Knowledge Profile UI (C38.5)
70. **`ui.element("div")` required for precise flex/grid control in NiceGUI** — `ui.row()`/`ui.column()` render as Quasar `q-row`/`q-col` and inject gap/padding that breaks inner `flex:1` and `width:100%`; plain div avoids all interference
71. **SVG gradient defs injected once in `index()` head** — `profile_panel` is refreshable; inline `<defs>` per icon duplicates on every render; page-head injection via `ui.add_head_html()` defines the gradient once and reuses by `id`
72. **CSS `::after` pseudo-element for tab underline via injected stylesheet** — NiceGUI `.style()` sets inline CSS which cannot define pseudo-elements; pseudo-element rules require a class-based stylesheet injected via `ui.add_head_html()`

## Scoring Correctness (C39)
73. **`session_question_count: int | None = None` sentinel default** — `None` skips the session guard; existing callers bypass it until Commit 41 wires the real counter from AgentState; default of `1` would have broken all pre-41 callers by triggering early return
74. **Passive signals excluded from session_history** — passive deltas update topic_score directly but never append to history; prevents weak inference from contaminating `best_prior` used in the MCQ spaced-rep formula

## Gate Remediation (C41)
75. **Phase 1 remediation scoped to `intermediate` only** — novice already gets Phase 1; advanced/expert Phase 1 gaps are likely LLM false positives at high score levels; routing back would be incorrect
76. **`session_question_counts` as AgentState field** — MemorySaver checkpoints it cross-turn; no Redis/API coupling needed; `.get() or {}` guard handles first-turn absence
77. **Proximity hint reads DB in `generate_node`** — `topic_scores_delta` is a per-turn sparse delta, not absolute scores; targeted async DB read is minimal-coupling; silently skipped on lookup failure

## RAG Specialist Persona (C42)
78. **RAG Specialist — writer role with single-owner format** — Lara owns slug schema + format definition; Specialist writes question depth within it; prevents format drift when two agents author to the same question bank

## Phase Unlock UI (C44)
79. **UI-layer gate crossing detection via `_prev_mastery` mutable list** — `gate_just_passed` consumed+cleared by `generate_node` before `profile_panel.refresh()` runs; UI detects advance by comparing current mastery to prior-call value in closure
80. **`_prev_mastery[0] is not None` guard** — prevents animation from firing on first panel load when no baseline mastery has been recorded yet

## Interactive UX — Navigation Chips & Formatting (2026-05-21)
81. **Semantic similarity for nav-intent detection** — `all-MiniLM-L6-v2` embedder (already used for retrieval) reused to classify navigation questions via cosine similarity against 14 anchor phrases; keyword matching rejected because paraphrases like "I'm not sure where to begin" share zero keywords with "what should I learn?"
82. **Navigation chips scoped to nav-intent responses only** — generalizing chips to all lists rejected; explanatory lists form arguments not menus; chips only make sense when the list is a navigation target
83. **Level-filtered chips by mastery_level** — novice: 2 chips (Foundation); intermediate: 6; advanced/expert: 8; sliced server-side where `user_level` is already in scope; prevents curriculum-skipping
84. **MCQ options moved inline into chat bubble** — removed pre-built bottom-panel MCQ construct; options created on-demand inside `response_inner_col`; full option text sent as user message (not just letter); `async def` handlers preserve NiceGUI slot context

## Mastery Level Simplification (2026-05-23)
85. **Remove `beginner` level, merge into `novice`** — both mapped to Phase 1 in-progress with no user-facing distinction; beginner had no badge design; four-level ladder (novice/intermediate/advanced/expert) is simpler and complete

## Prompt Quality (C45.5)
87. **Floor-first RESPONSE FORMAT (all 5 prompts)** — "only if/when" → mandatory floor; LLM treats permissive as withheld permission → plain prose; floor forces minimum structure signal
88. **Explicit persona in `_NOVICE_SYSTEM`** — audience description → declared voice + negative constraints; abstract label gives LLM no behavioral anchor

## Welcome Message UX (C45.6)
89. **`_PROGRESS_PHASES` inline (not `_PHASE_TOPICS`)** — display phase uses hardcoded slug lists; selection phase uses mastery-keyed dict; two concerns, same slugs, different semantics — independence explicit
90. **First-time path: `interaction_count == 0 AND mastery_level == "novice"`** — non-novice first-timers get returning-user format (handles 0/N gracefully); first-time path for users who genuinely don't know where to start
