# commit-protocol.md — RAG from Scratch
> The canonical build sequence. Every commit planned before any code is written.
> Each commit is atomic — one concern, one owner, one clear test gate.
> No commit is made without Team Lead approval. No two commits are combined.
> Status is maintained automatically by post_commit_next_step.py.

---

## Commit Index

| # | Name | Assignee | Status |
|---|---|---|---|
| 01 | auth-gate-on-ingest | backend | pending |
| 02 | config-and-naming-cleanup | backend | pending |
| 03 | wire-conversation-history | backend | pending |
| 04 | user-profile-db-schema | backend | pending |
| 05 | user-profile-service | backend | pending |
| 06 | user-profile-api | backend | pending |
| 07 | langgraph-state-schema | ai-engineer | pending |
| 08 | langgraph-retrieve-node | ai-engineer | pending |
| 09 | langgraph-generate-node | ai-engineer | pending |
| 10 | langgraph-graph-assembly | ai-engineer | pending |
| 11 | langgraph-graph-smoke-test | ai-engineer | pending |
| 12 | langgraph-assessment-scaffold | ai-engineer | pending |
| 13 | langgraph-assessment-llm | ai-engineer | pending |
| 14 | topic-scoring-service | backend | pending |
| 15 | profile-update-node | ai-engineer | pending |
| 16 | adaptive-prompt-templates | ai-engineer | pending |
| 17 | adaptive-graph-integration | ai-engineer | pending |
| 18 | profile-ui-panel | frontend | pending |
| 19 | dynamic-chat-ui | frontend | pending |
| 20 | production-compose | devops | pending |
| 21 | nginx-config | devops | pending |
| 22 | aws-ec2-deployment | devops | pending |
| 23 | integration-tests | backend + ai-engineer | pending |
| 24 | documentation | tech-writer | pending |

---

## Parallel Groups

```
Wave A (Phase 1):    01 ∥ 02 ∥ 03  — all touch distinct files, no shared state
Wave B (Phase 3):    08 ∥ 09       — retrieve_node and generate_node are independent
Wave C (Phase 7):    23 (integration tests — single owner pair, no further split)
```

---

## Commits in Detail

---

### Commit 01 — `auth-gate-on-ingest`

**Commit message:** `fix: require auth on /api/ingest and wrap ingest call in asyncio.to_thread`

**Body:**
Two related fixes to the document ingestion route.
First: adds `Depends(get_current_user)` so unauthenticated callers receive 401.
Second: wraps the blocking `ingest_documents()` call in `asyncio.to_thread()` — consistent
with the existing pattern in `chat.py` and required because ChromaDB HTTP calls block the event loop.

**Assignee:** Rex (`rex.stockagent@gmail.com`)

**Files touched:**
- `src/app/api/routes/documents.py`

**Depends on:** none

**Parallel with:** 02, 03

**Testing — done when:**
- [ ] `POST /api/ingest` without a token returns `401 Unauthorized`
- [ ] `POST /api/ingest` with a valid Bearer token accepts the file and returns `{"status": "ok"}`
- [ ] The endpoint does not block other concurrent requests during ingestion (verify with two simultaneous requests)

---

### Commit 02 — `config-and-naming-cleanup`

**Commit message:** `chore: fix config typos and update model default`

**Body:**
Corrects two typos that exist in the current code and would silently propagate
into new code if left unfixed:
- `allow_annonymous_chat` → `allow_anonymous_chat` in `config.py` and all call sites
- `load_knoweldge_base` → `load_knowledge_base` in `indexer.py` and all call sites
- Updates `openai_model` default from `gpt-4o` to `gpt-4o` (keep for now — Team Lead
  to update to target model once exact model ID is confirmed with OpenAI)

**Assignee:** Rex (`rex.stockagent@gmail.com`)

**Files touched:**
- `src/app/core/config.py`
- `src/rag/pipeline/indexer.py`
- `src/app/main.py` (call site update)
- `src/app/ui.py` (call site update for allow_anonymous_chat)

**Depends on:** none

**Parallel with:** 01, 03

**Testing — done when:**
- [ ] `grep -r "annonymous"` returns no matches in `src/`
- [ ] `grep -r "knoweldge"` returns no matches in `src/`
- [ ] App starts without errors after rename

---

### Commit 03 — `wire-conversation-history`

**Commit message:** `feat: inject conversation history into RAG generator prompt`

**Body:**
Wires `session_memory.format_history(session_id)` into the generator so the LLM
sees prior turns when answering. Currently the history is collected but discarded.
Adds a `{history}` slot to `RAG_PROMPT` and a `conversation_history` parameter to
`generate()`. History injection happens after retrieval (step 2 of chain.py) — it
influences generation, not retrieval.

**Assignee:** Rex (`rex.stockagent@gmail.com`)

**Files touched:**
- `src/rag/pipeline/generator.py` (add `conversation_history` param, update `RAG_PROMPT`)
- `src/rag/chain.py` (pass `format_history(session_id)` to `generate()`)

