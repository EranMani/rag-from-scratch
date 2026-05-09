## Viktor's Worklog

---

## Current State
Last reviewed: Commit 03 `wire-conversation-history` — Verdict: PASS WITH COMMENTS
Open resolutions awaiting: none (no Hard Blocks, no Concerns requiring response)
Recurring patterns by engineer: insufficient data — Commit 03 is the first reviewed

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
