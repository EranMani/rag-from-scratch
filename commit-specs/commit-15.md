# Commit 15 Spec — `profile-update-node`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

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

**Handoff consumed from Commit 05 (Mira flag):** `last_activity_at` MUST be set
explicitly: `update_profile(user_id, ..., last_activity_at=datetime.now(timezone.utc).isoformat())`
on every successful assessment turn. Without this, the UI profile panel (Commit 18)
displays a blank "Last active" field. This is a named deliverable of this commit.

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
- [ ] `last_activity_at` is set to a valid ISO 8601 timestamp after each successful turn