**Depends on:** none

**Parallel with:** 01, 02

**Handoff to Nova (Commit 10):** When `chain.py` is replaced by the LangGraph graph,
the `format_history()` injection MUST be carried forward. It is a named deliverable
of Commit 10 — not an optional carry-over. The graph's `generate_node` must receive
`conversation_history` from `AgentState` and inject it into the prompt.

**Testing — done when:**
- [ ] Asking a follow-up question (e.g. "What did I just ask?") returns a response that references the prior turn
- [ ] First question in a session has an empty history and the prompt still works correctly
- [ ] `format_history()` is called AFTER `retrieve()`, not before

---

### Commit 04 — `user-profile-db-schema`

**Commit message:** `feat: user_profiles table in SQLite with WAL mode and lifespan init`

**Body:**
Creates the `user_profiles` table in `data/app_users.db`. Adds WAL journal mode to
`_connect()` to prevent write-blocking during concurrent LangGraph agent calls.
Registers `init_profile_db()` in the FastAPI lifespan alongside `init_user_db()`.

Table schema:
```sql
CREATE TABLE IF NOT EXISTS user_profiles (
    id                TEXT PRIMARY KEY,
    user_id           TEXT NOT NULL UNIQUE,
    mastery_level     TEXT NOT NULL DEFAULT 'novice',
    interaction_count INTEGER NOT NULL DEFAULT 0,
    topic_scores      TEXT NOT NULL DEFAULT '{}',
    strengths         TEXT NOT NULL DEFAULT '[]',
    gaps              TEXT NOT NULL DEFAULT '[]',
    last_activity_at  TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
```

`mastery_level` values: `novice`, `beginner`, `intermediate`, `advanced`, `expert`.
`topic_scores`, `strengths`, `gaps` stored as JSON strings; service layer deserializes.

**Assignee:** Rex (`rex.stockagent@gmail.com`)

**Files touched:**
- `src/app/auth/db.py` (add `PRAGMA journal_mode=WAL` to `_connect()`)
- `src/app/profile/__init__.py` (new, empty)
- `src/app/profile/db.py` (new — `init_profile_db()` only)
- `src/app/main.py` (call `init_profile_db()` in lifespan)

**Depends on:** 01, 02, 03 (Phase 1 complete)

**Testing — done when:**
- [ ] Fresh app start creates the `user_profiles` table in `data/app_users.db`
- [ ] `PRAGMA journal_mode` returns `wal` when queried on the connection
- [ ] FK constraint is live: deleting a user row cascades to profile row

---

### Commit 05 — `user-profile-service`

**Commit message:** `feat: user profile CRUD service, UserProfilePublic schema, delete JSON stub`

**Body:**
Implements the full profile service layer. Deletes `src/rag/memory/profiles.py`
(the JSON file stub) and updates `src/rag/chain.py` call sites.

Service functions in `src/app/profile/db.py`:
- `create_profile(user_id: str) -> str` — creates row, returns profile_id UUID
- `get_profile_by_user_id(user_id: str) -> dict | None` — deserializes JSON fields
- `update_profile(user_id: str, **fields) -> None` — partial update via dynamic SQL
- `get_or_create_profile(user_id: str) -> dict` — critical: used by LangGraph agent on every entry

`topic_scores`, `strengths`, and `gaps` must be returned as Python objects (dict/list),
not raw JSON strings. The service layer owns deserialization.

`UserProfilePublic` schema in `src/app/profile/schemas.py`:
```python
class UserProfilePublic(BaseModel):
    user_id: str
    mastery_level: str
    interaction_count: int
    topic_scores: dict[str, float]
    strengths: list[str]
    gaps: list[str]
    last_activity_at: str | None
    created_at: str
```

Ships with CRUD unit tests in `tests/test_profile_service.py`.

**Assignee:** Rex (`rex.stockagent@gmail.com`)

**Files touched:**
- `src/app/profile/db.py` (expand with full CRUD)
- `src/app/profile/schemas.py` (new)
- `src/rag/memory/profiles.py` (DELETE)
- `src/rag/chain.py` (remove load_profile/save_profile imports and calls)
- `tests/__init__.py` (new, empty)
- `tests/test_profile_service.py` (new)

**Depends on:** 04

**Testing — done when:**
- [ ] `create_profile()` inserts a row with correct defaults
- [ ] `get_profile_by_user_id()` returns `topic_scores` as `dict`, not a string
- [ ] `update_profile(user_id, mastery_level="intermediate")` updates only that field
- [ ] `get_or_create_profile()` returns an existing profile on second call (no duplicate insert)
- [ ] App starts without import errors after `profiles.py` is deleted

---

### Commit 06 — `user-profile-api`

**Commit message:** `feat: GET /api/profile/me endpoint and auto-create profile on registration`

**Body:**
Exposes the user profile via REST. Adds `create_profile()` call to the register route
so every new user has a profile row immediately — `GET /api/profile/me` never 404s
for a registered user.

