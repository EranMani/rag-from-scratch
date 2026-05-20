# GLOSSARY.md — RAG from Scratch

> Maintained by Claude. Domain-specific terms used in this project's code,
> commits, and agent communication are defined here.
> Last updated: 2026-05-12 (Commit 25)

---

## Project Terms

### RAG (Retrieval-Augmented Generation)
**Meaning on this project:** A technique where relevant documents are retrieved from a knowledge base and injected into an LLM prompt before generation. The LLM answers based on retrieved context rather than parametric knowledge alone. Prevents hallucination for domain-specific questions.
**Used in:** `src/rag/`, commit names, README
**Introduced in:** existing codebase

### Knowledge Base
**Meaning on this project:** The 8 curriculum topics covering the full RAG lifecycle across three learning phases. Stored in `data/knowledge_base/`, indexed into ChromaDB at startup. Each topic has an associated question bank with rubric-graded test questions used for curriculum-driven assessment.
**Distinct from:** The ChromaDB vector store (which indexes the knowledge base, but is not itself the KB).
**Used in:** `src/rag/pipeline/indexer.py`, `data/knowledge_base/`, `knowledge-base/curriculum/`
**Introduced in:** existing codebase (6 topics); expanded to 8 topics in Commit 22

### AgentState
**Meaning on this project:** The TypedDict that carries all data through the LangGraph graph for a single user turn. Key field: `messages: Annotated[list[BaseMessage], add_messages]` — the full conversation history managed by LangGraph's `add_messages` reducer. `session_id` is NOT a field — it is passed as `thread_id` in the graph config. Designed for the full Commits 07–17 arc.
**Distinct from:** A Python dict (AgentState is typed, and `messages` uses a reducer — not plain assignment).
**Used in:** `src/agents/state.py`, all node files
**Introduced in:** Commit 07

### Node (LangGraph)
**Meaning on this project:** A single step in the agent graph. A Python function that receives `AgentState`, does one thing, and returns a partial state update. Nodes in this project: `retrieve_node`, `generate_node`, `assess_node`, `update_profile_node`.
**Distinct from:** A graph edge (which defines control flow between nodes).
**Used in:** `src/agents/nodes/`
**Introduced in:** Commit 08

### User Profile
**Meaning on this project:** A per-user record in the `user_profiles` SQLite table tracking learning state: topic scores, mastery level, identified strengths and gaps, interaction count. Read by the agent before generating a response; updated after each turn.
**Distinct from:** The auth user record in the `users` table (which stores credentials only).
**Used in:** `src/app/profile/`, `src/agents/nodes/update_profile.py`
**Introduced in:** Commit 04

### Topic Score
**Meaning on this project:** A float (0.0–1.0) representing a user's demonstrated understanding of a specific knowledge base topic, computed from assessment session performance via the spaced-repetition formula. Stored as a JSON dict in `user_profiles.topic_scores`. Keys are module slugs (see below). **Important:** `null` (Python `None`) means the topic has never been assessed — it is distinct from `0.0`, which means assessed and scored zero. Unassessed topics always fail phase gate checks.
**Distinct from:** A raw LLM confidence value (topic scores are computed and smoothed, not raw); a session score (which is the per-session input to the formula, not the stored value).
**Used in:** `src/app/profile/scoring.py`, `src/agents/state.py`
**Introduced in:** Commit 14; spaced-repetition formula added in Commit 25

### Mastery Level
**Meaning on this project:** A human-readable label derived deterministically from cumulative phase gate state — not from an average of scores. Mapping: `novice` (no Phase 1 topic assessed), `beginner` (≥1 Phase 1 topic assessed but Phase 1 gate not passed), `intermediate` (Phase 1 gate passed), `advanced` (Phase 1 + Phase 2 gates passed), `expert` (Phase 1 + Phase 2 + Phase 3 gates all passed). Gates are cumulative: `expert` requires all three phases, not just Phase 3. Used to select the adaptive prompt template.
**Distinct from:** A topic score (which is per-module); mastery level is the aggregate gate state, not a score average.
**Used in:** `src/app/profile/scoring.py`, `src/agents/prompts.py`, `src/agents/state.py`
**Introduced in:** Commit 14; gate-based formula introduced in Commit 25

