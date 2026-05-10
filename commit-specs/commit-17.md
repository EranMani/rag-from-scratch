# Commit 17 Spec — `adaptive-prompt-templates`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**

---

### Commit 17 — `adaptive-prompt-templates`

**Commit message:** `feat: adaptive prompt templates per mastery level`

**Body:**
Creates the prompt template library used by `generate_node` (Commit 18 will wire
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
