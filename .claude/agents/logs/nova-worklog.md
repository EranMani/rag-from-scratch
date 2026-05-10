# Nova — Worklog
# Project: rag-from-scratch
# Stack: Python 3.11+, FastAPI, LangGraph, LangChain, ChromaDB, SQLite

---

## Current State
*Last updated: Commit 15 `profile-update-node` · 2026-05-10*

**Last completed:** Commit 15 `profile-update-node` ✅
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- Commit 18 (UI profile panel): `update_profile_node` sets `last_activity_at` on every
  successful assessment turn using `datetime.now(timezone.utc).isoformat()`. The field is
  guaranteed to be a valid ISO 8601 UTC string after any authenticated turn with no
  assessment error.
- Commit 18: `interaction_count` is incremented by 1 per successful turn and persisted
  via `update_profile()`. The profile panel can read it directly.
- Downstream commits: `update_profile_node` is now in `src/agents/nodes/update_profile.py`
  (not a stub in `graph.py`). `graph.py` imports it as
  `from agents.nodes.update_profile import update_profile_node`.

**Open Handoffs — Inbound (consumed this session):**
- Commit 05 Mira handoff (last_activity_at): CONSUMED. `last_activity_at` is set on every
  successful turn.
- Commit 14 handoff (compute_topic_scores import path, no json.loads): CONSUMED. Importing
  as `from app.profile.scoring import compute_topic_scores, TopicScoreUpdate`; profile dict
  passed directly without json.loads.

**Key Interfaces I Own (for teammates):**
- `src/agents/graph.py` — `build_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph`
  Factory function. Called once in lifespan; result stored on `app.state.rag_graph`.
  `recursion_limit=10` baked into compiled graph config.
- `src/app/api/routes/chat.py` — `POST /api/chat` returns `text/event-stream`.
  SSE events: `{"type":"token","content":"..."}` and `{"type":"done","user_level":"...","assessed_topics":{}}`.
  Graph accessed via `request.app.state.rag_graph` — never from module-level import.
- `src/app/api/routes/chat.py` — `get_user_level(user_id: str | None) -> Literal[...]`
  Synchronous profile DB read; call via `asyncio.to_thread`. Returns 'novice' for anonymous.
- `src/agents/state.py` — `AgentState` TypedDict, `AssessmentOutput` Pydantic model,
  `VALID_MODULE_SLUGS` frozenset. Import from here for all graph nodes.
- `src/agents/__init__.py` — empty package marker
- `src/agents/nodes/__init__.py` — empty package marker
- `src/agents/nodes/retrieve.py` — `retrieve_node(state: AgentState) -> dict`
  Returns `{"docs": list[Document], "retrieval_source": str}` only.
- `src/agents/nodes/generate.py` — `async generate_node(state: AgentState) -> dict`
  Returns `{"messages": [AIMessage], "answer": str}` only.
- `AgentState` fields summary:
    - `messages: Annotated[list[BaseMessage], add_messages]` — append-only via reducer
    - `question: str` — convenience copy of messages[-1].content
    - `user_id: str | None` — from JWT; None = anonymous
    - `docs: list[Document]` — retrieved Documents (langchain_core.documents.Document)
    - `retrieval_source: str` — 'chroma' or 'bm25'
    - `answer: str` — complete generated answer
    - `user_level: Literal["novice","beginner","intermediate","advanced","expert"]`
    - `topic_scores_delta: dict[str, float]` — sparse per-turn assessed delta
    - `identified_gaps: list[str]` — low-understanding module slugs
    - `assessment_error: bool` — fallback edge trigger
    - `trace_id: str`, `latency_ms: int` — observability
    - `cache_hit: Literal["hit","miss","bypass"]` — cache status (contract for Commit 10+)
- `session_id` is NOT in state. Passed as thread_id in config.
- `AssessmentOutput`: `topic_scores_delta`, `identified_gaps`, `user_level` — all required.
  Use with `.with_structured_output(AssessmentOutput)` in assess_node.

**Decisions Other Agents Must Know:**
- `from __future__ import annotations` is used in `state.py` to enable forward references
  in TypedDict. This is safe with `get_type_hints(AgentState, include_extras=True)` —
  the `include_extras=True` is required to preserve the `Annotated` metadata.
- `langgraph>=0.2.0` and `langchain-core>=0.3.0` are now declared in `pyproject.toml`.
  They were installed but undeclared before Commit 07.

**Decisions Other Agents Must Know:**
- `from __future__ import annotations` is used in `state.py` to enable forward references
  in TypedDict. This is safe with `get_type_hints(AgentState, include_extras=True)` —
  the `include_extras=True` is required to preserve the `Annotated` metadata.
- `langgraph>=0.2.0` and `langchain-core>=0.3.0` are now declared in `pyproject.toml`.
  They were installed but undeclared before Commit 07.
- `chain.py` is kept as a thin placeholder (not deleted) after Commit 10. The decision
  log is in the file's module docstring. Deleting would break any future pipeline-level
  import paths; placeholder cost is zero.
- `tests/test_conversation_memory.py` was deleted along with `conversation.py`. The tests
  covered `SessionMemory` which no longer exists. Retaining a test file for a deleted
  class would fail the test suite.
- `app/ui.py` was updated to replace the `run_rag_pipeline` call with an internal
  httpx SSE stream to `POST /api/chat`. This was a discovered scope gap — the spec did
  not list `ui.py` in files touched, but it imported `run_rag_pipeline` which was removed.

**Scope Overflows Pre-Built:**
- (none)

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| 01 | Commit 07 `langgraph-state-schema` | ✅ Done | Used `Annotated[list[BaseMessage], add_messages]` with `from __future__ import annotations`; `session_id` excluded from state per architecture decision |
| 02 | Commit 08 `langgraph-retrieve-node` | ✅ Done | `retrieval_source` derived from CB state before/after call, not from return value — retrieve() doesn't expose which path ran |
| 03 | Commit 09 `langgraph-generate-node` | ✅ Done | Node is async (`ainvoke`) for streaming-readiness; `question` not read — current question is last HumanMessage in messages; LLM via get_provider().get_llm() |
| 04 | Commit 10 gate-fix | ✅ Done | Quinn: 4 chat route tests added; Sage: `nicegui_storage_secret` extracted to config — patched settings singleton directly in test 4 to avoid lru_cache re-evaluation |
| 05 | Commit 11 `langgraph-graph-smoke-test` | ✅ Done | Two distinct mock layers: retrieve_node patched at agents.graph; get_provider patched at agents.nodes.generate import site. Threading test uses shared MemorySaver + capture stub at generate_node level. |
| 06 | Commit 12 `langgraph-assessment-scaffold` | ✅ Done | Conditional edge: both error and non-error paths route to update_profile — structural branching now explicit via add_conditional_edges; update_profile_node is a passthrough stub declared in graph.py, not a separate file. |
| 07 | Commit 13 `langgraph-assessment-llm` | ✅ Done | Prompt in dedicated file; assessment_prompt.__or__ mock pattern avoids RunnableSequence internals in tests; user_level NOT written back to state. |
| 08 | Commit 15 `profile-update-node` | ✅ Done | Synchronous node in its own file; two fast-exit paths (None user_id, assessment_error=True); identified_gaps state field maps to `gaps` DB column; no json.loads on topic_scores. |

---

## Session 01 — Commit 07: `langgraph-state-schema`

**Date:** 2026-05-09
**Status:** ✅ Done

### Task Brief

