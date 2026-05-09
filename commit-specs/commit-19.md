# Commit 19 Spec — `dynamic-chat-ui`
> **Project:** rag-from-scratch · **Assignee:** Aria · **Load only for the active commit.**

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
