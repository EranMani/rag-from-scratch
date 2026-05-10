# Commit 18 Spec — `adaptive-graph-integration`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 18 — `adaptive-graph-integration`

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