**Assignee:** Rex (`rex.stockagent@gmail.com`)

**Files touched:**
- `src/app/api/routes/profile.py` (new — single GET endpoint)
- `src/app/api/routes/auth.py` (add `create_profile()` after `create_user()` in register)
- `src/app/main.py` (include profile router)

**Depends on:** 05

**Testing — done when:**
- [ ] `GET /api/profile/me` with valid token returns `UserProfilePublic` JSON
- [ ] `GET /api/profile/me` without token returns `401`
- [ ] Registering a new user: immediately calling `GET /api/profile/me` returns 200 (not 404)
- [ ] Response includes `topic_scores: {}`, `mastery_level: "novice"` for fresh user

---

### Commit 07 — `langgraph-state-schema`

**Commit message:** `feat: AgentState TypedDict and AssessmentOutput model for LangGraph graph`

**Body:**
Defines the full state schema for the LangGraph graph. This TypedDict is designed for
the entire arc (commits 07–17) — all Phase 4 fields are present from the start.
Retroactive state schema changes cascade through the compiled graph; designing it
completely here prevents that.

`AgentState` fields:
- `question: str`
- `session_id: str`
- `user_id: str | None`
- `conversation_history: str` — formatted from `SessionMemory` before graph entry
- `docs: list` — retrieved LangChain Documents
- `retrieval_source: str` — `"chroma"` or `"bm25"`
- `answer: str`
- `user_level: str` — `"novice"` | `"beginner"` | `"intermediate"` | `"advanced"` | `"expert"`
- `topic_scores_delta: dict[str, float]` — sparse dict of assessed modules this turn
- `identified_gaps: list[str]` — module slugs where understanding is low
- `assessment_error: bool` — True if assess_node failed (triggers fallback edge)
- `trace_id: str`
- `latency_ms: int`
- `cache_hit: str`

`AssessmentOutput` Pydantic model (used by `assess_node` for structured LLM output parsing):
```python
class AssessmentOutput(BaseModel):
    topic_scores_delta: dict[str, float]
    identified_gaps: list[str]
    user_level: str
```

Module slugs (the valid keys for `topic_scores_delta`):
`rag_fundamentals`, `vector_databases`, `langchain`, `chunking_strategies`,
`retrieval_methods`, `production_patterns`

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/__init__.py` (new, empty)
- `src/agents/state.py` (new)
- `src/agents/nodes/__init__.py` (new, empty)

**Depends on:** 04 (profile schema must be defined before designing state fields)

**Testing — done when:**
- [ ] `from agents.state import AgentState, AssessmentOutput` imports without error
- [ ] All required fields are present and typed correctly
- [ ] `AssessmentOutput` validates correctly with a sample LLM response dict

---

### Commit 08 — `langgraph-retrieve-node`

**Commit message:** `feat: LangGraph retrieve_node wrapping existing retriever`

**Body:**
Wraps the existing `retrieve()` function from `src/rag/pipeline/retriever.py` as a
LangGraph node. Reads `question` from `AgentState`, writes `docs` and
`retrieval_source` back into state. `retrieval_source` is set to `"chroma"` or
`"bm25"` based on which path was taken (readable from circuit breaker state).

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/nodes/retrieve.py` (new)

**Depends on:** 07

**Parallel with:** 09

**Testing — done when:**
- [ ] Node receives an `AgentState` with a `question` and returns state with `docs` populated
- [ ] `retrieval_source` is set to `"chroma"` or `"bm25"` on every invocation
- [ ] Node does not raise on an empty question (returns empty docs list)

---

### Commit 09 — `langgraph-generate-node`

**Commit message:** `feat: LangGraph generate_node with history-aware prompt template`

**Body:**
Wraps `generate()` as a LangGraph node. Uses `conversation_history` from `AgentState`
to inject prior conversation context into the prompt. Uses `docs` from state for
retrieved context. The prompt template includes a `{history}` slot from day one —
this avoids a breaking change when adaptive prompts are wired in Commit 17.

The prompt template here is the evolution of the one modified in Commit 03:
```
System: You are an expert on RAG systems. Answer using ONLY the provided context.
        Adapt your explanation depth to the user's level: {user_level}.
        [user_level starts as "novice" — adaptive depth is wired in Commit 17]

Context: {context}
History: {history}
Question: {question}
```

