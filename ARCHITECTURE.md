# ARCHITECTURE.md — RAG from Scratch

> Maintained by Claude. Updated before every Team Lead approval prompt when a commit
> introduces a new component, pattern, or data flow.
> Last updated: 2026-05-19 (Commit 33 — question-bank-mcq)

---

## System Overview

An adaptive teaching agent built on RAG (Retrieval-Augmented Generation). Users interact
with a structured knowledge base; a LangGraph agent assesses their understanding after
each turn, updates a persistent learning profile, and adapts response depth and vocabulary
to the user's current mastery level. Deployed on AWS EC2 behind nginx with a custom domain.

**North star:** A logged-in user interacts with the knowledge base, the agent dynamically
assesses their understanding, and their profile improves over time — the system feels
responsive to who they are, not a static Q&A tool.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.11 | |
| Web framework | FastAPI | Async routes; blocking calls wrapped in asyncio.to_thread() |
| UI | NiceGUI | Mounted on FastAPI via ui.run_with(); WebSocket-based reactive UI |
| Agent framework | LangGraph | graph.astream_events() → SSE StreamingResponse from Commit 10; MemorySaver checkpointer |
| RAG framework | LangChain | LCEL chains, ChromaDB integration, document loaders |
| LLM (primary) | OpenAI (gpt-4o) | Configurable via OPENAI_MODEL env var |
| LLM (fallback) | Ollama (gemma3:4b) | Activated when OpenAI circuit breaker is OPEN |
| Embeddings | HuggingFace sentence-transformers | Local, no API key required |
| Vector store | ChromaDB | Running as a separate HTTP service in Docker |
| Cache | Redis | 3 layers: query, embedding, LLM response |
| Database | SQLite3 | Raw queries, no ORM; WAL mode enabled; future: PostgreSQL |
| Package manager | uv | |
| Containerization | Docker Compose | Multi-service; prod and dev compose files |
| Reverse proxy | nginx | WebSocket support, SSL termination, Let's Encrypt |
| Monitoring | Prometheus + Grafana + ELK | Present in both dev and prod; dashboards TBD |
| Deployment | AWS EC2 (t3.xlarge) | 4 vCPU, 16 GB RAM; 32 GB gp3 EBS |

---

## Agent Domain Map