### TopicScoreUpdate
**Meaning on this project:** A TypedDict returned by `compute_topic_scores()` in `src/app/profile/scoring.py`. The typed interface contract between Rex's profile service and Nova's `update_profile_node`. Contains: full updated `topic_scores`, `session_history` (per-topic list of all prior session scores), `strengths`, `gaps`, and `mastery_level`.
**Distinct from:** `AssessmentOutput` (which is raw LLM output); `TopicScoreUpdate` is the computed result after applying the spaced-repetition formula to the existing profile.
**Used in:** `src/app/profile/scoring.py`, `src/agents/nodes/update_profile.py`
**Introduced in:** Commit 14; `session_history` field added in Commit 25

### Session History
**Meaning on this project:** A per-topic list of all prior session scores for a user, stored as `session_history: dict[str, list[float]]` in the `user_profiles` table (JSON column, same row as `topic_scores`). Required to compute `best_prior_session_score` for the spaced-repetition formula across sessions. Each entry in a topic's list is the `session_score` (mean of per-question scores) from one completed assessment session. Scores from sessions with fewer than 3 questions are not appended.
**Distinct from:** `session_score` (the score for a single completed session — the value appended to this list); `topic_score` (the stored mastery value, which is computed from the session history using the spaced-repetition formula).
**Used in:** `src/app/profile/db.py` (persisted), `src/app/profile/scoring.py` (read for best_prior computation), `src/agents/nodes/update_profile.py` (written via `TopicScoreUpdate`)
**Introduced in:** Commit 25

### AssessmentOutput
**Meaning on this project:** A Pydantic model returned by the LLM via `.with_structured_output()` in `assess_node`. Contains `topic_scores_delta` (sparse dict of modules assessed this turn), `identified_gaps`, and `user_level`. Validated by Pydantic before the graph uses it.
**Distinct from:** `TopicScoreUpdate` (which is the result after merging the delta into the full profile).
**Used in:** `src/agents/state.py`, `src/agents/nodes/assess.py`
**Introduced in:** Commit 07 (schema), Commit 13 (implementation)

### ChatResponse
**Meaning on this project:** A Pydantic model in `src/rag/chain.py` that defines the typed schema for the SSE `done` event payload. Fields: `answer: str` (full generated text), `user_level: str | None` (`None` means assessment did not run — not a mastery level), `assessed_topics: dict[str, float]` (topic slug → per-turn score delta). Built by `build_chat_response(state)` from the final `AgentState` after the graph run completes.
**Distinct from:** `AssessmentOutput` (which is raw LLM output during `assess_node`); `TopicScoreUpdate` (which is the merged absolute-score result after scoring).
**Used in:** `src/rag/chain.py`, `src/app/api/routes/chat.py`
**Introduced in:** Commit 18

### Module Slug
**Meaning on this project:** A snake_case identifier for a knowledge base topic, used as keys in `topic_scores`. The canonical 8-slug set (defined in `knowledge-base/curriculum/topic-slugs.json`, introduced with the replan on 2026-05-11):
- `embeddings_and_similarity` — Phase 1: Vector embeddings, cosine similarity, semantic search
- `rag_pipeline_architecture` — Phase 1: Indexing + query phases, context injection, generation loop
- `chunking_strategies` — Phase 2: Fixed vs. semantic chunking, overlap, token budgets
- `vector_databases` — Phase 2: HNSW/IVF index types, ANN tradeoffs, metadata filtering
- `retrieval_methods` — Phase 2: Sparse (BM25), dense, hybrid, reranking, MMR, HyDE
- `context_and_prompting` — Phase 2: Context window management, prompt templates, hallucination mitigation
- `evaluation_and_metrics` — Phase 3: RAGAS, faithfulness, answer relevancy, context precision/recall
- `production_patterns` — Phase 3: Caching, async pipelines, observability, cost control, failure modes
**Note:** The prior 6-slug set (`rag_fundamentals`, `langchain`, etc.) is deprecated as of the 2026-05-11 replan. Commits 24–25 migrate the application to use this 8-slug set.
**Used in:** `knowledge-base/curriculum/topic-slugs.json` (canonical source); `src/app/profile/scoring.py`, `src/agents/state.py` (updated in Commits 24–25)
**Introduced in:** Commit 07 (original 6-slug set); Commit 22 (canonical 8-slug set)

### asyncio.to_thread
**Meaning on this project:** A Python stdlib function (`asyncio.to_thread(fn, *args)`) that runs a synchronous callable in a thread pool executor and returns an awaitable. Used throughout this project to prevent blocking I/O (ChromaDB, SQLite, LLM calls) from stalling the async event loop. Called as `await asyncio.to_thread(fn, arg1, arg2)` — not wrapped in a lambda.
**Distinct from:** `asyncio.run_in_executor` (lower-level; `asyncio.to_thread` is the idiomatic modern replacement).
**Used in:** `src/app/api/routes/documents.py`, `src/app/api/routes/chat.py`, `src/app/auth/deps.py`
**Introduced in:** Commit 01 (extended from pattern already present in chat.py)