Writes `answer` back into `AgentState`.

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/nodes/generate.py` (new)

**Depends on:** 07

**Parallel with:** 08

**Testing — done when:**
- [ ] Node receives state with `docs`, `question`, `conversation_history` and returns state with `answer` set
- [ ] Node works correctly with empty `conversation_history` (first turn)
- [ ] Node uses `get_provider()` (respects OpenAI circuit breaker → Ollama fallback)

---

### Commit 10 — `langgraph-graph-assembly`

**Commit message:** `feat: assemble LangGraph graph and replace chain.py pipeline`

**Body:**
Wires `retrieve_node` and `generate_node` into a compiled LangGraph graph.
Replaces `run_rag_pipeline()` in `chain.py` with `graph.invoke()`.

Graph invocation is synchronous (`graph.invoke()` inside `asyncio.to_thread()` — same
pattern as the current `run_rag_pipeline` call in `chat.py` and `ui.py`). No change
to the thread dispatch pattern.

The wrapper function preserves the existing return shape:
`{"answer", "cache_hit", "chunks", "latency_ms", "trace_id"}` — `chat.py` and
`ui.py` unpack this directly and must not break.

Cache key strategy: the existing query-level Redis cache is retained for this commit.
Cache key invalidation per user profile is addressed in Commit 17 when adaptive
responses are active. For commits 10–16, cached responses may be shared across users
with different profiles — this is a known temporary limitation, logged here explicitly.

**Handoff consumed from Commit 03:** `conversation_history` threading MUST be wired.
`SessionMemory.format_history(session_id)` is called BEFORE `graph.invoke()` and
passed into the initial `AgentState` as `conversation_history`. This is a named
deliverable of this commit — not optional.

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/graph.py` (new)
- `src/rag/chain.py` (update `run_rag_pipeline` to call `graph.invoke`)

**Depends on:** 08, 09

**Testing — done when:**
- [ ] End-to-end: send a question via `/api/chat`, receive a valid answer
- [ ] `chat.py` and `ui.py` unpack the response without KeyError
- [ ] `conversation_history` is populated in state from `SessionMemory` before graph runs
- [ ] Graph handles ChromaDB circuit breaker OPEN (falls back to BM25 via retrieve_node)

---

### Commit 11 — `langgraph-graph-smoke-test`

**Commit message:** `test: smoke test for assembled LangGraph graph end-to-end`

**Body:**
Minimal integration test that exercises the full assembled graph and verifies
output shape and state population. This commit exists specifically to gate Phase 4
— no adaptive intelligence is built on an untested graph.

Test asserts:
- Graph accepts a valid `AgentState` input and returns a state dict
- `answer` is a non-empty string
- `docs` is a list (may be empty in test environment)
- `retrieval_source` is set to `"chroma"` or `"bm25"`
- `conversation_history` threading: a second invocation with the same session_id
  receives non-empty history

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `tests/test_graph_smoke.py` (new)

**Depends on:** 10

**Viktor Hard Block resolved:** This test gate was flagged as a required blocker before
Phase 4 builds on the assembled graph. Phase 4 (commits 12–17) does not begin until
this commit passes.

**Testing — done when:**
- [ ] `pytest tests/test_graph_smoke.py` passes with no errors
- [ ] Test does not require a live OpenAI key (use Ollama or mock the provider)

---

### Commit 12 — `langgraph-assessment-scaffold`

**Commit message:** `feat: assessment_node scaffold — contracts, fallback edge, stub LLM call`

**Body:**
Adds `assess_node` to the LangGraph graph. This commit ships the node structure,
input/output contract wiring, and a conditional fallback edge. The LLM call is
stubbed (returns a deterministic empty `AssessmentOutput`) — the real assessment
prompt is in Commit 13.

The fallback edge is non-negotiable for LangGraph: if `assess_node` sets
`assessment_error: True` in state, the graph routes directly to `update_profile_node`
with an empty delta (skips the error, profile is not updated). If `assessment_error`
is False, the graph continues normally. Both paths must compile cleanly.

Graph flow after this commit:
`retrieve_node → generate_node → assess_node → [conditional] → update_profile_node`
(update_profile_node is a stub at this stage — wired in Commit 15)

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/nodes/assess.py` (new)
- `src/agents/graph.py` (add node + conditional edge)

**Depends on:** 11

**Testing — done when:**
- [ ] Graph compiles without error after node is added
- [ ] Stub `assess_node` sets `assessment_error: False` and populates empty `AssessmentOutput`
- [ ] Conditional edge routes correctly on `assessment_error: True` (fallback path)
- [ ] Existing smoke test still passes

---

### Commit 13 — `langgraph-assessment-llm`

**Commit message:** `feat: assessment_node LLM integration with structured output parsing`

**Body:**
Replaces the stub in `assess_node` with a real LLM call that extracts topic
understanding from the user's question and the generated answer.

Uses `.with_structured_output(AssessmentOutput)` (LangChain's structured output
interface) — NOT `StrOutputParser`. This ensures the LLM returns a validated
`AssessmentOutput` object. If parsing fails, the node catches the exception,
sets `assessment_error: True`, and the graph takes the fallback edge cleanly.

Assessment prompt evaluates:
- Which knowledge base modules are referenced in this interaction
- What the user's apparent understanding level is for each module
- What gaps are visible from the question asked

The assessment is a second LLM call per user turn. It runs on the same provider
as `generate_node` (OpenAI primary, Ollama fallback via circuit breaker).

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/nodes/assess.py` (replace stub with real implementation)