| Domain | Owner | Key files |
|---|---|---|
| Backend | Rex | `src/app/auth/`, `src/app/profile/`, `src/app/api/routes/`, `src/app/core/`, `tests/` |
| AI / Agent | Nova | `src/agents/`, `src/rag/` |
| Frontend | Aria | `src/app/ui.py` |
| Infrastructure | Adam | `Dockerfile`, `docker-compose*.yml`, `nginx/`, `scripts/`, `systemd/`, `.env*.example` |
| Curriculum | Lara | `knowledge-base/curriculum/`, `docs/scoring-model.md` |
| Docs | Ryan | `README.md`, `GETTING_STARTED.md`, `docs/` |
| Orchestration | Claude | `CLAUDE.md`, `ORCHESTRATION.md`, `AGENTS.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `GLOSSARY.md`, `commit-protocol.md`, `project-state.json`, `team-preferences.md`, `hooks/` |

---

## Component Map

### FastAPI App
- **Type:** service
- **Owner:** Rex
- **Purpose:** HTTP API and NiceGUI host; entry point for all user and agent requests
- **Depends on:** SQLite, Redis, ChromaDB (via RAG pipeline), Ollama
- **Introduced in:** existing codebase

### NiceGUI UI
- **Type:** frontend
- **Owner:** Aria
- **Purpose:** Browser-based chat interface; auth pages; profile sidebar panel; marketing landing page
- **Routes:**
  - `@ui.page("/landing")` — static marketing landing page; unauthenticated entry point (Commit 30); synchronous `def`, no auth/session/API calls; 8 sections + particle canvas animation
  - `@ui.page("/")` `async def index()` — main chat app; authenticated users only; redirects to `/landing` if unauthenticated (changed from `/login` in Commit 30)
  - `@ui.page("/login")` / `@ui.page("/register")` — auth pages
- **Layout:** `ui.row` with 280px profile sidebar (left) and `flex:1` chat column (right), introduced Commit 19
- **Profile panel:** `@ui.refreshable async def profile_panel()` nested inside `index()`; fetches `GET /api/profile/me` on load; handles anonymous / API failure / empty / active user states; `profile_panel.refresh()` called from `send()` after each completed turn (Commit 20)
- **send() flow** (Commit 20): `ui.timer(2.5, _advance)` cycles stage labels ("Retrieving context..." → "Personalizing your answer..." → "Generating response...") while SSE stream runs; `stage_active = [True]` mutable flag guards `_advance` against use-after-delete; `finally` block sets `stage_active[0] = False` → `cancel()` → `delete()` in that order; adaptation badge added from `done_data["user_level"]`; `profile_panel.refresh()` called before re-enabling send button
- **CSS isolation:** all landing page styles namespaced `rag-landing-*`; injected per-page via `ui.add_head_html()`; NiceGUI container constraints (`.nicegui-content`, `.q-page`, `.q-page-container`) overridden in landing page only for full-bleed layout
- **Depends on:** FastAPI app (mounted via ui.run_with())
- **Introduced in:** existing codebase

### Auth System
- **Type:** service
- **Owner:** Rex
- **Purpose:** User registration, login, JWT issuance and verification
- **Depends on:** SQLite (users table), bcrypt, PyJWT
- **Introduced in:** existing codebase

### RAG Pipeline
- **Type:** service
- **Owner:** Nova
- **Purpose:** Retrieve relevant chunks from ChromaDB, generate answers via LLM
- **Depends on:** ChromaDB, Redis cache, OpenAI/Ollama providers, circuit breakers
- **Introduced in:** existing codebase; replaced by LangGraph graph in Commit 10

### LangGraph Agent
- **Type:** agent
- **Owner:** Nova
- **Purpose:** Stateful graph that retrieves, generates, assesses, and updates user profiles adaptively
- **Depends on:** ChromaDB, OpenAI/Ollama, SQLite (user_profiles), Redis
- **Introduced in:** Commits 07–17

### User Profile Service
- **Type:** service
- **Owner:** Rex
- **Purpose:** CRUD for user learning profiles; persists topic scores, mastery level, strengths, gaps
- **Depends on:** SQLite (user_profiles table)
- **Introduced in:** Commits 04–06

### Topic Scoring Service
- **Type:** pure-function service
- **Owner:** Rex
- **Purpose:** Applies spaced-repetition scoring formula to session performance data; computes mastery level from phase gate state; no DB access
- **Contract:** `compute_topic_scores(current_profile: dict, topic_scores_delta: dict[str, float]) → TopicScoreUpdate`
  - `topic_scores_delta` values are session scores (0.0–1.0 absolute), not deltas to add
  - Formula: `topic_score = 0.7 × session_score + 0.3 × best_prior_session_score` (first session: `= session_score`)
  - `TopicScoreUpdate`: `{topic_scores, session_history, strengths, gaps, mastery_level}`
- **Mastery level mapping:** phase gate state (not score average); evaluated expert → novice; `None` topic score fails gate checks; `None ≠ 0.0`
- **Depends on:** nothing (pure function, zero imports outside stdlib/typing)
- **Introduced in:** Commit 14 (additive model); **rewritten in Commit 25** (spaced-repetition + phase gates)
- **Consumed by:** `update_profile_node`

### Profile Update Node (`update_profile_node`)
- **Type:** LangGraph node (synchronous)
- **Owner:** Nova
- **Purpose:** Persists topic score deltas to the user profile after each assessed turn
- **Contract:** reads `user_id`, `assessment_error`, `topic_scores_delta` from `AgentState`; returns `{}`
- **Depends on:** Topic Scoring Service (`compute_topic_scores`), User Profile Service (`get_profile_by_user_id`, `update_profile`)
- **Introduced in:** Commit 15 (stub from Commit 12 replaced)

### Adaptive Prompt Template Library
- **Type:** prompt library
- **Owner:** Nova
- **Purpose:** 5 mastery-level `ChatPromptTemplate` objects (novice → expert) and a `DEFAULT_PROMPT` fallback. Templates vary in explanation depth, assumed prior knowledge, and vocabulary level. Wired into `generate_node` from Commit 18.
- **Interface:** `PROMPT_TEMPLATES: dict[str, ChatPromptTemplate]` and `DEFAULT_PROMPT: ChatPromptTemplate` — both importable from `agents.prompts`
- **Contract:** each template takes a single `{context}` input variable; `.format_messages(context=...)` returns `[SystemMessage]`
- **Introduced in:** Commit 17

### RAG Curriculum
- **Type:** knowledge base (Markdown + JSON artifacts)
- **Owner:** Lara
- **Purpose:** Defines the complete RAG learning curriculum: canonical 8-topic slug list, three-phase progression with hard gates, per-topic test question banks with LLM-evaluable rubrics, MCQ phase-gate advancement questions, and scoring formula for Nova/Rex implementation
- **Location:** `knowledge-base/curriculum/`
- **Key artifacts:**
  - `topic-slugs.json` — machine-readable canonical 8-slug list
  - `gates.md` — phase gate thresholds + scoring formula (open-ended + MCQ binary scoring rules)
  - `curriculum-map.md` — topic tree + learning objectives
  - `questions/[slug].md` — 8 open-ended question banks with correct/partial/incorrect rubrics (LLM-evaluable)
  - `questions/mcq/[slug].md` — 8 MCQ banks (5 questions each); deterministic answer-key scoring; used exclusively for phase-gate advancement tests (Commit 33)
  - `mcq-format.md` — MCQ question schema, quality constraints, scoring rules (Commit 33)
- **Consumed by:** Nova (Commit 24 — assessment engine); Rex (Commit 25 — profile scoring); Mira+Lara (Commit 23 — scoring model spec); Nova (Commits 35 + 36 — MCQ assessment engine + onboarding)
- **Introduced in:** Commit 22; MCQ banks added in Commit 33

### ChatResponse
- **Type:** typed wire schema (Pydantic model)
- **Owner:** Nova
- **Purpose:** Typed schema for the SSE `done` event payload. Single source of truth for the JSON shape that clients receive at the end of each streaming response.
- **Location:** `src/rag/chain.py`
- **Contract:** `answer: str`, `user_level: str | None` (`None` = assessment did not run), `assessed_topics: dict[str, float]` (topic slug → per-turn score delta)
- **Interface:** `build_chat_response(state: dict) → ChatResponse` — adapter that extracts fields from the final `AgentState` dict after `on_chain_end` fires
- **Introduced in:** Commit 18

### Redis Cache
- **Type:** cache
- **Owner:** Nova (logic), Adam (infrastructure)
- **Purpose:** 3-layer cache: query → answer, text → embedding, prompt → LLM response
- **Depends on:** Redis service
- **Introduced in:** existing codebase

### Circuit Breakers
- **Type:** resilience
- **Owner:** Nova
- **Purpose:** Protect ChromaDB, OpenAI, and Redis from cascade failures; trigger fallbacks
- **Depends on:** nothing external
- **Introduced in:** existing codebase

---

## Data Flows

### Chat turn (current, Commits 01–09)

```
1. User submits question via NiceGUI
2. UI calls POST /api/chat with JWT bearer token
3. chat.py verifies JWT → extracts user_id
4. asyncio.to_thread(run_rag_pipeline, question, session_id, user_id)
5. Query cache check → serve from cache if hit
6. retrieve() → ChromaDB (or BM25 fallback) → docs
7. SessionMemory.format_history(session_id) → conversation_history string [Commit 03]
8. LLM response cache check → serve from cache if hit (does not include history in key)
9. generate(question, docs, conversation_history) → LLM → answer
10. Caches updated; SessionMemory updated with new turn
11. Response returned: answer + cache metadata + retrieved chunks
```

### Chat turn (post-LangGraph, Commits 10+)

```
1. User submits question via NiceGUI
2. UI calls POST /api/chat with JWT bearer token
3. chat.py verifies JWT → extracts user_id + session_id
4. Build initial AgentState: messages=[HumanMessage(question)], question, user_id, user_level, ...
5. config = {"configurable": {"thread_id": session_id}}
6. graph.astream_events(initial_state, config) → SSE StreamingResponse
7.   retrieve_node → ChromaDB (or BM25 fallback) → docs, retrieval_source
8.   generate_node → PROMPT_TEMPLATES.get(user_level, DEFAULT_PROMPT) → SystemMessage(context) + messages → LLM → streams tokens
9.       ↳ on_chat_model_stream events → SSE "token" events to client
10.  assess_node → two modes: (A) test mode — deterministic question selection from curriculum,
       no LLM call, returns pending_test_question/slug; (B) evaluation mode — LLM call →
       EvaluationOutput verdict → test_answer_score, topic_scores_delta
