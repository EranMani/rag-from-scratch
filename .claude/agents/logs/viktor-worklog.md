## Viktor's Worklog

---

## Current State
Last reviewed: Commit 07 `langgraph-state-schema` (second pass) — Verdict: PASS
Open resolutions awaiting: none — all 4 first-pass blockers resolved
Recurring patterns by engineer (Rex):
  - Strong responsiveness to typing-discipline feedback: every Concern from the first pass closed cleanly with the recommended fix, plus extra defensive validators (slug filtering) beyond the minimum.
  - Watch for: forward-looking schema fields whose runtime producers still emit legacy values (cache_hit). Documented this turn — flag again only if the Commit 10 migration is skipped.

---

## Commit 03 — `wire-conversation-history`

**Files reviewed:**
- `src/rag/pipeline/generator.py`
- `src/rag/chain.py`
- `src/rag/memory/conversation.py` (supporting read — not changed, but contract verification required)

**Date:** 2026-05-09

### Findings

💬 `src/rag/chain.py:60` — The LLM cache key (`question + first 100 chars of each chunk`) does not incorporate `conversation_history`. Two requests with identical question and chunks but different conversation histories will collide on the LLM cache: the second caller receives a response generated without their prior context. This is the direct consequence of the intentional design decision to call `format_history()` before the LLM cache check but after `retrieve()`. The cache bypass scenario (STEP 3 serving a hit) silently drops history. This is currently a Comment rather than a Concern because the system serves the cached *answer* text (which is still factually correct), but callers who rely on conversational coherence will observe unexpected behavior. If multi-turn coherence is a correctness requirement for this system, this becomes a Concern. Flag for the owning agent so the trade-off is explicitly documented.

💬 `src/rag/pipeline/generator.py:19` — When `conversation_history` is `""` (first turn, or LLM cache hit path), the prompt renders as the literal string `"Conversation history:\n\n"` with a blank body. This is not a rendering error — LangChain's `ChatPromptTemplate` substitutes the slot value as-is, so an empty string produces an empty section. The LLM will see it and process it fine. However, the label `"Conversation history:"` floating above nothing is mild prompt noise on every first-turn call. A simple `{history}` conditional would suppress the label when history is empty, but LangChain's `from_messages` syntax does not support inline conditionals natively — the cleanest fix would be to build the history block in Python before injection: `history_block = f"Conversation history:\n{conversation_history}\n" if conversation_history else ""`. Then remove the static label from the prompt template. Not a defect — a polish note.

💬 `src/rag/memory/conversation.py:39` — `format_history()` accesses `self._sessions[session_id]` directly via `defaultdict`, which auto-creates an empty list on first access for any new `session_id`. Then it slices `messages[-10:]`. On an empty list, `messages[-10:]` returns `[]`, and `"\n".join(...)` over an empty iterable returns `""`. So the first-turn behavior is correct. This was worth verifying against the prompt slot rendering concern above — confirmed safe.

💬 `src/rag/chain.py:73–75` — `session_memory.add_human()` and `session_memory.add_assistant()` are called unconditionally after both the LLM-cache-hit and the generate paths. This means that on an LLM cache hit, the turn is still recorded in session memory (question + cached answer). That is arguably correct behavior — the user asked a question and got an answer, so the turn happened — but it is worth a comment in the code that this is deliberate, not an oversight. If `cached_response` is served, history grows. If that history is then injected on the *next* turn, and the *next* turn also hits the LLM cache, the prompt key on that turn still does not include history. The compounding effect is that history grows faithfully but never influences cache-served responses. Document the intent.

### What's Good

The ordering discipline is exactly right. The comment on line 56 ("format_history() is called AFTER retrieve() so history influences generation only, not retrieval — this is intentional per design") is the kind of reasoning that saves the next engineer from "fixing" a non-bug. That comment earns its place. The `conversation_history: str = ""` default on `generate()` is the correct backward-compatible signature — existing callers pass two arguments and continue to work without modification. The docstring on `generate()` is complete and specific: it names the source (`SessionMemory.format_history()`), the expected type, and the first-turn behavior. That is above average documentation discipline.

### Verdict
PASS WITH COMMENTS

---

## Commit 07 — `langgraph-state-schema` (second pass)

**Files reviewed:**
- `src/agents/state.py`
- `tests/test_agent_state.py`
- Cross-references: `src/rag/chain.py` (legacy cache_hit values), `src/app/profile/schemas.py` and `src/app/profile/db.py` (mastery_level cohesion)