### Circuit Breaker
**Meaning on this project:** A resilience pattern that stops sending requests to a failing service. Three states: CLOSED (normal), OPEN (failing — reject immediately), HALF_OPEN (probing — allow one test request). This project has circuit breakers for ChromaDB (`chroma_cb`), OpenAI (`openai_cb`), and Redis (`redis_cb`).
**Used in:** `src/rag/resilience/circuit_breaker.py`
**Introduced in:** existing codebase

### BM25 Fallback
**Meaning on this project:** Keyword-based retrieval using the BM25 algorithm. Activated automatically when the ChromaDB circuit breaker is OPEN. Less semantically accurate than vector search but keeps the system operational.
**Distinct from:** ChromaDB semantic search (primary retrieval path).
**Used in:** `src/rag/resilience/degradation.py`, `src/rag/pipeline/retriever.py`
**Introduced in:** existing codebase

### Session Memory
**Meaning on this project:** An in-process conversation buffer per session, keyed by session_id. Stores the last N message turns. Not persisted to disk — lost on app restart. Previously injected into chain.py as a `conversation_history` string.
**Status:** Deleted in Commit 10. Replaced by LangGraph's `MemorySaver` checkpointer, which manages conversation history natively via `thread_id` in the graph config. No application code needed for history injection after Commit 10.
**Distinct from:** User Profile (which is persistent in SQLite and tracks understanding, not conversation).
**Was in:** `src/rag/memory/conversation.py` (deleted in Commit 10)
**Introduced in:** existing codebase

### add_messages (reducer)
**Meaning on this project:** A LangGraph reducer function used as `Annotated[list[BaseMessage], add_messages]` on `AgentState.messages`. When a node returns `{"messages": [new_message]}`, the reducer *appends* the new message to the existing list rather than replacing it. This is what makes multi-turn conversation work without manual list management.
**Distinct from:** A plain `list[BaseMessage]` TypedDict field (which would replace the entire list on every update).
**Used in:** `src/agents/state.py`, `langgraph.graph.message`
**Introduced in:** Commit 07

### MemorySaver (checkpointer)
**Meaning on this project:** LangGraph's built-in in-process checkpointer. When the graph is compiled with `graph.compile(checkpointer=MemorySaver())` and invoked with `config={"configurable": {"thread_id": session_id}}`, LangGraph automatically saves and restores `AgentState` (including `messages`) between turns. The conversation history is reconstructed transparently — no application code required.
**Distinct from:** `SessionMemory` (the custom in-process buffer deleted in Commit 10); `SqliteSaver`/`PostgresSaver` (disk-persistent checkpointers for multi-instance deployments).
**Used in:** `src/agents/graph.py` (Commit 10), LangGraph internals
**Introduced in:** Commit 10

### SSE (Server-Sent Events)
**Meaning on this project:** A one-way HTTP streaming protocol where the server pushes events to the client over a persistent connection. `Content-Type: text/event-stream`. Each event is a line of the form `data: <json>\n\n`. Used in this project to stream LLM tokens from `POST /api/chat` as they are generated, so the client receives tokens progressively rather than waiting for the full answer.
**Distinct from:** WebSocket (bidirectional); chunked transfer encoding (raw bytes, no event structure); HTTP/2 push (server-initiated, not response-streaming).
**Used in:** `src/app/api/routes/chat.py` (`StreamingResponse(media_type="text/event-stream")`), `src/app/ui.py` (httpx SSE consumer)
**Introduced in:** Commit 10

### CompiledStateGraph
**Meaning on this project:** The type returned by `graph.compile(checkpointer=...)` in LangGraph. A fully wired, executable graph object. In this project produced by `build_graph(checkpointer)` in `src/agents/graph.py` and stored on `app.state.rag_graph` during lifespan. Exposes `astream_events()` for async streaming invocation.
**Distinct from:** `StateGraph` (the builder object used to define nodes and edges before compilation).
**Used in:** `src/agents/graph.py`, `src/app/main.py`
**Introduced in:** Commit 10