11.  update_profile_node → compute_topic_scores() → update_profile() → SQLite
12. build_chat_response(final_state) → ChatResponse → SSE "done" event: { answer, user_level, assessed_topics }
13. MemorySaver checkpointer persists messages under thread_id for next turn
```

Note: `SessionMemory` class deleted in Commit 10. Conversation history is managed entirely
by LangGraph's `MemorySaver` checkpointer — no explicit history-string injection.

### User profile progression

```
Registration → create_profile() → SQLite row (mastery_level: novice, topic_scores: {})
Each turn → assess_node → topic_scores_delta → compute_topic_scores() → update_profile()
GET /api/profile/me → current profile → NiceGUI profile panel
```

---

## External Integrations

| System | How connected | Owner | Notes |
|---|---|---|---|
| OpenAI API | LangChain ChatOpenAI | Nova | Primary LLM; circuit breaker guards it |
| Ollama | LangChain ChatOllama | Nova | Local fallback; runs in Docker |
| ChromaDB | chromadb.HttpClient | Nova | Vector store; circuit breaker guards it |
| Redis | redis-py from_url | Nova | Cache; errors swallowed gracefully |
| SQLite | raw sqlite3 | Rex | WAL mode; users + profiles in one DB file |

---

## Security Boundaries

| Boundary | Mechanism | Notes |
|---|---|---|
| API authentication | JWT Bearer token + Depends(get_current_user) | Applied to /api/auth/me, /api/profile/me, /api/ingest |
| Chat auth | Optional auth + allow_anonymous_chat setting | Anonymous chat configurable; ingest is always mandatory auth |
| File upload path confinement | Path(filename).name + is_relative_to(UPLOAD_DIR) | Two-layer defense against path traversal on /api/ingest |
| Secrets | .env file; never in code | JWT secret, OpenAI API key, NiceGUI storage secret (added Commit 10) |
| Monitoring endpoints | nginx reverse proxy with auth | /grafana, /kibana, /prometheus not publicly browsable |
| /metrics | nginx deny rule | Prometheus scrape endpoint blocked from public internet |

---

## Document Ingest Flow

```
1. User uploads file via POST /api/ingest (JWT required)
2. get_current_user dependency validates JWT → asyncio.to_thread(get_user_by_id)
3. Extension check: only .txt and .md accepted
4. Path confinement: Path(filename).name strips traversal; resolve() + is_relative_to() confirms bounds
5. File bytes written to data/uploads/
6. TextLoader reads file → LangChain Documents
7. asyncio.to_thread(ingest_documents, docs) → ChromaDB (off the event loop)
8. Returns {"status": "ok", "chunks_ingested": N, "filename": safe_name}
```

---

## Known Architecture Debts

| Debt | Impact | Logged | Priority |
|---|---|---|---|
| get_current_user returns full DB row incl. password_hash | Any future endpoint returning current_user directly will leak the hash — callers must project to safe fields | Sage Commit 01 | 🟡 fix before new /me-style endpoints |
| Unbounded file upload size on /api/ingest | Large uploads OOM the process; no size cap exists | Sage Commit 01 | 🟡 fix before public launch |
| SessionMemory deleted in Commit 10 | Replaced by MemorySaver checkpointer. MemorySaver is also in-process — lost on restart. Swap to SqliteSaver for persistence. | Commit 10 | 🟡 swap before production |
| SQLite → PostgreSQL migration pending | Scale limitation; no concurrent writes at volume | DECISIONS.md | 🟢 deferred |
| NiceGUI → Node.js migration pending | UI framework constraint | DECISIONS.md | 🟢 deferred |
| NiceGUI streaming display | SSE tokens wired in Commit 10; NiceGUI reactive token display deferred to Commit 18 | Commit 18 | 🟡 before Commit 18 |
| `_deserialize_row` return type is untyped `dict` | Misses mypy coverage on callers that access keys that don't exist | Viktor Commit 05 | 🟢 advisory |
| `UserProfilePublic` timestamps typed as `str` not `datetime` | Malformed timestamps pass schema validation silently | Viktor Commit 05 | 🟢 advisory — fix before production |
| `_connect()` duplicated in `auth/db.py` and `profile/db.py` | Future hardening applied to one may not be applied to the other | Sage Commit 04 | 🟡 refactor to shared `src/app/core/db.py` when convenient |
| `user_id` returned in `TokenResponse` body on register/login | Pre-conditions any future IDOR — clients can decode JWT `sub` instead; remove field from schema | Sage Commit 06 | 🟡 fix before public launch |
| Non-atomic user+profile insert in `register` route | If `create_profile` fails with non-`IntegrityError`, user row persists without profile; user can log in but `GET /api/profile/me` returns 404 | Sage Commit 06 | 🟡 wrap in shared transaction or use `get_or_create_profile` in route |
| No test for valid JWT with nonexistent `user_id` (deleted-account scenario) | `get_current_user` DB-lookup branch is untested; refactor could silently break 401 on deleted accounts | Quinn Commit 06 | 🟢 accepted coverage debt |
| ~~`compute_topic_scores` has no isolation tests~~ | **Resolved in Commit 15** — 14 new isolation tests added in `tests/test_scoring.py` covering delta merge, clamping, mastery boundaries, strengths/gaps extraction. | Quinn wave C15 → resolved C15 | ✅ closed |

---

## LangGraph Graph Topology

```
START
  │
  ▼