Define the full LangGraph state schema (`AgentState` TypedDict and `AssessmentOutput`
Pydantic model) for the Phase 4 adaptive RAG agent. The schema must cover the complete
Commit 07–17 arc — retroactive additions cascade through the compiled graph.

### AI Problem Being Solved

The core design problem: how to manage conversational context across turns in a
LangGraph graph. The naive approach — `conversation_history: str` — works for
single-session use but breaks with LangGraph's checkpointer because it conflates
two concerns: message transport (what came in this turn) and memory persistence
(prior turns). Separating them via `messages: Annotated[list[BaseMessage], add_messages]`
plus checkpointer-backed `thread_id` is the production-grade pattern.

The second design problem: where `session_id` lives. Putting it in `AgentState` is
tempting — it's useful for logging — but it creates a conflict with LangGraph's
`MemorySaver` checkpointer, which uses `thread_id` from the config to partition
checkpoint namespaces. If `session_id` also lives in state, there are now two
sources of truth for the same concept. The spec is explicit: `session_id` goes in
config only.

### Prompt / Tool Design Decisions

`AssessmentOutput` is a Pydantic model rather than a TypedDict because it is the
output schema for a structured LLM call via `.with_structured_output()`. LangChain's
structured output tooling expects a Pydantic `BaseModel`, not a TypedDict. The three
fields (`topic_scores_delta`, `identified_gaps`, `user_level`) are all required — no
Optional — so a missing field produces a clean `ValidationError` rather than a silent None.

`VALID_MODULE_SLUGS` is defined as a module-level `frozenset` in `state.py` rather
than a validator on `AssessmentOutput` by design: the spec does not constrain keys
at the Pydantic level (the LLM may occasionally produce a novel key and the system
handles it gracefully), but the constant needs to be importable by assess_node for
prompt construction.

### What Was Considered and Ruled Out

1. `conversation_history: str` field — rejected. This was Rex's existing pattern in
   `chain.py`, but it doesn't compose with the checkpointer. With `add_messages`,
   prior turns are reconstructed automatically at graph entry via `thread_id`.

2. `session_id: str` in `AgentState` — rejected per spec. It belongs in config.

3. Using `TypedDict` for `AssessmentOutput` — rejected. LangChain's
   `.with_structured_output()` requires a Pydantic model for JSON schema generation
   and field validation. TypedDict has no runtime validation.

4. Making `assessment_error` an `Optional[str]` (error message) instead of `bool` —
   considered. Decided against it: the fallback edge only needs a boolean signal.
   Error detail belongs in structured logs (via `trace_id`), not in graph state.

### Dependency Finding

`langgraph` and `langchain-core` were installed in the environment but not declared
in `pyproject.toml`. Added both with floor versions that match the installed environment
(`langgraph>=0.2.0`, `langchain-core>=0.3.0`). This is a correctness fix — the project
could not be reproduced from `pyproject.toml` alone before this commit.

### Test Results

All 7 spec gates passed:
- GATE 1: `from agents.state import AgentState, AssessmentOutput` imports without error
- GATE 2: All required fields present in `get_type_hints(AgentState, include_extras=True)`
- GATE 3: `messages` hint is `Annotated[list[BaseMessage], add_messages]` with
  `__metadata__[0] is add_messages` confirmed
- GATE 4: `session_id` absent from `AgentState`
- GATE 5: `add_messages([HumanMessage("hello")]) then add_messages([AIMessage("world")])`
  produces a 2-item list — accumulation confirmed
- GATE 6: `AssessmentOutput` validates correctly with a sample dict
- GATE 7: `AssessmentOutput` raises `ValidationError` on missing required fields (2 errors)

Full existing suite: 53 tests passed, 0 failures.

### Approach

The initial question was whether `from __future__ import annotations` would break
`get_type_hints` for the `Annotated` metadata check. In Python 3.11 with
`from __future__ import annotations`, all annotations are stored as strings at class
definition time. `get_type_hints()` resolves them — but only with `include_extras=True`
does it preserve the `Annotated` wrapper rather than stripping it to the bare type.
This is the non-obvious part: without `include_extras=True`, `hints['messages']` would
return `list[BaseMessage]` and the Gate 3 assertions would fail. The fix is to always
call `get_type_hints(AgentState, include_extras=True)` in any downstream introspection
code — not the default. This is documented in the worklog rather than in code comments
because it affects callers in future commits, not the schema file itself.

---

### Viktor Fixes Applied (2026-05-09)

**Fix 1 — `cache_hit` type hardened to `Literal["hit", "miss", "bypass"]`**
Changed from `str`. chain.py's legacy values are documented in the field docstring
as a known gap to be resolved in Commit 10. The Literal documents the contract, not
the current implementation state.

**Fix 2 — `docs` type hardened to `list[Document]`**
Added `from langchain_core.documents import Document`. This catches the wrong-type
write at the type-checker level before it reaches generate_node.

**Fix 3 — `user_level` hardened to `Literal[...]` in both `AgentState` and `AssessmentOutput`**
The same 5-value Literal is used in both places. In `AssessmentOutput` this enforces
the constraint at Pydantic parse time — no additional validator needed.

**Fix 4 — `topic_scores_delta` and `identified_gaps` slug validation added to `AssessmentOutput`**
Two `@field_validator` methods (`mode="before"`) silently drop unknown keys/values
against `VALID_MODULE_SLUGS` and log a warning via `logger.warning()`. Silent drop
(not raise) is the stated policy so a single hallucinated slug does not discard the
entire assessment result. Added `import logging` and module-level `logger` instance.
Added `field_validator` to the `pydantic` import.

**Fix 5 — `tests/test_agent_state.py` added**
16 tests: 7 original spec gates + 3 Viktor additions (invalid user_level, unknown slug
drop, valid slug preserve) + additional coverage for all missing-field cases.
Final test count: 69 passed (53 prior + 16 new), 0 failures.

**Judgment calls:**
- Two separate `@field_validator` methods (one per field) rather than a single combined
  validator. The combined form (`@field_validator("topic_scores_delta", "identified_gaps")`)
  was considered, but the two fields have different types (dict vs list), requiring a
  type branch inside the validator. Separate validators are cleaner and easier to read.
- `frozenset` membership test is O(1) and the set is small — no performance concern.
- The `logger` instance is module-level (not class-level) because `AssessmentOutput`
  is a Pydantic model and module-level logging is the standard pattern there.

---

## Session 02 — Commit 08: `langgraph-retrieve-node`

**Date:** 2026-05-09
**Status:** ✅ Done

### Task Brief

Wrap the existing `retrieve()` function from `src/rag/pipeline/retriever.py` as a
LangGraph node. Read `question` from `AgentState`, call the retriever, write `docs`
and `retrieval_source` back into state. `retrieval_source` must be `"chroma"` or
`"bm25"` on every invocation.

### AI Problem Being Solved

The node had no AI logic — it's a pure data-flow wrapper. The non-trivial engineering
problem was: **how to determine which retrieval path ran** given that `retrieve()`
returns only `list[Document]` with no metadata about which branch executed.

### Tool / Node Design Decisions

The `retrieval_source` label is derived by inspecting `chroma_cb.is_available()`
before and after the `retrieve()` call:

- Before available, after available → Chroma succeeded → `"chroma"`
- Before NOT available → BM25 ran directly → `"bm25"`
- Before available, after NOT available → Chroma attempted, CB tripped during call,
  BM25 fallback activated inside `retrieve()` → `"bm25"`

This is accurate for all three circuit breaker scenarios without duplicating any
retrieval logic. The node owns only the source-label derivation; `retrieve()` owns
all actual retrieval.