### thread_id (graph config)
**Meaning on this project:** The key within `{"configurable": {"thread_id": value}}` passed to `graph.astream_events()`. LangGraph's checkpointer uses this value to identify which conversation thread to save and restore. In this project, `session_id` from the request is used as `thread_id`. Each unique `session_id` → independent conversation thread with its own `AgentState` history.
**Distinct from:** `session_id` in the HTTP request body (which is the source value); `user_id` from JWT (which identifies the user, not the conversation thread).
**Used in:** `src/app/api/routes/chat.py` (`config = {"configurable": {"thread_id": session_id}}`)
**Introduced in:** Commit 10

### assessment_error
**Meaning on this project:** A boolean field in `AgentState`. Set to `True` by `assess_node` when the LLM call or structured-output parsing fails during assessment. When `True`, the conditional edge `_route_after_assess` in `graph.py` routes to `update_profile_node` with empty deltas — the profile is not updated but the graph continues cleanly to END. When `False`, the normal path applies the assessment delta to the profile.
**Distinct from:** A Python exception (which is caught inside `assess_node`; `assessment_error` is the state-level signal emitted after the exception is handled).
**Used in:** `src/agents/state.py`, `src/agents/nodes/assess.py`, `src/agents/graph.py`
**Introduced in:** Commit 12

### assessed_topics (SSE schema key)
**Meaning on this project:** The key name for `topic_scores_delta` in the final SSE `done` event: `{"type": "done", "user_level": ..., "assessed_topics": {...}}`. Renamed at the serialization boundary to better reflect consumer intent (which topics were assessed this turn) rather than implementation detail (the delta values). Values are `dict[str, float]` — same structure as `topic_scores_delta` in `AgentState`.
**Distinct from:** `topic_scores_delta` (the internal `AgentState` field name — a sparse per-turn delta, not exposed directly in SSE).
**Used in:** `src/app/api/routes/chat.py` (emitted in `generate_stream()`), `tests/test_chat_route.py`
**Introduced in:** Commit 10

