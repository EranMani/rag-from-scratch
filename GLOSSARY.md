# GLOSSARY.md — RAG from Scratch

> Maintained by Claude. Domain-specific terms used in this project's code,
> commits, and agent communication are defined here.
> Last updated: 2026-05-08

---

## Project Terms

### RAG (Retrieval-Augmented Generation)
**Meaning on this project:** A technique where relevant documents are retrieved from a knowledge base and injected into an LLM prompt before generation. The LLM answers based on retrieved context rather than parametric knowledge alone. Prevents hallucination for domain-specific questions.
**Used in:** `src/rag/`, commit names, README
**Introduced in:** existing codebase

### Knowledge Base
**Meaning on this project:** The 6 Markdown modules covering RAG architecture, vector databases, LangChain, chunking, retrieval methods, and production patterns. Stored in `data/knowledge_base/`, indexed into ChromaDB at startup.
**Distinct from:** The ChromaDB vector store (which indexes the knowledge base, but is not itself the KB).
**Used in:** `src/rag/pipeline/indexer.py`, `data/knowledge_base/`
**Introduced in:** existing codebase

### AgentState
**Meaning on this project:** The TypedDict that carries all data through the LangGraph graph for a single user turn. Contains the question, conversation history, retrieved docs, generated answer, assessment output, and profile update delta. Designed for the full arc in Commit 07.
**Distinct from:** A Python dict (AgentState is typed and compiled by LangGraph).
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
**Meaning on this project:** A float (0.0–1.0) representing a user's demonstrated understanding of a specific knowledge base module. Stored as a JSON dict in `user_profiles.topic_scores`. Keys are module slugs (see below).
**Distinct from:** A raw LLM confidence value (topic scores are computed and smoothed, not raw).
**Used in:** `src/app/profile/scoring.py`, `src/agents/state.py`
**Introduced in:** Commit 14

### Mastery Level
**Meaning on this project:** A human-readable label derived deterministically from the average of all topic scores: `novice` (< 0.2), `beginner` (0.2–0.4), `intermediate` (0.4–0.6), `advanced` (0.6–0.8), `expert` (≥ 0.8). Used to select the adaptive prompt template.
**Distinct from:** A topic score (which is per-module); mastery level is the aggregate.
**Used in:** `src/app/profile/scoring.py`, `src/agents/prompts.py`, `src/agents/state.py`
**Introduced in:** Commit 14

### TopicScoreUpdate
**Meaning on this project:** A TypedDict returned by `compute_topic_scores()` in `src/app/profile/scoring.py`. The typed interface contract between Rex's profile service and Nova's `update_profile_node`. Contains: full updated `topic_scores`, `strengths`, `gaps`, and `mastery_level`.
**Distinct from:** `AssessmentOutput` (which is raw LLM output); `TopicScoreUpdate` is the computed result after merging the delta into existing scores.
**Used in:** `src/app/profile/scoring.py`, `src/agents/nodes/update_profile.py`
**Introduced in:** Commit 14

### AssessmentOutput
**Meaning on this project:** A Pydantic model returned by the LLM via `.with_structured_output()` in `assess_node`. Contains `topic_scores_delta` (sparse dict of modules assessed this turn), `identified_gaps`, and `user_level`. Validated by Pydantic before the graph uses it.
**Distinct from:** `TopicScoreUpdate` (which is the result after merging the delta into the full profile).
**Used in:** `src/agents/state.py`, `src/agents/nodes/assess.py`
**Introduced in:** Commit 07 (schema), Commit 13 (implementation)

### Module Slug
**Meaning on this project:** A snake_case identifier for a knowledge base module, used as keys in `topic_scores`. The canonical set:
- `rag_fundamentals` — Module 1: Information Retrieval
- `vector_databases` — Module 2: Vector Databases
- `retrieval_methods` — Module 3: RAG Architecture
- `chunking_strategies` — Module 4: Chunking
- `langchain` — Module 5: LangChain and Agents
- `production_patterns` — Module 6: Production RAG
**Used in:** `src/app/profile/scoring.py`, `src/agents/state.py`
**Introduced in:** Commit 07

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
**Meaning on this project:** An in-process conversation buffer per session, keyed by session_id. Stores the last N message turns. Not persisted to disk — lost on app restart. Injected into `AgentState` as `conversation_history` before each graph invocation.
**Distinct from:** User Profile (which is persistent in SQLite and tracks understanding, not conversation).
**Used in:** `src/rag/memory/conversation.py`
**Introduced in:** existing codebase

### WAL Mode
**Meaning on this project:** SQLite Write-Ahead Logging journal mode. Enables concurrent reads during a write operation. Enabled via `PRAGMA journal_mode=WAL` in `_connect()`. Required because the LangGraph agent thread writes profile updates while FastAPI request threads read user data concurrently.
**Used in:** `src/app/auth/db.py`
**Introduced in:** Commit 04

---

## Agent / Protocol Terms

### Commit
**Meaning on this project:** A single, scoped unit of work assigned to one agent. One concern, one owner. Cannot span agent domains without an explicit cross-domain note in the spec.
**Used in:** `commit-protocol.md`, all worklogs

### Handoff
**Meaning on this project:** A structured note from one agent to another, routed through Claude, carrying context the receiving agent needs before starting work. Currently open: Commit 03 → Nova (Commit 10) re: conversation history threading.
**Used in:** `project-state.json open_handoffs`

### Hard Block
**Meaning on this project:** A Viktor finding so severe it bypasses the normal quality gate and surfaces directly to the Team Lead before any commit is made. Two Hard Blocks were raised during /init: graph replacement with zero tests (resolved by Commit 11), and untyped cross-agent interface (resolved by Commit 14's typed interface requirement).
**Used in:** `ORCHESTRATION.md`, Viktor reviews

*Last updated: 2026-05-08 — /init complete, pre-build*
