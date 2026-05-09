# Nova — Worklog
# Project: rag-from-scratch
# Stack: Python 3.11+, FastAPI, LangGraph, LangChain, ChromaDB, SQLite

---

## Current State
*Last updated: Commit 09 · 2026-05-09*

**Last completed:** Commit 09 `langgraph-generate-node` ✅
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- Commit 10 (graph assembly + streaming): `generate_node` is in `src/agents/nodes/generate.py`.
  Signature: `async def generate_node(state: AgentState) -> dict`.
  Returns exactly `{"messages": [AIMessage], "answer": str}`.
  Import as: `from agents.nodes.generate import generate_node`.
  The node is async — use `await` or wire into the graph with `graph.astream_events()`.
  `add_messages` appends the returned `[AIMessage]` — the node does NOT return the full history.
  `question` is NOT read by this node — the current question is already the last HumanMessage in state["messages"].
  LLM is obtained via `get_provider().get_llm()` — OpenAI CB → Ollama fallback is automatic.
  When `graph.astream_events()` is wired, `on_chat_model_stream` token events fire with zero
  changes to generate_node — it's already async and uses `ainvoke`.
- Commit 08+ (graph build): `AgentState` is complete. All Phase 4 fields are present.
  `messages` uses `add_messages` reducer — nodes must append `[HumanMessage(...)]` or
  `[AIMessage(...)]` via state update, not replace the list.
- Commit 10 (streaming): `session_id` is passed as `thread_id` in the graph config,
  NOT as a state field. Pattern:
      config = {"configurable": {"thread_id": session_id}}
      graph.astream_events(initial_state, config=config, version="v2")
- Commit 15 (profile_update_node): `AssessmentOutput.topic_scores_delta` is a per-turn
  delta — not a DB snapshot. The node must MERGE these deltas into the existing
  `user_profiles.topic_scores` dict, not overwrite it.
- Rex (Commit 10): Rex's handoff about `format_history(session_id)` is superseded by
  the `messages` / `add_messages` design. Conversation history is now managed by the
  LangGraph checkpointer via `thread_id`. No explicit `conversation_history` string
  injection is needed.

**Open Handoffs — Inbound:**
- (none)

**Key Interfaces I Own (for teammates):**
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
