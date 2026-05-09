# ARCHITECTURE.md — RAG from Scratch

> Maintained by Claude. Updated before every Team Lead approval prompt when a commit
> introduces a new component, pattern, or data flow.
> Last updated: 2026-05-08 (post-archaeology, pre-build)

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
| Agent framework | LangGraph | Synchronous graph.invoke() inside asyncio.to_thread() |
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
- **Purpose:** CRUD for user learning profiles; topic scoring; mastery level computation
- **Depends on:** SQLite (user_profiles table)
- **Introduced in:** Commits 04–06, 14

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
3. chat.py verifies JWT → extracts user_id
4. SessionMemory.format_history(session_id) → conversation_history string
5. asyncio.to_thread(graph.invoke, AgentState{question, user_id, conversation_history, ...})
6. retrieve_node → ChromaDB (or BM25 fallback) → docs, retrieval_source
7. generate_node → adaptive prompt (user_level from profile) → LLM → answer
8. assess_node → second LLM call → AssessmentOutput (topic_scores_delta, user_level)
9. update_profile_node → compute_topic_scores() → update_profile() → SQLite
10. Response returned: answer + user_level + assessed_topics + cache metadata
11. UI renders answer card + refreshes profile panel
```

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
| Secrets | .env file; never in code | JWT secret, OpenAI API key |
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
| SessionMemory is in-process (lost on restart) | Users lose conversation context on app restart | archaeology | 🟡 |
| SQLite → PostgreSQL migration pending | Scale limitation; no concurrent writes at volume | DECISIONS.md | 🟢 deferred |
| NiceGUI → Node.js migration pending | UI framework constraint | DECISIONS.md | 🟢 deferred |
| No streaming from LangGraph to UI | Agent state transitions are simulated (timer labels) | DECISIONS.md | 🟡 deferred to Option B |
| `src/rag/memory/profiles.py` flat-file store not yet retired | Two profile backends coexist — one writes to JSON files, one to SQLite; a reader using the wrong backend gets stale data | Viktor Commit 04 | 🔴 retire in Commit 05 (spec already deletes it) |
| `jwt_secret` has a hardcoded default in config.py | Any deployment that doesn't override JWT_SECRET issues forgeable tokens | Sage Commit 04 | 🔴 must fix before first authenticated route ships (Commit 05) |
| `_connect()` duplicated in `auth/db.py` and `profile/db.py` | Future hardening applied to one may not be applied to the other | Sage Commit 04 | 🟡 refactor to shared `src/app/core/db.py` when convenient |

---

## Sections to Complete During Build

- **LangGraph graph diagram** — detailed node/edge map — after Commit 13
- **Profile scoring algorithm** — threshold table and delta merge strategy — after Commit 14
- **Monitoring pipeline** — log flow from app → Logstash → Elasticsearch — after Commit 24

*Last updated: 2026-05-09 — Commit 04 complete*