**Depends on:** 12

**Testing — done when:**
- [ ] `assess_node` with a question about "vector databases" returns `topic_scores_delta` with `vector_databases` key set
- [ ] LLM parse failure sets `assessment_error: True` and does not raise
- [ ] `user_level` in returned state is one of the valid mastery level strings
- [ ] Assessment call uses `get_provider()` — inherits circuit breaker fallback

---

### Commit 14 — `topic-scoring-service`

**Commit message:** `feat: topic scoring service — TopicScoreUpdate interface and tests`

**Body:**
Pure-function scoring service. Nova's `update_profile_node` (Commit 15) imports and
calls this. The typed interface is the contract between Rex's domain (profile DB)
and Nova's domain (LangGraph nodes). It ships as a named deliverable.

`TopicScoreUpdate` TypedDict:
```python
class TopicScoreUpdate(TypedDict):
    topic_scores: dict[str, float]   # full updated scores (all modules)
    strengths:    list[str]           # module slugs with score >= 0.7
    gaps:         list[str]           # module slugs with score <= 0.3
    mastery_level: str                # computed deterministically from avg score
```

`compute_topic_scores(current_profile: dict, assessed_topics: dict[str, float], interaction_count: int) -> TopicScoreUpdate`
- Pure function — no DB calls inside
- Merges `assessed_topics` deltas into existing `topic_scores`
- Computes `mastery_level` from average of all topic scores (deterministic formula)
- Returns full updated `TopicScoreUpdate`

`get_mastery_level(topic_scores: dict[str, float]) -> str`
- Standalone helper: novice < 0.2, beginner 0.2–0.4, intermediate 0.4–0.6, advanced 0.6–0.8, expert >= 0.8

Ships with unit tests in `tests/test_scoring.py`.

**Assignee:** Rex (`rex.stockagent@gmail.com`)

**Files touched:**
- `src/app/profile/scoring.py` (new)
- `tests/test_scoring.py` (new)

**Depends on:** 05

**Testing — done when:**
- [ ] `compute_topic_scores` with a fresh profile and `{"vector_databases": 0.8}` returns correct merged scores
- [ ] `get_mastery_level({"rag_fundamentals": 0.9, "vector_databases": 0.85})` returns `"expert"`
- [ ] Function is pure: same inputs always produce same outputs
- [ ] Invalid module slug in `assessed_topics` is ignored gracefully (not raised)

---

### Commit 15 — `profile-update-node`

**Commit message:** `feat: profile_update_node wired into LangGraph graph after assessment`

**Body:**
Implements `update_profile_node` and wires it into the graph. Consumes:
- `topic_scores_delta` and `identified_gaps` from `AgentState` (set by `assess_node`)
- `compute_topic_scores()` from `src/app/profile/scoring.py` (Commit 14 typed interface)
- `update_profile()` from `src/app/profile/db.py` to persist to SQLite

The node is synchronous (no `asyncio` inside). It is called from `asyncio.to_thread()`
at the graph invocation level — do not introduce nested thread dispatch inside the node.

On `assessment_error: True` (fallback edge), the node is skipped — the profile is
not updated for failed assessments. This is intentional eventual consistency design.

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/nodes/update_profile.py` (new)
- `src/agents/graph.py` (replace stub update_profile_node with real implementation)

**Depends on:** 13, 14

**Testing — done when:**
- [ ] After a full graph invocation with `user_id` set, the profile row in SQLite has updated `topic_scores`
- [ ] `interaction_count` increments after each turn
- [ ] Fallback path (assessment_error=True) does not write to the DB
- [ ] Node works correctly when `user_id` is None (anonymous user — skip profile update)

---

### Commit 16 — `adaptive-prompt-templates`

**Commit message:** `feat: adaptive prompt templates per mastery level`

**Body:**
Creates the prompt template library used by `generate_node` (Commit 17 will wire
them in). One template variant per mastery level. Templates differ in:
- Explanation depth (novice: analogies + definitions; expert: technical detail only)
- Assumed prior knowledge
- Vocabulary level

Templates are defined as a dict keyed on mastery level string. The `generate_node`
selects the correct template based on `user_level` from `AgentState`.

Also includes a default template (used when `user_level` is not set) — identical
to the current `RAG_PROMPT` in `generator.py`, ensuring no regression if the
assessment hasn't run yet.

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/prompts.py` (new)

**Depends on:** 07 (needs AgentState with `user_level`)

**Testing — done when:**
- [ ] All 5 mastery level keys (`novice`, `beginner`, `intermediate`, `advanced`, `expert`) have a defined template
- [ ] Default template (no user_level) matches existing `RAG_PROMPT` behavior
- [ ] Templates import without error

---

### Commit 17 — `adaptive-graph-integration`

**Commit message:** `feat: wire adaptive prompts into graph, fix cache key, extend ChatResponse`

**Body:**
Three related wiring changes that complete the adaptive intelligence system:

