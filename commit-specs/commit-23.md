# Commit 23 Spec — `scoring-model-product-spec`
> **Project:** rag-from-scratch · **Assignee:** Mira + Lara · **Load only for the active commit.**

---

### Commit 23 — `scoring-model-product-spec`

**Commit message:** `docs: scoring model product spec — curriculum-driven, test-answer-based`

**Body:**
Mira and Lara jointly produce the canonical product specification for how curriculum
test performance translates to topic scores and user_level. This spec is the
implementation contract that Nova (Commit 24) and Rex (Commit 25) must follow.
No application source code changes — documentation only.

**Questions this spec must answer with concrete, implementable rules:**
1. When does the agent administer a test question vs. answer a content question?
2. What does a test session look like from the user's perspective? Is it transparent?
3. How does test performance (correct / partial / incorrect) map to a score delta? Exact numbers.
4. What score threshold marks a topic as "passing" for phase gate advancement?
5. How does partial knowledge register — can a user be at 0.6 on a topic without passing it?
6. Does score decay exist? If so, when and at what rate?
7. How does `user_level` (novice / beginner / intermediate / advanced / expert) map to phase progress?

**Assignee:** Mira (product perspective) + Lara (curriculum and scoring expertise)

**Files touched:**
- `docs/scoring-model.md` (new) — canonical product spec, consumed as implementation contract by Nova and Rex

**Depends on:** Commit 22 (`knowledge-base/curriculum/gates.md` must exist — phase thresholds defined by Lara feed this spec)

**Testing — done when:**
- [ ] `docs/scoring-model.md` answers all 7 questions above
- [ ] Score delta formula is numeric and unambiguous — Nova and Rex can implement without follow-up questions
- [ ] Phase gate thresholds in this spec are consistent with `knowledge-base/curriculum/gates.md`
- [ ] `user_level` mapping is explicit: which score ranges or phase positions correspond to which level labels
- [ ] No application source code was modified