**Date:** 2026-05-09

### First-pass resolutions — verification

1. **`cache_hit` Literal — RESOLVED.** Now `Literal["hit", "miss", "bypass"]`. The docstring on lines 103–107 calls out the chain.py legacy values (`"query" | "llm" | "none"`) and ties the migration to Commit 10. I verified chain.py still emits the legacy strings at lines 50, 70, 75 — but they never flow into an AgentState today because the graph doesn't exist yet. No runtime collision. The forward-looking Literal is the right call; the documented migration boundary is exactly the kind of contract a reader 18 months from now needs.
2. **`docs: list[Document]` — RESOLVED.** Explicit `from langchain_core.documents import Document` at line 18, and the field annotation at line 69 carries the type. A reader now knows exactly what `docs[0]` is without grepping.
3. **`user_level: Literal[...]` — RESOLVED in both locations.** AgentState (line 81) and AssessmentOutput (line 132) share the same five-value Literal. AssessmentOutput's Literal is enforced at parse time by Pydantic (test V1 confirms `"wizard"` raises ValidationError). AgentState's Literal is type-checker-only since TypedDict has no runtime validation — that limitation is correctly noted in the test file's design notes (lines 22–23). Cross-checked against `src/app/profile/db.py:38` — the DB defaults to `'novice'`, which is in the Literal. No domain mismatch.
4. **Test file — RESOLVED.** `tests/test_agent_state.py` exists with 16 tests. I ran the full suite locally: **69/69 pass, including all 16 new tests**. Spec gates 1–7 plus the three Viktor additions (V1 invalid level, V2 unknown slug dropped, V3 valid slug preserved) all green.

### Findings on the resolved diff

💬 `src/agents/state.py:29` — `VALID_MODULE_SLUGS` is the canonical source of truth for module identifiers in the AgentState domain. There is no equivalent constant in `src/app/profile/` even though that module also operates on module slugs (`topic_scores: dict[str, float]` at `schemas.py:8`, persisted via `db.py:40`). Today the profile DB accepts any string key in `topic_scores` because there is no validation layer there. When Commit 15 wires `profile_update_node` to merge `topic_scores_delta` into the profile, the assess_node side will be slug-validated (good) but the profile-update side will accept whatever a future caller supplies. Not a defect today — `VALID_MODULE_SLUGS` lives where it's needed right now. Noting it so that when profile_update_node lands, the constant either moves to a shared module or gets re-imported at the boundary. Either is fine; pick consciously.

💬 `src/agents/state.py:135-159` — Both `field_validator`s use `mode="before"` and return early when the input is not the expected container type (`if not isinstance(v, dict): return v`). That early-return delegates the type-mismatch error to Pydantic's downstream type-coercion step, which is correct — Pydantic will raise a clean `ValidationError` against the field type. Just be aware: if a future refactor changes one of these fields to `Any` or `object`, the early-return becomes a silent identity pass-through. Today it's safe.

💬 `tests/test_agent_state.py:46-49` — Imports inside test methods (`def test_import_agent_state(self)` at line 46) rather than at module top. This is fine for explicit "does this import succeed" gate tests, but the same pattern is repeated inside every other test class (e.g. line 75, 88, 117). It does no harm — the import is cached after the first call — but the `# noqa: F401` on lines 46 and 49 suggests the author knows top-level imports would be cleaner. Style preference, not a defect.

### What's Good

The slug-filtering validators are above-spec defensive engineering. The first-pass Concern was just "constrain `user_level`"; Rex went further and constrained `topic_scores_delta` keys and `identified_gaps` values too — with `mode="before"` so a malformed LLM output is sanitized into a clean dict rather than producing a hard ValidationError that aborts the assess_node turn. That decision matches the assess_node failure-handling story implied by the `assessment_error: bool` field — the graph wants to soft-fail assessment, not crash, and silent slug-dropping (with a logger.warning) is exactly the right shape for that. Good instinct.

The docstring on `cache_hit` (lines 103–107) is the model for how to document a forward-looking schema field with a known producer mismatch. It names the legacy values, names the migration commit, and names the contract going forward. A reader does not need to grep chain.py to understand the divergence — the schema explains itself.

The test file's design-notes block (lines 19–28) is the kind of meta-commentary that saves the next person from "fixing" the import-inside-test pattern or wondering why TypedDict isn't validated at runtime. Earned its place.

### Verdict
PASS