1. **`generate_node` updated**: reads `user_level` from `AgentState`, selects the
   matching prompt template from `src/agents/prompts.py`, uses it for the LLM call.

2. **Cache key fix**: the Redis query-level cache key now incorporates `user_level`.
   Without this, two users at different mastery levels asking the same question
   receive the same cached response. New key: `rag:query:{sha256(question + user_level)}`.
   For anonymous users (no `user_id`), behavior is unchanged.

3. **`ChatResponse` extended**: `src/app/api/routes/chat.py` gains two new optional
   fields that the UI uses in Commit 19:
   ```python
   user_level: str | None = None
   assessed_topics: list[str] = []
   ```
   These are populated from `AgentState` by the graph wrapper in `chain.py`.

Cross-domain note: items 2 and 3 touch Rex's files (`redis_cache.py`, `chat.py`).
Nova writes the diff; Rex reviews it in the quality gate before approval.

**Assignee:** Nova (`nova.nodegraph@gmail.com`)

**Files touched:**
- `src/agents/nodes/generate.py` (select adaptive template)
- `src/rag/cache/redis_cache.py` (update query cache key)
- `src/app/api/routes/chat.py` (extend ChatResponse)
- `src/rag/chain.py` (populate new ChatResponse fields from AgentState)

**Depends on:** 15, 16

**Testing — done when:**
- [ ] Two users at different mastery levels asking the same question receive different responses (not served from the same cache entry)
- [ ] Anonymous user chat behavior is unchanged
- [ ] `ChatResponse` includes `user_level` and `assessed_topics` in JSON output
- [ ] Novice user receives an answer with simpler vocabulary than expert user (manual review)

---

### Commit 18 — `profile-ui-panel`

**Commit message:** `feat: profile sidebar panel with refreshable knowledge profile display`

**Body:**
Adds a profile sidebar to the main chat page. Structural changes:

1. **Layout refactor**: replaces the single centered `ui.column` container with a
   `ui.row` containing a left sidebar (~280px) and right chat area (`flex:1`).

2. **Dead code removal**: the duplicate inline login form in `index()` (lines ~195–231
   in the current `ui.py`) is removed and replaced with `ui.navigate.to("/login")`.
   This also removes the duplicate `do_login()` closure.

3. **Profile panel**: built with `@ui.refreshable` decorator from day one so Commit 19
   can call `.refresh()` without layout surgery. Fetches `GET /api/profile/me` on
   page load. Displays:
   - Mastery level label
   - Topic scores as `ui.linear_progress` bars (one per module)
   - Identified gaps as a short tag list
   - Query count and "Last active" timestamp

Panel handles the case where `topic_scores` is empty (fresh user) gracefully —
shows "Start chatting to build your profile" message.

**Assignee:** Aria (`aria.stockagent@gmail.com`)

**Files touched:**
- `src/app/ui.py`

**Depends on:** 06 (profile API), 17 (ChatResponse extended)

**Testing — done when:**
- [ ] Logged-in user sees profile panel on the left side of the chat page
- [ ] Fresh user (no interactions yet) sees the empty-state message, not an error
- [ ] Profile panel loads without blocking the chat area
- [ ] Logging out clears the profile panel
- [ ] Duplicate inline login form is gone from `index()`

---

### Commit 19 — `dynamic-chat-ui`

**Commit message:** `feat: agent state stage labels and profile refresh after each turn`

**Body:**
Two additions to the chat send flow:

1. **Agent stage indicators**: replaces the single `"Thinking..."` label with a
   timer-driven sequence of stage labels while `asyncio.to_thread(graph.invoke, ...)`
   runs: `"Retrieving context..."` → `"Assessing your level..."` → `"Generating response..."`.
   A `ui.timer` at 2.5s intervals advances the label. Timer is cancelled when the
   thread returns. Labels are honest about the pipeline existing without requiring
   real-time graph callbacks.

2. **Profile refresh**: after each turn, calls `profile_panel.refresh()` so the
   sidebar reflects any topic score updates from the completed turn. The refresh
   makes a new `GET /api/profile/me` request.

3. **Adaptation badge**: if `user_level` is present in the response, adds a small
   badge to the response card: `"Adapted for: [level]"` in addition to the existing
   cache/latency/chunks badges.

**Assignee:** Aria (`aria.stockagent@gmail.com`)

**Files touched:**
- `src/app/ui.py`

**Depends on:** 18

**Testing — done when:**
- [ ] Stage labels cycle visibly while a response is being generated
- [ ] Profile panel updates after a turn completes (topic scores change after first substantive interaction)
- [ ] `"Adapted for:"` badge appears when `user_level` is in the response
- [ ] UI does not break when `user_level` is absent (anonymous or pre-assessment turn)

---

### Commit 20 — `production-compose`

**Commit message:** `chore: production docker-compose with monitoring, hardened config, log rotation`

