# ARCHITECTURE.md — RAG from Scratch

> Maintained by Claude. Updated before every Team Lead approval prompt when a commit
> introduces a new component, pattern, or data flow.
> Last updated: 2026-05-10 (Commit 15 — fix-score-delta-semantics)

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
- **Purpose:** Browser-based chat interface; auth pages; profile panel (Commit 18+)
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
- **Purpose:** Merges topic score deltas, computes mastery level, strengths, and gaps — no DB access
- **Contract:** `compute_topic_scores(current_profile, assessed_topics, interaction_count) → TopicScoreUpdate`
- **Depends on:** nothing (pure function, zero imports outside stdlib/typing)
- **Introduced in:** Commit 14
- **Consumed by:** Nova's `update_profile_node` (Commit 15)

### Profile Update Node (`update_profile_node`)
- **Type:** LangGraph node (synchronous)
- **Owner:** Nova
- **Purpose:** Persists topic score deltas to the user profile after each assessed turn
- **Contract:** reads `user_id`, `assessment_error`, `topic_scores_delta` from `AgentState`; returns `{}`
- **Depends on:** Topic Scoring Service (`compute_topic_scores`), User Profile Service (`get_profile_by_user_id`, `update_profile`)
- **Introduced in:** Commit 15 (stub from Commit 12 replaced)

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
8.   generate_node → SystemMessage(context) + messages → LLM → streams tokens
9.       ↳ on_chat_model_stream events → SSE "token" events to client
10.  assess_node → second LLM call → AssessmentOutput (topic_scores_delta, user_level)
11.  update_profile_node → compute_topic_scores() → update_profile() → SQLite
12. SSE "done" event: { user_level, assessed_topics }
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
assess_node            — calls assessment_prompt | llm.with_structured_output(AssessmentOutput);
  │                       writes topic_scores_delta, identified_gaps, assessment_error
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

## Sections to Complete During Build

- **Monitoring pipeline** — log flow from app → Logstash → Elasticsearch — after Commit 24

*Last updated: 2026-05-10 — Commit 14 complete (topic scoring service; scoring algorithm thresholds documented)*