The node function signature follows the LangGraph node contract exactly:
`def retrieve_node(state: AgentState) -> dict`. Return dict contains only the keys
being written (`docs`, `retrieval_source`) — not the full state.

### What Was Considered and Ruled Out

1. **Inspect return value metadata** — `retrieve()` returns plain `list[Document]`.
   There is no metadata on the Document objects that reliably identifies the retrieval
   path (both Chroma and BM25 return the same `Document` type). Ruled out.

2. **Duplicate the routing logic** in the node — check `chroma_cb.is_available()`,
   call either `get_vectorstore().similarity_search()` or `_bm25_fallback.get_relevant_documents()`
   directly. Ruled out: duplicates `retriever.py` logic and creates drift risk if
   the CB logic is updated later.

3. **Extend `retrieve()` to return a tuple `(docs, source)`** — cleanest interface,
   but outside node's domain. `retriever.py` is the backend engineer's domain per
   AGENTS.md. Ruled out as a domain boundary violation.

4. **Read `chroma_cb.state` directly** (compare to `CircuitState.OPEN`) rather than
   `is_available()` — functionally equivalent but `is_available()` is the public API
   for this check and already handles HALF_OPEN correctly.

### Failure Modes Considered

- `retrieve()` raises an exception — currently propagates up. The spec does not
  require exception handling in the node; circuit breaking is handled inside
  `retrieve()` already. No additional try/except added.
- `_bm25_fallback` is `None` (not initialized at startup) — `retrieve()` logs an
  error and returns `[]`. The node handles this cleanly: `docs=[]`, source determined
  by CB state logic.
- Empty question string — forwarded to `retrieve()` verbatim. BM25 handles empty
  queries by returning 0-score matches; Chroma handles it with an empty embedding.
  Both return `[]` gracefully. Spec gate 3 confirmed.

### Test Results

11 new tests, all passed:
- Gate 1 (3 tests): docs populated, question forwarded, return dict has only 2 keys
- Gate 2 (4 tests): chroma path, bm25 direct path, bm25 tripped path, source is str
- Gate 3 (4 tests): empty question, empty string forwarded, source still set, no raise

Full suite: 80 passed (69 prior + 11 new), 0 failures.

### Approach

The initial question was whether the `retrieval_source` detection belonged in the
node or in `retrieve()`. The spec says to set it "based on which path was taken
(readable from circuit breaker state)" — this explicitly points at the CB as the
detection mechanism rather than modifying `retrieve()`. Reading `chroma_cb.is_available()`
before and after the call is the minimal, non-invasive implementation of that spec
instruction. The before/after comparison is necessary (not just before) because
`chroma_cb.is_available()` before the call being True doesn't guarantee Chroma
succeeded — it may fail mid-call and the CB may trip during the call. The after-check
catches that case and correctly labels it `"bm25"`.

---

## Session 03 — Commit 09: `langgraph-generate-node`

**Date:** 2026-05-09
**Status:** ✅ Done

### Task Brief

Build `generate_node` — the LangGraph async generation node that takes retrieved docs
and the full message history, calls the LLM via `get_provider().get_llm()`, and
returns `{"messages": [AIMessage], "answer": str}`.

### AI Problem Being Solved

The generation node sits at the intersection of two LangGraph concerns: (1) proper
message accumulation via the `add_messages` reducer, and (2) streaming readiness.
The naive approach — calling `llm.invoke()` synchronously — would work for correctness
but break streaming. LangGraph's `astream_events()` mechanism emits `on_chat_model_stream`
token events only when the underlying LLM call is `async`. Using `await llm.ainvoke()`
here means the streaming path in Commit 10 requires zero changes to this node.

The second concern is `question` vs `messages`. The question field exists as a
convenience for `retrieve_node` (which needs a bare string for similarity search). In
`generate_node`, the question is already embedded as the last `HumanMessage` in
`state["messages"]`. Using `question` here would create two sources of truth and
risk desync if the LangGraph checkpointer reconstructs message history from a
different source than `question`.

### Prompt / Tool Design Decisions

The `SystemMessage` is constructed inline per-call rather than from a template file.
Rationale: the context changes every call (docs from retrieval) and the user_level
changes per user. A static prompt file would require f-string injection anyway — the
inline construction is cleaner for a node that has no fixed few-shot examples. If
multi-turn prompt tuning becomes necessary in a later commit, the inline construction
can be extracted to a prompt file without changing the node's interface.

The `user_level` default is `"novice"` via `state.get("user_level", "novice")` rather
than assuming the field is always present. `AgentState` declares it as required, but
TypedDict fields can be absent at runtime if the state dict was constructed without all
keys (e.g., from a minimal test fixture or an early graph entry that hasn't populated
user_level yet). The `"novice"` default is the safest choice — it produces the most
accessible output rather than an error.

### What Was Considered and Ruled Out

1. **Sync `llm.invoke()`** — rejected. Blocks the async event loop and defeats
   streaming readiness. `ainvoke` is the required pattern for all async LangGraph nodes.

2. **Reading `state["question"]` instead of `state["messages"]`** — rejected per spec.
   The spec is explicit: "the current user question is already the last HumanMessage in
   `state["messages"]`". Using `question` in the LLM call creates a redundancy and
   would miss the full conversational framing.

3. **Instantiating `ChatOpenAI` directly** — rejected. `get_provider()` is the circuit
   breaker entry point. A direct instantiation bypasses the OpenAI → Ollama fallback
   chain and couples the node to a single provider.

4. **Returning `{"messages": all_messages, "answer": ...}`** — rejected. The
   `add_messages` reducer accumulates messages — if the node returned the full history
   plus the new AIMessage, the history would be doubled on every turn. The node returns
   only the new message `[response]`.

5. **Caching the LLM instance as a module-level variable** — considered but ruled out.
   `get_provider()` is called per invocation so it can observe the current circuit
   breaker state. Caching the LLM would freeze the provider choice at import time,
   making CB failover invisible to the node.

### Failure Modes Considered

- **LLM provider down / rate-limited** — `get_provider()` returns OllamaProvider if
  `openai_cb` is OPEN. If Ollama is also unavailable, `ainvoke()` will raise. The spec
  does not require try/except in the node — circuit breaking is the provider layer's
  responsibility. An unhandled raise propagates to the graph, which surfaces it as
  a graph invocation error to the SSE endpoint.
- **Empty docs list** — `"\n\n".join(...)` on an empty list produces `""`. The system
  message says "Answer using ONLY the provided context" with an empty context block.
  The LLM will produce a "I don't have enough context" answer rather than hallucinating.
  This is acceptable behaviour and matches the RAG contract.