**Body:**
Creates `docker-compose.prod.yml` as a standalone file (not a compose override).
Key differences from dev compose:

- `./src:/app/src` bind mount **removed** — prod runs the baked image
- All internal service ports (`chroma`, `redis`, `ollama`, `elasticsearch`) use
  `expose:` only — not mapped to host
- `restart: always` on all services (survives EC2 reboots)
- Logging driver on every service: `json-file` with `max-size: 10m`, `max-file: 5`
- Memory limits: `ollama` capped at `5G` (t3.xlarge has 16 GB), `elasticsearch` JVM
  heap reduced to `-Xms256m -Xmx512m`
- Grafana: `GF_SECURITY_ADMIN_PASSWORD` read from env, not hardcoded
- Elasticsearch: `xpack.security.enabled=false` flagged with a TODO comment for the
  monitoring hardening commit — Team Lead decision to leave as-is for portfolio demo
- Monitoring services (Prometheus, Grafana, ELK) **remain in prod compose** — portfolio
  decision: the system should show it can evaluate itself in production

Also:
- `docker-compose.yml` (dev): adds `profiles: [monitoring]` to ELK + Prometheus +
  Grafana services so local dev can run `docker compose up` without the monitoring stack
  and opt in with `--profile monitoring`
- `.env.prod.example` created — all env vars required in production with no defaults
  for secrets (JWT_SECRET, OPENAI_API_KEY, GRAFANA_ADMIN_PASSWORD documented as required)

**Assignee:** Adam (`adam.stockagent@gmail.com`)

**Files touched:**
- `docker-compose.prod.yml` (new)
- `.env.prod.example` (new)
- `docker-compose.yml` (add profiles: [monitoring] to monitoring services)

**Depends on:** 17 (all application features complete before production config is written)

**Testing — done when:**
- [ ] `docker compose -f docker-compose.prod.yml config` validates without errors
- [ ] No `./src:/app/src` bind mount present in prod compose
- [ ] All monitoring service ports are internal-only (`expose:`, not `ports:`)
- [ ] `.env.prod.example` contains every env var referenced in config.py with no secret defaults
- [ ] Dev compose `docker compose up` starts without ELK/Prometheus (monitoring profile opt-in)

---

### Commit 21 — `nginx-config`

**Commit message:** `feat: nginx reverse proxy with WebSocket support, HTTPS, and monitoring routes`

**Body:**
Adds nginx as a service in `docker-compose.prod.yml` and writes `nginx/nginx.conf`.

Required config (non-negotiable):
- HTTP → HTTPS redirect (301), except `/.well-known/acme-challenge/` for Certbot renewal
- SSL termination with Let's Encrypt certs at `/etc/letsencrypt/live/{domain}/`
- `proxy_read_timeout 86400` — **critical**: NiceGUI WebSocket silently disconnects
  at the default 60s timeout without this
- `proxy_buffering off` — required for NiceGUI SSE fallback and any streaming responses
- WebSocket upgrade headers: `Upgrade`, `Connection: upgrade`
- `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto` headers

Security:
- `location /metrics { deny all; return 403; }` — Prometheus scrape endpoint must
  not be publicly accessible
- Monitoring dashboards proxied at internal paths with HTTP basic auth:
  `/grafana/` → Grafana, `/kibana/` → Kibana, `/prometheus/` → Prometheus
- Security headers: `X-Frame-Options DENY`, `X-Content-Type-Options nosniff`,
  `Strict-Transport-Security max-age=31536000`

**Assignee:** Adam (`adam.stockagent@gmail.com`)

**Files touched:**
- `nginx/nginx.conf` (new)
- `docker-compose.prod.yml` (add nginx service with cert volumes)

**Depends on:** 20

**Testing — done when:**
- [ ] `nginx -t` (config test) passes inside the nginx container
- [ ] `curl -I http://domain` returns 301 redirect to https
- [ ] NiceGUI chat page remains connected for > 60 seconds without disconnect
- [ ] `GET /metrics` returns 403 from outside the Docker network
- [ ] WebSocket connection established (check browser DevTools Network tab)

---

### Commit 22 — `aws-ec2-deployment`

**Commit message:** `feat: EC2 deployment scripts — systemd, SSL, swapfile, backup`

**Body:**
All scripts and config needed for a clean first deploy on a fresh EC2 instance.

`scripts/deploy.sh`:
- Install Docker + Docker Compose plugin (not v1)
- Clone repository to `/opt/rag-from-scratch`
- `.env.prod` validation guard: `grep JWT_SECRET .env.prod || (echo "FATAL: JWT_SECRET missing" && exit 1)`
- `docker compose -f docker-compose.prod.yml build`
- `docker compose -f docker-compose.prod.yml up -d`
- Ollama model pre-pull: `docker exec rag-ollama ollama pull gemma3:4b`
- Run Certbot initial cert acquisition