retrieve_node          — reads question from state; calls retrieve(); writes docs, retrieval_source
  │
  ▼
generate_node          — builds SystemMessage(context) + messages; calls LLM (async ainvoke); writes messages, answer
  │
  ▼
assess_node            — two modes: (A) test mode: deterministic question load from
  │                       knowledge-base/curriculum/questions/<slug>.md, no LLM call;
  │                       (B) eval mode: assessment_prompt | llm.with_structured_output(EvaluationOutput)
  │                       → verdict → test_answer_score (1.0/0.5/0.0); writes topic_scores_delta,
  │                       identified_gaps, assessment_error, test_mode, pending_test_question,
  │                       pending_test_slug, test_answer_score
  │
  ├─ assessment_error=False ──┐
  │                           │
  └─ assessment_error=True ───┤  (both paths: _route_after_assess → "update_profile")
                              ▼
update_profile_node    — synchronous node (Commit 15); fast-exits on user_id=None or assessment_error=True;
  │                       calls compute_topic_scores() then update_profile() with merged scores,
  │                       interaction_count+1, and last_activity_at=UTC ISO 8601 timestamp
  │
  ▼
END

Checkpointer: MemorySaver — persists AgentState under thread_id=session_id between turns
Recursion limit: 10 (baked into compiled graph config via .with_config())
Streaming: graph.astream_events(version="v2") — on_chat_model_stream events → SSE tokens
```

---

## Profile Scoring Algorithm

Implemented in `src/app/profile/scoring.py` (Commit 14). Pure function — no DB access.

**Delta merge strategy:**
- `current_profile["topic_scores"]` is already `dict[str, float]` (deserialized by profile DB layer)
- Each entry in `assessed_topics` overwrites the matching key in the merged copy
- Invalid values (non-numeric, None, list) are silently dropped — unknown-but-numeric slugs are stored
- Out-of-range scores are clamped to [0.0, 1.0] before storage

**Mastery level thresholds (average of all topic scores):**
| Range | Level |
|---|---|
| avg < 0.2 | novice |
| 0.2 ≤ avg < 0.4 | beginner |
| 0.4 ≤ avg < 0.6 | intermediate |
| 0.6 ≤ avg < 0.8 | advanced |
| avg ≥ 0.8 | expert |
| empty dict | novice |

**Strengths / gaps thresholds:**
- Strength: score ≥ 0.7
- Gap: score ≤ 0.3

---

## Production Compose Topology

Introduced in Commit 21. `docker-compose.prod.yml` is a standalone file (not a compose override).

**Service inventory (prod):**
| Service | Image | Host port | Container port | Notes |
|---|---|---|---|---|
| app | local build | 8000 | 8000 | entry point; `env_file: .env.prod` |
| chroma | chromadb/chroma:latest | — | 8000 (expose) | vector store; `condition: service_healthy` |
| redis | redis:7-alpine | — | 6379 (expose) | cache; `condition: service_healthy` |
| ollama | ollama/ollama:latest | — | 11434 (expose) | local LLM; `condition: service_started`; memory limit: 5G |
| prometheus | prom/prometheus:latest | — | 9090 (expose) | metrics scraper |
| grafana | grafana/grafana:latest | 3000 | 3000 | dashboard UI; admin pw from env |
| elasticsearch | docker.elastic.co/…:8.13.0 | — | 9200 (expose) | log store; xpack.security off (TODO) |
| logstash | docker.elastic.co/…:8.13.0 | — | 5044, 9600 (expose) | log pipeline |
| kibana | docker.elastic.co/…:8.13.0 | — | 5601 (expose) | log UI |

**Key prod-vs-dev differences:**
- `./src:/app/src` bind mount removed — prod runs the baked image only
- All data/monitoring services use `expose:` not `ports:` (internal-only), except app:8000 and grafana:3000
- `restart: always` on all services (EC2 reboot survivability)
- Log rotation: `json-file` driver, `max-size: 10m`, `max-file: 5` on every service (via `x-logging` YAML anchor)
- `CHROMA_PORT=8000` explicit in app service environment (container-internal; dev host maps 8001→8000)

**Dev compose change (Commit 21):**
- ELK + Prometheus + Grafana services added `profiles: [monitoring]`
- `docker compose up` now starts only core stack (app, chroma, redis, ollama)
- `docker compose up --profile monitoring` activates full stack

**Deployment env vars:** `.env.prod.example` — secrets have empty values; all non-secret fields carry defaults. Four required secrets: `JWT_SECRET`, `NICEGUI_STORAGE_SECRET`, `OPENAI_API_KEY`, `GRAFANA_ADMIN_PASSWORD`.

---

## Sections to Complete During Build

- **Monitoring pipeline** — log flow from app → Logstash → Elasticsearch — after Commit 24
- **Grafana dashboards** — pre-built dashboard exports for request latency / cache hit rate — Commit 26 or 27

## UI Layer — Font and Design System (C26)

**Google Inter font:** Injected via `ui.add_head_html()` separately in each `@ui.page` function (`login_page`, `register_page`, `index`). NiceGUI creates a fresh HTML document per page route — a font link injected in `index()` does not propagate to `/login` or `/register`.

**CSS palette token system:** A `:root` CSS variable block (`--c-bg`, `--c-surface`, `--c-border`, `--c-accent`, `--c-accent-2`, `--c-muted`, `--c-warm`) is defined at the top of the single `<style>` block in `index()`. Tokens are consumed by subsequent UI commits (C27–29). Auth pages use hardcoded hex values (pre-token).

**Auth page redesign pattern:** Login and register pages use radial gradient body background, glass morphism card (`backdrop-filter:blur(8px)` + `rgba` surface), inline SVG logo mark via `ui.html()`, and gradient CTA button. Glass morphism requires no fallback for this portfolio audience.

---

*Last updated: 2026-05-17 — Commit 26 complete (ui-foundation: Inter font, palette tokens, auth page redesign)*