- **`user_level` field absent** — handled via `.get("user_level", "novice")` default.
- **`ainvoke` returns a non-`AIMessage`** — typed as `AIMessage` in the annotation.
  If the provider returns a different `BaseMessage` subtype, `response.content` still
  works (it's defined on `BaseMessage`). Runtime correctness is not affected; Pyright
  would flag the mismatch.

### Test Results

18 new tests, all passed:
- Gate 1 (4 tests): answer key is str, messages has AIMessage, exactly 2 keys returned, answer matches AIMessage content
- Gate 2 (3 tests): returned messages has exactly 1 AIMessage, list length is 1, no HumanMessage echoed back
- Gate 3 (3 tests): first-turn answer returned, no raise, docs joined into context
- Gate 4 (3 tests): second-turn answer returned, full history forwarded to LLM in order, no raise
- Gate 5 (5 tests): get_provider called once, get_llm called on provider, ainvoke called (not invoke), system message has user_level, missing user_level defaults to 'novice'

Full suite: 98 passed (80 prior + 18 new), 0 failures.

### Approach

The initial design question was where to call `get_provider()` — once at module import
(singleton) or once per node invocation. A module-level singleton was tempting for
performance, but it would freeze the provider at import time and make the circuit breaker
invisible — any CB state change after import would be silently ignored. Per-invocation
call means every turn observes the current CB state, paying one function call overhead
that is negligible compared to the LLM round-trip. The per-invocation pattern is correct.

The `type: ignore[call-overload]` comment on `state.get("user_level", "novice")` is
intentional: `AgentState` is a `TypedDict` and `TypedDict.get()` with a default is not
typed to return the union of the value type and the default in all Pyright versions.
The comment documents that this is a Pyright limitation workaround, not a logic smell.

---

## Session 04 — Commit 10: `langgraph-graph-assembly`

**Date:** 2026-05-10
**Status:** ✅ Done

### Task Brief

Wire `retrieve_node` and `generate_node` into a compiled LangGraph graph. Replace
`run_rag_pipeline()` in `chain.py` with `graph.astream_events()` in `chat.py`.
Delete `SessionMemory` entirely. Instantiate `MemorySaver` in the FastAPI lifespan
and store the compiled graph on `app.state.rag_graph`.

### AI Problem Being Solved

The core problem: how to replace a synchronous pipeline (`run_rag_pipeline` → JSON
response) with an async streaming graph that emits token-level SSE events, while
preserving cross-turn conversation history that was previously stored in `SessionMemory`.

The two subsystems that had to work together are (a) LangGraph's checkpointer model
(keyed by `thread_id`) for conversation continuity, and (b) FastAPI's `StreamingResponse`
with `astream_events()` for token streaming. Neither requires the other to change — they
compose naturally when wired through the factory function pattern and lifespan.

### Graph Design Decisions

**Factory function, not module singleton.** `build_graph(checkpointer)` is called once
in lifespan and stored on `app.state.rag_graph`. This was the only viable design:
`MemorySaver` must be instantiated inside the lifespan so it is scoped to one
application lifetime. A module-level singleton would be created at import time (before
lifespan runs) and would not be garbage-collected cleanly on shutdown.

**`recursion_limit=10` baked into compiled graph config via `.with_config()`.**
The spec required `recursion_limit` to be set. LangGraph's `StateGraph.compile()` does
not accept `recursion_limit` directly — it is passed as a config key. `.with_config()`
applied after `compile()` bakes it into the graph's default config so every invocation
inherits it without the caller having to pass it explicitly.

**`graph.astream_events(..., version="v2")` in `chat.py`.** The `version="v2"` argument
is required for LangGraph >= 0.2 to emit `on_chat_model_stream` events. Without it the
stream runs but token events are absent — the client would see only the final `done`
event. This was explicitly called out in the pre-brief, making it a zero-ambiguity
requirement.

**`generate_stream()` is a pure async generator — no blocking I/O.** The generator
iterates over `rag_graph.astream_events()` which is itself an async generator.
The only non-async operation inside is `json.dumps()` which is CPU-bound but
instantaneous. There is no `asyncio.to_thread()` call inside the generator — correct.

### What Was Considered and Ruled Out

1. **Module-level `MemorySaver` singleton** — rejected. Creates a shared mutable object
   at import time, making the lifespan pattern pointless and making tests harder to
   isolate (the singleton would bleed state between test runs).

2. **Passing `recursion_limit` in every `astream_events()` call** — considered but
   rejected in favour of `.with_config()`. Baking it into the compiled graph is the
   correct pattern for project-wide defaults. Per-call passing would require every
   caller to know the magic number.

3. **Streaming from NiceGUI UI via the old `run_rag_pipeline` path** — impossible after
   this commit because `run_rag_pipeline` is removed. The UI (`app/ui.py`) imported
   `run_rag_pipeline` directly — a discovered scope gap not listed in the spec. Fixed by
   replacing the direct call with an httpx SSE stream to `POST /api/chat`.

4. **Keeping `test_conversation_memory.py`** — rejected. The test file exclusively tests
   `SessionMemory`, which is deleted. Retaining it would fail the suite. The test's
   coverage concern (conversation continuity) is now owned by `test_graph.py` Gate 3.

5. **Deleting `chain.py`** — considered. After removing `run_rag_pipeline`, `chain.py`
   is empty of logic. Decision: keep as a thin placeholder with a module docstring
   explaining the Commit 10 removal. Deleting would require updating import paths in
   other files (e.g., the `test_chain_imports_without_error` test in `test_profile_service.py`
   which imports `rag.chain` as an import smoke test). Lower risk to retain.

### Failure Modes Considered

- **LangGraph provider error / rate limit mid-stream** — `astream_events()` is an
  async generator. An exception raised inside the graph propagates out of the `async for`
  loop, which terminates `generate_stream()`. FastAPI will close the SSE connection.
  The client sees an incomplete stream (no `done` event). This is acceptable for this
  commit — circuit breaker is already present in the provider layer.

- **`on_chain_end LangGraph` event absent** — if the graph fails before completion,
  `final_state` remains `{}`. The `done` event still emits with `user_level: "novice"`
  and `assessed_topics: {}` as defaults. The client gets a graceful `done` rather than
  a hung connection.

- **Second turn with unknown `thread_id`** — `MemorySaver` creates a new checkpoint
  namespace for every unseen `thread_id`. No error. History starts fresh.

- **`ui.py` consuming SSE via httpx `stream()`** — the internal httpx client has a
  30-second timeout. A very slow LLM response could time out before the `done` event.
  Accepted as-is; timeout tuning is a deployment concern not a correctness issue.

### Test Results

13 new tests in `tests/test_graph.py`, all passed:
- Gate 1 (2 tests): `build_graph()` returns `CompiledStateGraph`, accepts `MemorySaver`
- Gate 2 (2 tests): retrieve runs before generate; generate receives docs from retrieve
- Gate 3 (2 tests): second turn has prior messages in state; different thread_ids are independent
- Gate 4 (1 test): compiled graph config has finite `recursion_limit`
- Gate 5 (4 tests): `conversation.py` absent from filesystem; not importable; no `SessionMemory` in chain; no `run_rag_pipeline` in chain
- Gate 6 (1 test): CB OPEN → BM25 fallback works end-to-end through the graph

Deleted `tests/test_conversation_memory.py` (5 tests for the now-deleted `SessionMemory`).
Net test delta: +13 new, -5 deleted = +8. Final suite: 103 passed, 0 failures.

### Approach

The initial cognitive map of this commit looked straightforward: `build_graph()`,
wire two nodes, update lifespan, swap `chat.py` endpoint. The wrinkle was `ui.py` —
it imported `run_rag_pipeline` which was being deleted, and it was not listed in the
spec's "files touched". The right call was to fix it in scope rather than flag it as
a blocker. The fix (httpx SSE collection) was two dozen lines and kept the UI working
without touching the streaming architecture. The alternative — leaving `ui.py` broken
and flagging it — would have been correct protocol but unnecessary friction for something
that was clearly an oversight in the spec, not a domain boundary question.

The `.with_config({"recursion_limit": _RECURSION_LIMIT})` pattern was the key
implementation detail that clinched the recursion_limit requirement. `compile()` does
not accept it as a keyword argument; the config must be applied after compilation.
Reading the LangGraph source confirmed this. The constant `_RECURSION_LIMIT = 10` is
private to `graph.py` — not exported — because callers should not depend on the specific
value.

---

## Session 04 — Commit 10 gate-fix

**Date:** 2026-05-10
**Status:** ✅ Done

### Task Brief

Two quality gate findings returned from the Commit 10 gate wave. Both blocking:
- Quinn BLOCK: `chat.py` HTTP layer had zero test coverage; 4 tests required.
- Sage MEDIUM: `ui.py:370` had a hardcoded `storage_secret="rag-secret-key"` exposing
  the NiceGUI cookie signing key in a public repo.

### AI Problem Being Solved

**Quinn fix:** The challenge was testing a streaming SSE endpoint (FastAPI + `StreamingResponse`)
against a `CompiledStateGraph` without a live LangGraph runtime. The graph's `astream_events()`
is an async generator — it can't be replaced with a plain `AsyncMock` because async generators
and async coroutines are different protocol types in Python. A `MagicMock` with `return_value`
assigned would be callable but not async-iterable. The solution was a `FakeGraph` class whose
`astream_events` method is declared with `async def ... yield` — a true async generator — so
`async for event in rag_graph.astream_events(...)` in the endpoint works correctly.

A second issue surfaced during the first test run: the authenticated tests (Tests 1-3) failed
with `sqlite3.OperationalError: no such table: user_profiles`. The route calls
`asyncio.to_thread(get_user_level, user_id)` which hits the profile DB. Since the test app
has no lifespan and no SQLite setup, `get_user_level` had to be patched out entirely via
`patch("app.api.routes.chat.get_user_level", return_value="novice")`. The anonymous test
(Test 4) never reaches that code path — the 401 fires first — so no patch was needed there.

**Sage fix:** The `nicegui_storage_secret` field was added to `Settings` with the same
`field_validator` pattern as `jwt_secret` (minimum 32 characters, no default so startup
fails fast). The lru_cached singleton means tests that need to patch `allow_anonymous_chat`
must mutate the already-imported `config_module.settings` instance attribute directly rather
than patching the class. This was the same pattern used in the test for the anonymous 401 gate.

### Prompt Design Decisions

No LLM calls in this session. All work was deterministic code and test construction.

### Tool Output Schema Decisions

`FakeGraph.astream_events` yields raw `dict[str, Any]` objects matching the LangGraph v2
event schema: `{"event": str, "name": str, "data": {...}}`. The `chunk` object inside
`on_chat_model_stream` data is constructed via `type("Chunk", (), {"content": content})()` —
a zero-dependency stand-in that satisfies `chunk.content` attribute access without importing
any LangChain types into the test.

### Failure Modes Considered

- `FakeGraph` as `MagicMock` — rejected: MagicMock is not an async generator, `async for`
  over it raises `TypeError: object MagicMock can't be used in 'await' expression`.
- Patching at `app.core.config.Settings.allow_anonymous_chat` (the class) — rejected:
  `lru_cache` means `settings` is already instantiated; patching the class attribute does
  not affect the cached instance. Mutating the instance directly is the correct approach.
- Using `TestClient` without `client.stream()` for streaming responses — rejected: the
  non-streaming client reads the full body before returning, which works for SSE but
  `iter_lines()` is only available on a streaming context manager response.

### Approach

Initially the three authenticated tests looked like they just needed a `FakeGraph` and the
dependency override. The first run showed the `user_profiles` SQLite error — `get_user_level`
was not on the radar because the spec didn't mention it. Once identified, patching it at
`app.api.routes.chat.get_user_level` (the function's home module, not the call site) was
the correct target — patches at the call site would be fragile if the import were to change.
The Sage fix was straightforward once the validator pattern from `jwt_secret` was established
as the template: copy, rename, update the error message, add to `.env.example` and `.env`.

### Test Results

107 passed (103 existing + 4 new) in 16.03s. Zero regressions.

---

## Session 05 — Commit 11: `langgraph-graph-smoke-test`

**Date:** 2026-05-10

**AI Problem Being Solved:**
Write a minimal integration smoke test that exercises the fully assembled graph
(Commit 10) end-to-end — no real LLM, no ChromaDB, no BM25 corpus — and verifies
that the output shape contract holds: `answer` is a non-empty string, `docs` is a
list, `retrieval_source` is exactly `"chroma"` or `"bm25"`, and MemorySaver cross-turn
persistence works as specified.

**Prompt / Design Decisions:**

1. **Two distinct mock layers, not one.** The graph's nodes are bound at compile time
   (LangGraph captures the function references when `builder.add_node()` is called).
   For Gates 1–4, patching `retrieve_node` at `agents.graph` (its import site in graph.py)
   and `get_provider` at `agents.nodes.generate` (its import site in generate.py) is
   sufficient to fully exercise the real generate_node code path while preventing any
   external I/O. This mirrors the pattern established in `test_generate_node.py`.

2. **Gate 5 threading — capture at generate_node, not at the final result.** The spec
   asks that "a second invocation with the same session_id receives non-empty history."
   The cleanest way to assert this is to capture `state["messages"]` as seen by
   `generate_node` on each turn, rather than inspecting the final ainvoke() return value.
   The final state dict after ainvoke() does contain the full accumulated message list,
   but reading it from the captured result is less explicit than reading it from inside
   the node's view. The capture-generate approach (patching `agents.graph.generate_node`
   with an async stub that records state) gives a direct view of what MemorySaver replayed.

3. **Shared MemorySaver + shared graph instance across turns.** Both invocations in each
   threading test use the same `checkpointer = MemorySaver()` and the same compiled `graph`.
   This is the only correct threading test setup — a new MemorySaver per invocation would
   always start with empty state, making the test trivially pass for the wrong reason.

4. **Viktor-defensive: set membership assertion.** The spec explicitly requires
   `assert state["retrieval_source"] in {"chroma", "bm25"}`. All four Gate 4 tests use
   this form. Gate 4b also adds the exact-value assertion after the membership check.

5. **Collection types fully typed in all stubs and helpers.** All local variables in
   stubs and test methods use explicit `list[X]` or `dict[str, Any]` — no bare `list`
   or `dict`. `config` variables are typed `dict[str, Any]` at their declaration site.

**Tool Output Schema Decisions:**
No new tool schemas introduced — this commit tests existing schemas. The smoke test
validates that `retrieve_node`'s output schema (`docs: list[Document]`, `retrieval_source: str`)
and `generate_node`'s output schema (`answer: str`, `messages: list[AIMessage]`) survive the
full graph invocation round-trip correctly.

**Failure Modes Considered:**
- MemorySaver test failing if a new graph instance (and thus new checkpointer) is built per
  invocation — prevented by shared setup pattern.
- Gate 5 history test falsely passing because `ainvoke()` returns the current-turn input
  messages rather than the accumulated checkpoint state — prevented by capturing inside the
  node stub where the reducer has already merged the checkpoint.
- `retrieval_source` assertion being a string equality check rather than set membership —
  Viktor would block this; all assertions use `in {"chroma", "bm25"}`.

### Approach

Initially considered patching only at the graph level (`agents.graph.retrieve_node` and
`agents.graph.generate_node`) for all gates, which would be maximally isolated but would
not exercise the real `generate_node` code at all. The spec's Gate 2 (non-empty answer)
and Gate 3 (docs is a list) are more meaningful when `generate_node` runs for real — they
confirm the full invocation pipeline rather than a double stub. The final design uses
real `generate_node` for Gates 1–4 (with only `get_provider` mocked to prevent LLM calls)
and stubs `generate_node` entirely only for Gate 5 (where the threading assertion requires
capturing raw state before the node returns). This gives the best coverage with the minimum
mock surface.

### Test Results

14 passed in 24.56s. Zero regressions.

---

## Session 06 — Commit 12: `langgraph-assessment-scaffold`

**Date:** 2026-05-10
**Status:** ✅ Done

### Task Brief

Add `assess_node` to the LangGraph graph. Ship the node structure, input/output
contract wiring, and a conditional fallback edge. The LLM call is stubbed
(deterministic empty `AssessmentOutput`). Wire `update_profile_node` as a
passthrough stub in `graph.py`. Both paths (assessment_error True and False) must
compile cleanly and reach `update_profile_node`.

Final graph topology: `START → retrieve → generate → assess → [conditional] → update_profile → END`

### AI Problem Being Solved

The design problem was how to represent the conditional fallback edge when both paths lead
to the same destination (`update_profile_node`). A naive implementation would use a
regular edge from `assess` to `update_profile` and skip the conditional entirely —
which would also work for correctness in this commit. The decision to use
`add_conditional_edges` even when both paths resolve to the same node was deliberate:
it makes the branching structure explicit and inspectable via `graph.get_graph()`,
it's the correct wiring for when Commit 15 might diverge the paths, and it means
the routing logic is in a named function (`_route_after_assess`) that can be unit-tested
independently of graph compilation.

The second design question was whether `update_profile_node` should live in its own
file or as a stub in `graph.py`. The spec says "stub node in graph.py only" — the stub
is a passthrough that will be replaced in Commit 15. Putting it in `graph.py` signals
its temporary status clearly and avoids creating a file that will need to be
structurally replaced (vs. just having its body filled in).

### Prompt / Tool Design Decisions

**assess_node output contract: three keys only.**
The node returns exactly `{"topic_scores_delta": ..., "identified_gaps": ..., "assessment_error": ...}`.
It does not touch `user_level` in the state — even though `AssessmentOutput` has a `user_level`
field. In this scaffold commit, the user_level from the stub's `AssessmentOutput` is only
used to construct the output object (to satisfy the schema) — it is not written back to state.
Rationale: the spec says assess_node should not touch `messages`, `docs`, `answer`, or other
nodes' keys. `user_level` is currently considered a "turn input" field (loaded from the profile
before graph entry). Letting assess_node overwrite it would create a circular update loop
(assess reads user_level, updates user_level, next turn's assess reads the just-assessed
user_level). In Commit 13/15, this decision will be revisited — the spec may intend for
assess_node to emit a `user_level_delta` rather than overwrite state directly.