`systemd/rag-app.service`:
- `After=docker.service`, `Requires=docker.service`
- `ExecStart` runs `docker compose -f docker-compose.prod.yml up -d`
- `ExecStop` runs `docker compose -f docker-compose.prod.yml down`
- Ensures stack restarts after EC2 reboot

`scripts/setup-swap.sh`:
- Creates 4 GB swapfile at `/swapfile`
- Cheap insurance against OOM kills during Ollama model loading spikes

`scripts/backup.sh`:
- Tarballs `data/app_users.db` (SQLite) and `chroma_data` Docker volume to S3
- Intended to run via daily cron: `0 3 * * * /opt/rag-from-scratch/scripts/backup.sh`
- S3 bucket and IAM role documented in script header

`scripts/health-check.sh`:
- Hits `https://{domain}/api/health`
- Returns 0 on success, 1 on failure

Target EC2 instance: **t3.xlarge** (4 vCPU, 16 GB RAM) with 32 GB gp3 EBS volume.
Rationale: Ollama (gemma3:4b) needs ~3.5 GB RAM, ELK stack needs ~2 GB, app + ChromaDB
+ Redis need ~1 GB. t3.large (8 GB) is insufficient with monitoring running.

**Assignee:** Adam (`adam.stockagent@gmail.com`)

**Files touched:**
- `scripts/deploy.sh` (new)
- `scripts/health-check.sh` (new)
- `scripts/backup.sh` (new)
- `scripts/setup-swap.sh` (new)
- `systemd/rag-app.service` (new)

**Depends on:** 21

**Testing — done when:**
- [ ] `scripts/deploy.sh` runs on a fresh Ubuntu EC2 instance without errors
- [ ] `systemctl status rag-app` shows active after reboot
- [ ] `scripts/health-check.sh` returns 0 on a running stack
- [ ] Ollama responds with `gemma3:4b` after deploy (not on-demand pull)
- [ ] `.env.prod` missing → deploy.sh exits with FATAL message, not silently continues

---

### Commit 23 — `integration-tests`

**Commit message:** `test: full graph integration tests and edge case coverage`

**Body:**
Integration tests that exercise the full LangGraph pipeline with real profile state
transitions. These are end-to-end tests, not unit tests — they verify that commits
07–17 work correctly as a system.

Test scenarios:
- Fresh user (no profile): graph runs, assessment runs, profile created with first scores
- Return user (existing profile): graph runs, assessment merges delta into existing scores
- Assessment failure: graph takes fallback edge, profile not updated, answer still returned
- Anonymous user (`user_id=None`): graph runs, no profile writes, no error
- Empty knowledge base (no docs): graph returns graceful "no information" answer

**Assignee:** Rex + Nova (coordinate — Rex owns profile assertions, Nova owns graph assertions)

**Files touched:**
- `tests/test_integration.py` (new)

**Depends on:** 17 (all features complete)

**Testing — done when:**
- [ ] All 5 test scenarios pass
- [ ] Tests do not require a live OpenAI key (Ollama or stubbed provider)
- [ ] Profile state in SQLite is verifiably correct after each scenario

---

### Commit 24 — `documentation`

**Commit message:** `docs: README, architecture overview, getting started guide`

**Body:**
Complete documentation pass for the portfolio project.

`README.md`:
- Project description and north star
- Tech stack overview with reasoning
- Architecture diagram (ASCII or Mermaid)
- How to run locally (`docker compose up`)
- How to run with monitoring stack (`docker compose --profile monitoring up`)
- Environment variables (reference `.env.example`)

`GETTING_STARTED.md` (update existing file):
- Step-by-step local setup
- How to create an account and test the adaptive agent
- How to inspect your profile progression

`docs/API_REFERENCE.md`:
- All endpoints: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`,
  `/api/profile/me`, `/api/chat`, `/api/ingest`, `/api/health`, `/metrics`
- Request/response schemas

**Assignee:** Ryan (`ryan.tech.writer.agent@gmail.com`)

**Files touched:**
- `README.md`
- `GETTING_STARTED.md`
- `docs/API_REFERENCE.md` (new)

**Depends on:** 23

**Testing — done when:**
- [ ] `README.md` has a working quickstart (someone with Docker can run it from scratch following the README)
- [ ] All API endpoints are documented with example request/response
- [ ] Architecture diagram reflects the actual system (LangGraph graph, profile flow, caching)

---

## Protocol Rules

1. Commits are made in the order listed. No skipping.
2. Each commit requires Team Lead approval before it is made.
3. The assignee does the work. Cross-domain touches are flagged as handoffs before the commit, not discovered after.
4. Testing gate must be fully satisfied before approval is surfaced.
5. If a commit reveals a prior commit needs changing — stop. Surface to Team Lead first.
6. `ARCHITECTURE.md`, `DECISIONS.md`, `GLOSSARY.md` are updated by Claude before every approval prompt.
7. Scope overflow is logged immediately — never silently absorbed.
8. Viktor reviews every commit. Sage reviews any commit touching auth, secrets, or external API calls.