### PROMPT_TEMPLATES
**Meaning on this project:** A `dict[str, ChatPromptTemplate]` defined in `src/agents/prompts/rag.py` and exported from `agents.prompts`. Keys are the 5 mastery level strings (`"novice"`, `"beginner"`, `"intermediate"`, `"advanced"`, `"expert"`). Each value is a `ChatPromptTemplate` with a single `{context}` input variable. `generate_node` calls `PROMPT_TEMPLATES.get(user_level, DEFAULT_PROMPT)` to select the correct template before each LLM call.
**Distinct from:** `DEFAULT_PROMPT` (the fallback template — not in the dict); `assessment_prompt` (the assessment node's prompt in `src/agents/prompts/assessment.py`).
**Used in:** `src/agents/prompts/rag.py`, `src/agents/prompts/__init__.py` (Commit 17); `src/agents/nodes/generate.py` (Commit 18)
**Introduced in:** Commit 17

### DEFAULT_PROMPT
**Meaning on this project:** A `ChatPromptTemplate` defined in `src/agents/prompts/rag.py` that mirrors the existing inline `SystemMessage` in `generate_node`. Used as the fallback when `PROMPT_TEMPLATES.get(user_level)` returns `None` (unset or unknown mastery level). Contains the same "Answer using ONLY the provided context" constraint and RAG domain framing as the original inline message — ensures zero regression for users who haven't been assessed yet.
**Distinct from:** `PROMPT_TEMPLATES` (the mastery-level dict — `DEFAULT_PROMPT` is not a key in it); a bare string (it is a `ChatPromptTemplate` with a `{context}` variable).
**Used in:** `src/agents/prompts/rag.py`, `src/agents/prompts/__init__.py` (Commit 17)
**Introduced in:** Commit 17

### WAL Mode
**Meaning on this project:** SQLite Write-Ahead Logging journal mode. Enables concurrent reads during a write operation. Enabled via `PRAGMA journal_mode=WAL` in `_connect()`. Required because the LangGraph agent thread writes profile updates while FastAPI request threads read user data concurrently.
**Used in:** `src/app/auth/db.py`, `src/app/profile/db.py`
**Introduced in:** Commit 04

---

## Agent / Protocol Terms

### Commit
**Meaning on this project:** A single, scoped unit of work assigned to one agent. One concern, one owner. Cannot span agent domains without an explicit cross-domain note in the spec.
**Used in:** `commit-protocol.md`, all worklogs

### Handoff
**Meaning on this project:** A structured note from one agent to another, routed through Claude, carrying context the receiving agent needs before starting work. Currently open: Commit 05 → Nova (Commit 15) re: `last_activity_at` must be set on every profile update.
**Used in:** `project-state.json open_handoffs`

### Hard Block
**Meaning on this project:** A Viktor finding so severe it bypasses the normal quality gate and surfaces directly to the Team Lead before any commit is made. Two Hard Blocks were raised during /init: graph replacement with zero tests (resolved by Commit 11), and untyped cross-agent interface (resolved by Commit 14's typed interface requirement).
**Used in:** `ORCHESTRATION.md`, Viktor reviews

### Phase Gate
**Meaning on this project:** A score threshold that all required topics in a phase must meet before the learner can access the next phase's content. Phase 1 and Phase 3 gates require each topic ≥ a per-topic minimum. Phase 2 gate additionally requires the mean of all four topics ≥ 0.75 (because Phase 2 topics are interdependent). Unassessed topics (`null` score) always fail a gate check.
**Used in:** `knowledge-base/curriculum/gates.md` (definition); `src/agents/` (Nova implements), `src/app/profile/` (Rex implements) — Commits 24–25
**Introduced in:** Commit 22

### Topic Score (curriculum-based)
**Meaning on this project:** Under the curriculum redesign (Commit 22+), topic scores are computed from test performance, not chat interaction counts. Formula: `topic_score = 0.7 × current_session_score + 0.3 × best_prior_session_score`. Session scores are the mean of per-question scores (1.0 correct / 0.5 partial / 0.0 incorrect). Sessions with fewer than 3 questions produce no score update. Unassessed topics have score `null`, not `0.0`.
**Distinct from:** The pre-replan scoring model (which inferred mastery from question content, not answers — deprecated as of the 2026-05-11 replan).
**Used in:** `knowledge-base/curriculum/gates.md` (formula); implemented by Rex in Commit 25
**Introduced in:** Commit 22 (formula defined); prior definition active through Commit 21

### Faithfulness (RAGAS)
**Meaning on this project:** A RAGAS evaluation metric that measures the fraction of factual claims in a generated answer that are attributable to the retrieved context. A faithful answer makes no claims beyond what the retrieved documents support. Low faithfulness indicates hallucination.
**Used in:** `knowledge-base/curriculum/questions/evaluation_and_metrics.md` (tested in curriculum); future evaluation pipeline
**Introduced in:** Commit 22 (curriculum definition)

### Context Precision (RAGAS)
**Meaning on this project:** A RAGAS evaluation metric that measures the fraction of retrieved chunks that are actually relevant to answering the question. High context precision means the retrieval system surfaced mostly useful documents. Low precision indicates the retriever is returning noise along with relevant chunks.
**Used in:** `knowledge-base/curriculum/questions/evaluation_and_metrics.md`
**Introduced in:** Commit 22 (curriculum definition)

### Context Recall (RAGAS)
**Meaning on this project:** A RAGAS evaluation metric that measures the fraction of the information needed to answer the question that is present in the retrieved chunks. High context recall means the retrieval system found all the relevant material. Low recall means key information was missed during retrieval.
**Used in:** `knowledge-base/curriculum/questions/evaluation_and_metrics.md`
**Introduced in:** Commit 22 (curriculum definition)

### Assessment Session
**Meaning on this project:** A structured sequence of test questions (minimum 3) administered by the agent for a single topic. An assessment session produces a `session_score` (mean of per-question scores) which updates the `topic_score` via the spaced repetition formula. Sessions with fewer than 3 questions are discarded without updating the score. Assessment sessions are transparent — the agent announces when one is starting.
**Distinct from:** A content turn (a regular question-and-answer exchange where the user asks about RAG concepts); an incomplete session (fewer than 3 questions, no score update).
**Used in:** `docs/scoring-model.md` (behavioral spec); implemented by Nova in Commit 24
**Introduced in:** Commit 23 (behavioral definition)

### Readiness Score Threshold
**Meaning on this project:** The topic score value (0.60) at which the agent switches from content delivery to assessment mode for a given topic. A topic at 0.60 is above chance-correct territory and below the phase gate minimum (0.70 or 0.75), making it the ideal moment to test. The second trigger for assessment is 5 content turns with no prior score.
**Distinct from:** Phase gate threshold (the score required to pass a gate and advance to the next phase); a mastery threshold (the gate minimum).
**Used in:** `docs/scoring-model.md` (Section 9 machine-readable reference); implemented by Nova in Commit 24
**Introduced in:** Commit 23

### Assessment Deferral
**Meaning on this project:** A one-time postponement of an assessment session offered to the user when the readiness trigger fires. The user may defer once per topic per session; a second deferral attempt in the same session is not honored and the agent delivers the first question anyway. Deferral state resets at the start of each new conversation session.
**Distinct from:** Declining assessment entirely (not possible); a session ending before assessment (which simply means the trigger fires again next time).
**Used in:** `docs/scoring-model.md` (Section 6.2); implemented by Nova in Commit 24
**Introduced in:** Commit 23

### EvaluationOutput
**Meaning on this project:** A Pydantic model introduced in Commit 24 and used exclusively by `assess_node` in evaluation mode. Contains `verdict: str` (`"correct"` / `"partial"` / `"incorrect"`), `confidence: float` (0.0–1.0), `identified_gaps: list[str]`, and `user_level: str`. Used with `.with_structured_output(EvaluationOutput)` to get a structured LLM evaluation of the user's test answer against a curriculum rubric.
**Distinct from:** `AssessmentOutput` (the prior schema — still defined in `state.py` but no longer used in `assess_node` after Commit 24; Rex's Commit 25 may retain or remove it). `EvaluationOutput` returns a verdict per test question; `AssessmentOutput` returned delta scores per inferred topic.
**Used in:** `src/agents/state.py`, `src/agents/nodes/assess.py`
**Introduced in:** Commit 24

### test_mode / pending_test_question / pending_test_slug / test_answer_score
**Meaning on this project:** Four new `AgentState` fields added in Commit 24 to support curriculum-driven test administration:
- `test_mode: bool` — `True` when `assess_node` has selected and delivered a curriculum question; `False` otherwise.
- `pending_test_question: str | None` — the curriculum test question text currently awaiting the user's answer. `None` when no test is in progress.
- `pending_test_slug: str | None` — the topic slug of the pending test question; must be in `VALID_MODULE_SLUGS`. `None` when no test is in progress.
- `test_answer_score: float | None` — the score assigned to the most recently evaluated test answer: `1.0` (correct), `0.5` (partial), `0.0` (incorrect). `None` on test-mode turns (no answer yet) and on fallback.
**Used in:** `src/agents/state.py`, `src/agents/nodes/assess.py`
**Introduced in:** Commit 24

### MCQ (Multiple-Choice Question)
**Meaning on this project:** A curriculum question format with exactly 4 options (A–D), a single unambiguous correct answer, and an explanation. Used exclusively as a phase-gate advancement instrument — binary-scored by answer-key comparison (no LLM evaluator required). Scores are 1.0 (correct) or 0.0 (incorrect); no partial credit. MCQ questions live in `knowledge-base/curriculum/questions/mcq/[slug].md` (5 per topic, 2 beginner + 2 intermediate + 1 advanced).
**Distinct from:** Open-ended questions (which use rubric-based LLM evaluation with correct/partial/incorrect verdicts and are the primary in-session learning format); phase gate threshold (the score a topic must reach to advance, not the question format used to measure it).
**Used in:** `knowledge-base/curriculum/questions/mcq/`, `knowledge-base/curriculum/mcq-format.md`, `knowledge-base/curriculum/gates.md`
**Introduced in:** Commit 33

### Onboarding Wizard
**Meaning on this project:** The 3-step `ui.dialog()` shown to first-time users on their first visit to the chat page. Step 1: self-report level. Step 2: 3 diagnostic MCQs. Step 3: placement confirmation. Fully skippable — skipping places the user at `novice` level without completing Step 3. Triggered when `GET /api/onboarding/status` returns `{"needed": true}` (i.e., the user has no topic scores yet).
**Distinct from:** The regular chat assessment loop (ongoing per-session MCQ questions that update topic scores after placement).
**Used in:** `src/app/ui.py` (dialog + handlers), `src/app/api/routes/onboarding.py`
**Introduced in:** Commit 38

### Phase Progress Panel
**Meaning on this project:** The sidebar panel in the chat page that shows the user's current phase label, the topics in that phase with color-coded scores, and the advancement threshold message. Replaces the old module-by-module progress bar list. Refreshes after every chat turn. Derived from `mastery_level` and `topic_scores` in the user's profile.
**Distinct from:** The mastery chip (single badge showing level) and the interaction count (session counter) — those remain above the phase panel.
**Used in:** `src/app/ui.py` (`profile_panel()` refreshable), `_PHASE_LABELS`, `_PHASE_TOPICS`, `_ADVANCE_MSG` module-level dicts
**Introduced in:** Commit 38

*Last updated: 2026-05-20 — Commit 38 complete (onboarding wizard + phase progress panel terms added)*