**Fallback: try/except on the entire assess_node body.**
The try/except wraps the stub `AssessmentOutput(...)` call so the fallback mechanism is
testable even in the scaffold. This is intentional: when Commit 13 replaces the stub with
a real LLM chain, the fallback already works without any changes. The test suite confirms
that patching `AssessmentOutput` to raise produces `assessment_error=True` — exactly the
behavior Commit 13's LLM parse failure would trigger.

### What Was Considered and Ruled Out

1. **Regular edge from `assess` to `update_profile`** — technically correct for this commit
   since both conditional paths go to the same node. Rejected in favor of `add_conditional_edges`
   because: (a) it makes the routing logic visible and testable, (b) it's the correct wiring
   for the eventual diverged-path case, and (c) it requires no structural change to the graph
   when Commit 15 potentially diverges the fallback.

2. **`update_profile_node` in `src/agents/nodes/update_profile.py`** — considered. Rejected
   per spec ("stub node in graph.py only"). A separate file for a 1-line passthrough adds
   unnecessary file count and suggests the stub is a permanent resident.

3. **Writing `user_level` back to state from assess_node** — considered (AssessmentOutput
   has a `user_level` field). Rejected: would make assess_node a writer of a "turn input"
   field, creating potential state ownership conflicts and a circular update risk. Deferred
   to the Commit 13/15 design review.

