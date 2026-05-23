# Commit 46 Spec — `mastery-matched-routing`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**
> **Note:** New commit added in replan 2026-05-23 — adaptive engine priority over infra. Former nginx-config (old 46) renumbered to 53.

---

### Commit 46 — `mastery-matched-routing`

**Commit message:** `feat(EranMani): filter question pool by user mastery level in select_test_question`

**Body:**
Requested by Eran Mani, our team lead: route assessment questions to the user's current mastery level. A novice user should receive novice-tier questions; an advanced user receives advanced-tier questions. The `mastery_level` field already exists in `AgentState` and the `difficulty:` field already exists in every question file — this commit wires the two together.

**Assignee:** Nova

**Files touched:**
- `src/rag/graph/nodes/test_delivery.py` — filter question pool by mastery_level before sampling
- `src/rag/graph/nodes/question_selection.py` — pass mastery_level to question loader if applicable
- `tests/test_mastery_routing.py` (new) — test scenarios for tier-matched delivery

**Depends on:** 45.6 (all prior features stable)

**Design constraints:**
- The mapping is direct: mastery_level `"novice"` → difficulty `"novice"`, etc.
- If no questions exist at the user's mastery tier for a given slug, fall back to the nearest available tier (lower first, then higher). Do not return an empty question — always deliver something.
- If `mastery_level` is `None` or unrecognized, fall back to unrestricted sampling (current behavior).
- No changes to `AgentState` schema — `mastery_level` already exists.
- No changes to knowledge-base files.

**Testing — done when:**
- [ ] Novice user (`mastery_level="novice"`) receives only novice-difficulty questions
- [ ] Advanced user (`mastery_level="advanced"`) receives advanced-difficulty questions
- [ ] Fallback tier logic: if no questions at target tier, nearest tier is served (not an error)
- [ ] `mastery_level=None` preserves prior unrestricted behavior
- [ ] All existing tests still pass