4. **Async `update_profile_node`** — not used. The stub returns `{}` synchronously. LangGraph
   supports both sync and async nodes. A sync stub is correct here; Commit 15's real node
   will be async (it will call the profile service).

### Failure Modes Considered

- **Both conditional paths resolve to the same string** — `_route_after_assess` returns
  `"update_profile"` regardless of `assessment_error`. This is intentional per spec; the
  fallback path is "reach update_profile with empty delta." If future commits need a true
  bypass (skip update_profile entirely), `_route_after_assess` and `add_conditional_edges`
  mapping can be extended without touching any other node.
- **assess_node exception in production (LLM parse failure)** — try/except catches all
  `Exception` subclasses, logs with `exc_info=True` for traceback, and returns empty delta
  with `assessment_error=True`. The graph continues cleanly to `update_profile_node`.
- **Smoke tests breaking after graph topology change** — verify before shipping. The existing
  14 smoke tests patch `retrieve_node` and `generate_node` but leave `assess_node` to run
  as the real stub. Since the stub is deterministic and has no external calls, all 14 passed
  without modification.

### Test Results

19 new tests in `tests/test_assess_node.py`, all passed:
- Gate 1 (4 tests): stub returns `assessment_error=False`, empty `topic_scores_delta`, empty `identified_gaps`, correct output types
- Gate 2 (3 tests): no foreign keys in output, all declared keys present, exactly the declared keys
- Gate 3 (3 tests): exception → `assessment_error=True`, empty deltas on exception, all three keys in fallback output
- Gate 4 (3 tests): `_route_after_assess` routes to `"update_profile"` on both True and False, insensitive to other state keys
- Gate 5 (6 tests): graph compiles, ainvoke doesn't raise, returns dict, assess output in final state, fallback path reaches update_profile, normal path reaches update_profile

Existing 14 smoke tests: all passed (no modifications required).
Full suite: 140 passed (121 prior + 19 new), 0 failures.

### Approach

The initial question was whether the conditional edge needed to be `add_conditional_edges`
or whether a plain `add_edge("assess", "update_profile")` would satisfy the spec. The spec
says "the fallback edge is non-negotiable for LangGraph" and "both paths must compile cleanly."
Both compile with a plain edge — but the spec's wording ("conditional fallback edge") and the
commit message ("conditional fallback edge") are unambiguous that the routing must be explicit.
The tie-breaker was testability: `_route_after_assess` as a named function with two unit tests
gives clear evidence the routing logic reads `assessment_error`, satisfying Viktor's sharp edge
check ("The conditional edge function must read `state['assessment_error']` — not the node
return value directly").

---

## Session 07 — Commit 13: `langgraph-assessment-llm`

**Date:** 2026-05-10
**Status:** ✅ Done

### Task Brief

Replace the deterministic stub in `assess_node` with a real LLM call using
`assessment_prompt | llm.with_structured_output(AssessmentOutput)`. Create a new
`src/agents/prompts/assessment.py` module containing the assessment prompt template.
Add 15 new tests covering the real LLM path, parse failure fallback, user_level
validation, and per-invocation provider routing. All 140 prior tests must continue
to pass.

### AI Problem Being Solved

The core assessment problem: given a user's question and the RAG-generated answer,
identify which knowledge modules were touched, assess the user's apparent understanding
of each, and surface gaps — without a live LLM in tests and without making the
assessment error a hard failure in production.

The secondary problem: this is a hidden second LLM call per user turn. Latency matters.
The prompt must be concise and provide sufficient constraint to prevent hallucinated
module slugs without being verbose.

The tertiary problem: `AssessmentOutput` has a `user_level` field (required by the
Pydantic schema for `.with_structured_output()`), but `assess_node` must NOT write
`user_level` back to `AgentState` — that would create a state ownership conflict with
the profile update system. The LLM needs the field in its output schema, but the node
intentionally discards it.

### Prompt / Tool Design Decisions

**Prompt structure: role → task → constraints → output format.**
The prompt in `src/agents/prompts/assessment.py` uses a `ChatPromptTemplate` with two
messages: a system message establishing the role and constraints, and a human message
providing the per-turn inputs (question, answer, valid_slugs).

**Why `valid_slugs` is passed as an input variable, not hardcoded in the system prompt.**
`VALID_MODULE_SLUGS` is a module-level constant in `state.py`. Passing it as a
template variable (`{valid_slugs}`) at invocation time via `sorted(VALID_MODULE_SLUGS)`
means the prompt automatically updates if slugs are added to or removed from the set
in a future commit — no prompt file needs to change. The alternative (hardcoding the
slugs in the system message string) would create a maintenance coupling between
`state.py` and `assessment.py` that is invisible to the type checker.

**Why constraint language is explicit about slugs ("MUST come from the valid_slugs list").**
The Pydantic validator on `AssessmentOutput.topic_scores_delta` silently drops unknown
slugs — but silent drops mean the downstream delta is smaller than intended. The prompt
constraint prevents the hallucination before it reaches the validator. Defense in depth:
prompt constrains → validator cleans. Either layer is sufficient; both together mean
hallucinated slugs are practically eliminated in production.

**No few-shot examples in the prompt.** `.with_structured_output()` provides strong
implicit grounding via the JSON schema. Adding examples would increase token cost per
hidden call. The explicit constraint language and the score range specification
(`[-1.0, 1.0]`) are sufficient to guide the LLM to well-formed output.

### What Was Considered and Ruled Out

1. **Hardcoding VALID_MODULE_SLUGS in the prompt string** — rejected. Creates silent
   drift risk. The frozenset in state.py is the single source of truth; the prompt
   receives it at runtime.

2. **Using `StrOutputParser` instead of `.with_structured_output()`** — rejected per
   spec and per design principle. Free-form LLM output that requires downstream parsing
   is a reliability failure. `.with_structured_output()` gives validated structured output
   or raises at parse time.

3. **Caching the LLM instance at module level** — rejected. Same reasoning as
   `generate_node`: the circuit breaker state must be observed per invocation, not
   frozen at import time.

4. **Writing `user_level` back to `AgentState` from `assess_node`** — rejected.
   `user_level` in `AgentState` is currently a "turn input" field loaded from the
   profile before graph entry. Letting `assess_node` overwrite it would create a circular
   update (assess reads user_level → updates user_level → next assess reads the just-
   assessed level). The field exists in `AssessmentOutput` for the LLM's assessment,
   not for state propagation. This decision is documented in the docstring and deferred
   to Commit 15.

5. **Using `pytest.fixture` for the mock setup** — considered for the repeated
   `_make_provider_mock` / `_make_prompt_mock` pattern. Rejected because the fixtures
   would need parametrization for different `AssessmentOutput` values across tests.
   The factory functions are simpler and make the mock dependencies explicit at each
   test site.

### Failure Modes Considered

**RunnableSequence mock opacity.** The critical failure mode in testing: `assess_node`
does `chain = assessment_prompt | llm.with_structured_output(AssessmentOutput)`. The `|`
operator creates a LangChain `RunnableSequence`. When I mocked `llm.with_structured_output`
to return a `MagicMock`, the resulting `assessment_prompt | mock_chain` was a
`RunnableSequence` wrapping the real prompt template and the mock. When
`RunnableSequence.ainvoke()` was called, it correctly called `mock_chain.ainvoke()` —
but the return value was a `MagicMock` attribute auto-generated by `MagicMock`, not my
`AssessmentOutput`. The root cause: `MagicMock.ainvoke` returns a `MagicMock` by default
unless explicitly set to `AsyncMock(return_value=...)`. The fix: mock at the prompt level
instead — `assessment_prompt.__or__` returns a fully-controlled chain mock. This avoids
all `RunnableSequence` internal machinery.

**Provider import-time config failure.** The module-level import of `from rag.providers
import get_provider` in `assess.py` triggers `app.core.config.settings` at collection
time when the `.env` is absent. This cascades to a `ValidationError` during test
collection, not during test execution. The fix: the worktree needs a `.env` (copied from
root for the test run). Long-term fix: a `conftest.py` that mocks `settings` at collection
time would be more portable. Flagged but not implemented — outside scope.

**LangGraph state serialization of MagicMock.** When `assess_node` runs inside the
real graph (Gate 5 tests), LangGraph's `MemorySaver` tries to serialize the state
values to msgpack. A `MagicMock` in `topic_scores_delta` causes `TypeError: Type is
not msgpack serializable: MagicMock`. This confirms the chain return value was a
`MagicMock` before the prompt-level mock fix. After the fix, the chain returns a real
`AssessmentOutput`, and `result.topic_scores_delta` is a proper `dict[str, float]`.

### Test Results

34 tests total in `test_assess_node.py` (up from 19):
- Gate 1 (4 tests): happy path — assessment_error=False, topic_scores_delta is dict, identified_gaps is list, output types correct
- Gate 2 (3 tests): output key boundary — no foreign keys, all declared keys present, exactly declared keys
- Gate 3 (4 tests): fallback — provider error sets assessment_error=True, chain invoke error sets True, empty deltas on error, fallback output has all keys
- Gate 4 (3 tests): conditional edge routing — routes to update_profile on both True and False
- Gate 5 (6 tests): graph integration — compiles, ainvoke doesn't raise, returns dict, assess output in state, fallback path, normal path
- Gate 6 (3 tests): LLM output mapping — vector_databases slug present, delta values are floats, gaps are valid slugs
- Gate 7 (3 tests): parse failure — ValueError sets True, RuntimeError empties deltas, Exception doesn't re-raise
- Gate 8 (4 tests): user_level validation — mock level is valid, invalid level rejected, all 5 accepted, user_level NOT in state output
- Gate 9 (4 tests): provider routing — get_provider called once per invocation, twice for two calls, get_llm called on result, with_structured_output called with AssessmentOutput class

Full suite: 155 passed (140 prior + 15 new), 0 failures.

### Approach

The first 30 minutes were prompt design. The key question was whether to constrain slugs at
the prompt level (given the validator already handles unknown slugs via silent drop) or rely
entirely on the schema enforcement. The decision: constrain at both levels. The prompt says
"MUST come from the valid_slugs list" and receives the actual list at runtime. The validator
catches any hallucinated slugs that slip through. The latency tradeoff was real — this is a
hidden second call — so the prompt was kept as tight as possible: no examples, no verbose
explanation of what RAG modules are, just the constraints and the task.

The test mocking problem consumed more time than the implementation. The initial approach
(mocking `llm.with_structured_output` to return a mock chain) failed because LangChain's
`RunnableSequence.ainvoke` doesn't directly call the mock chain's `ainvoke` method in a way
that a plain `MagicMock` with `ainvoke = AsyncMock(...)` handles correctly for all LangChain
versions. The symptom was `topic_scores_delta` being a `MagicMock` instead of a `dict`. The
fix was to mock one level higher — patch `assessment_prompt.__or__` to return a mock chain
I fully control. This bypasses the `RunnableSequence` machinery entirely: `assessment_prompt |
mock_llm_output` returns my mock chain, whose `ainvoke` I set to return my `AssessmentOutput`.
The insight: when testing LangChain chains, don't mock at the Runnable composition level —
mock at the entry point of the composition operator.

---

## Session 08 — Commit 15: `profile-update-node`

**Date:** 2026-05-10
**Status:** ✅ Done

### Task Brief

Replace the `update_profile_node` passthrough stub in `graph.py` with a real implementation
that: fetches the user's current profile, calls `compute_topic_scores()` to merge the
per-turn delta, and persists the result via `update_profile()`. Handle the two fast-exit
paths (anonymous user, assessment error). Set `last_activity_at` on every successful write.

### AI Problem Being Solved

This is not an AI problem — the node is entirely deterministic. The engineering problem
was: how to correctly map the three-layer data flow (AgentState fields → scoring service
types → DB column names) without introducing impedance mismatches at each boundary.

Three specific impedance questions had to be resolved before writing any code:

1. What does `compute_topic_scores` actually expect? The function signature is
   `compute_topic_scores(current_profile: dict, assessed_topics: dict[str, float], interaction_count: int)`.
   The first argument is the full profile dict (not just `profile["topic_scores"]`) — the
   function calls `current_profile.get("topic_scores", {})` internally. Passing only the
   scores dict would silently produce an empty merged result.

2. What column names does `update_profile()` accept? The `_ALLOWED_PROFILE_COLUMNS`
   allowlist in `db.py` is `{"mastery_level", "interaction_count", "topic_scores",
   "strengths", "gaps", "last_activity_at"}`. The AgentState field is `identified_gaps`
   but the DB column is `gaps`. Passing `identified_gaps=` to `update_profile()` would
   raise `ValueError` at runtime.

3. Should `identified_gaps` from state be written directly to `gaps`, or should the
   scoring-derived `gaps` (low-score slugs) be used? The scoring service computes
   `gaps` from merged scores (slugs with score <= 0.3). The per-turn `identified_gaps`
   from the LLM is the raw signal. The merged `score_update["gaps"]` reflects the full
   accumulated state and is therefore the correct value to persist.

### Tool / Node Design Decisions

**Two fast-exit paths at the top of the function.**
`user_id is None` exits immediately — before any DB call. `assessment_error is True`
exits immediately — before any DB call. Both return `{}`. This ordering is deliberate:
checking `user_id` first means we never fetch a profile for an anonymous user, not even
as a side effect of the `assessment_error` check.

**No async inside the node.**
The spec is explicit: synchronous node called via `asyncio.to_thread()` at the invocation
level. Adding `async` or `asyncio.to_thread()` inside the node would nest thread dispatch
inside thread dispatch — a pattern that is difficult to test and produces undefined behavior
under some event loop configurations. The node is sync throughout.

**`interaction_count` passed to `compute_topic_scores` even though unused.**
The scoring formula does not use `interaction_count`, but the function contract requires it
(Commit 14 spec). Passing it satisfies the contract and keeps the call site stable if the
formula evolves to use it in a future commit.

**Defensive `None` check after `get_profile_by_user_id`.**
If the profile row is missing (e.g., the user exists in `users` but their profile was never
created — a known edge case if auth is misconfigured), the node logs a warning and returns
`{}` cleanly. It does not raise, and it does not create the profile (that is the auth layer's
responsibility per the profile DB module docs).

### What Was Considered and Ruled Out

1. **Passing `identified_gaps` directly to `update_profile(identified_gaps=...)` as the
   `gaps` column** — rejected. `identified_gaps` is not an allowed column name
   (`_ALLOWED_PROFILE_COLUMNS` uses `gaps`). More importantly, the scoring service
   produces `score_update["gaps"]` which is derived from the full merged profile state —
   a richer signal than the per-turn raw LLM output.

2. **Creating the profile if missing** — rejected. Profile creation belongs to the
   registration/auth flow (Commit 06). Creating here would silently bypass the FK
   constraint on `user_profiles.user_id → users.id` and could produce orphaned profiles
   if called with a non-existent user_id.

3. **Making the node async** — rejected per spec. Async nodes in LangGraph require
   `await` inside, which means the event loop must be running. Since the caller wraps
   via `asyncio.to_thread()`, an async node would require the thread to have its own
   event loop, which is non-standard and fragile.

4. **Writing `user_level` from `score_update["mastery_level"]` to `AgentState`** —
   not applicable. This node returns `{}` — it does not update AgentState. The mastery
   level is persisted to the DB via `update_profile(mastery_level=...)`.

### Failure Modes Considered

- **`get_profile_by_user_id` raises** (DB connection failure) — propagates up. The graph
  surfaces it as a graph invocation error. No specific try/except added — DB failures are
  infrastructure-level and should alert, not be silently swallowed.
- **`compute_topic_scores` with all-invalid delta** — returns empty merged scores + novice
  mastery. `update_profile` is still called and sets `last_activity_at`. Acceptable.
- **`update_profile` raises `ValueError` for unknown column** — would indicate a code bug
  (wrong kwarg name). Propagates up. The test suite at commit time validates the exact
  kwargs.

### Handoffs Consumed

- Commit 05 (Mira): `last_activity_at` set via `datetime.now(timezone.utc).isoformat()` on
  every successful turn. CONSUMED.
- Commit 14: `compute_topic_scores` import path confirmed; profile dict passed without
  `json.loads` (already deserialized by `get_profile_by_user_id`); `interaction_count`
  passed in call even though unused by formula. CONSUMED.

### Outbound Handoffs

- Commit 18 (UI profile panel): `last_activity_at` is a guaranteed ISO 8601 UTC string
  after any successful authenticated turn. `interaction_count` is incremented per turn
  and persisted. Both are readable directly from the profile row.
- Downstream: `update_profile_node` is now in `src/agents/nodes/update_profile.py`.
  `graph.py` imports it: `from agents.nodes.update_profile import update_profile_node`.

### Test Results

22 new tests in `tests/test_update_profile_node.py`, all passed:
- Gate 1 (4 tests): topic_scores written to DB, existing scores preserved in merge,
  delta values in merged output, returns empty dict
- Gate 2 (3 tests): interaction_count incremented by 1, incremented from 0, not
  incremented on error path
- Gate 3 (4 tests): update_profile not called on error, get_profile not called on error,
  returns {} on error path, no DB write with empty delta and error
- Gate 4 (4 tests): update_profile not called when anonymous, get_profile not called when
  anonymous, returns {} for anonymous, non-empty delta still skips on anonymous
- Gate 5 (5 tests): last_activity_at passed to update_profile, is string, is valid ISO 8601,
  not set on anonymous path, not set on error path
- Bonus (2 tests): no DB write when profile not found, returns {} when profile not found

Full suite: 194 passed (172 prior + 22 new), 0 failures.

### Approach

The commit looked like a straightforward data plumbing job — read state fields, call service,
call DB. The two non-obvious decisions were the `identified_gaps` → `gaps` mapping and the
full-profile-dict contract of `compute_topic_scores`. Both were caught before writing any code
by reading `db.py` (the `_ALLOWED_PROFILE_COLUMNS` frozenset made the column names explicit)
and `scoring.py` (the `current_profile.get("topic_scores", {})` call made it clear the full
dict was expected). The test design was deliberately shallow: all 22 tests use mocked DB
functions (`patch("agents.nodes.update_profile.get_profile_by_user_id", ...)`) rather than
a real SQLite database. This is the correct choice for a unit test — the DB round-trip is
tested in `test_profile_service.py` where it belongs. The gate tests verify behavioral
contracts, not DB internals.
