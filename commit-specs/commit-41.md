# Commit 41 Spec — `gate-remediation`
> **Project:** rag-from-scratch · **Assignee:** ai-engineer (Nova) · **Load only for the active commit.**
> **Note:** Added in replan 2026-05-20 — phase gate design gap: intermediate users permanently locked out of Phase 1 remediation; also wires langchain_fundamentals slug from Commit 40.

---

### Commit 41 — `gate-remediation`

**Commit message:** `fix: gate remediation — intermediate Phase 1 re-testing, langchain slug wiring, session counter`

**Body:**
Three fixes to the gate and topic-selection layer, plus wiring the new LangChain slug
from Commit 40 into the code layer.

**Fix 1 — Wire langchain_fundamentals into code (Commit 40 handoff from Lara)**
- `src/agents/state.py`: add `"langchain_fundamentals"` to `VALID_MODULE_SLUGS`
- `src/app/profile/scoring.py`: add `"langchain_fundamentals"` to `PHASE_2_TOPICS`
- `src/agents/nodes/assess.py`: add `"langchain_fundamentals"` to `_ORDERED_SLUGS`
  at the end of the Phase 2 block (before `evaluation_and_metrics`)

**Fix 2 — Phase 1 gap remediation for intermediate users**
`src/agents/nodes/assess.py`: the current `_select_test_slug` maps `intermediate`
users exclusively to `PHASE_2_TOPICS`. Once Phase 1 is passed, no Phase 1 question
can ever be served — even when `identified_gaps` contains a Phase 1 slug. A user who
scraped 0.70 and shows Phase 1 weakness through natural questions receives no
targeted help.

Fix: add a gap-remediation exception. If `identified_gaps` contains a Phase 1 slug
AND `user_level == "intermediate"`, that slug is eligible for selection regardless of
the phase mapping. The phase gate still governs progression (Phase 2 remains the
default for intermediate users). New priority order in `_select_test_slug`:
  1. Phase 1 slugs in identified_gaps where user_level == "intermediate" (remediation)
  2. First gap slug eligible for user's current phase
  3. Canonical ordering within eligible phase (fallback)

**Fix 3 — Wire session_question_count from Commit 39**
- `src/agents/state.py`: add `session_question_counts: dict[str, int]` field to
  `AgentState` — tracks how many MCQ answers have been evaluated per topic this session.
- `src/agents/nodes/assess.py`: in evaluation mode (`_evaluate_answer`), emit
  a `session_question_counts` update incrementing `pending_slug` by 1.
- `src/agents/nodes/update_profile.py`: read per-topic counts from state and pass
  the count for the active topic to `compute_topic_scores` via the
  `session_question_count` parameter added in Commit 39.

**Fix 4 — Score-proximity feedback in generate_node**
`src/agents/nodes/generate.py`: when building the adaptive prompt context, check if
any Phase 1 or Phase 2 topic has a score between 0.60 and 0.69 (within reach of the
0.70 gate threshold). If so, add a proximity hint to the system context:
  "Note: user is close to passing [topic] (score: X.XX, threshold: 0.70).
  Reinforce this topic where natural."
This gives the generate node visibility into near-passing topics without touching
the scoring formula.

**Assignee:** Nova

**Files touched:**
- `src/agents/state.py` — add `langchain_fundamentals` to VALID_MODULE_SLUGS; add `session_question_counts` field
- `src/app/profile/scoring.py` — add `langchain_fundamentals` to PHASE_2_TOPICS
- `src/agents/nodes/assess.py` — add slug to `_ORDERED_SLUGS`; fix `_select_test_slug` remediation logic; emit `session_question_counts` increments
- `src/agents/nodes/update_profile.py` — pass per-topic session count to `compute_topic_scores`
- `src/agents/nodes/generate.py` — add proximity hint to adaptive prompt context

**Depends on:** 39 (scoring guard in place), 40 (LangChain slug exists in knowledge-base)

**Testing — done when:**
- [ ] `langchain_fundamentals` slug passes VALID_MODULE_SLUGS validation without error
- [ ] Intermediate user with `identified_gaps=["embeddings_and_similarity"]` receives a Phase 1 question
- [ ] Intermediate user with no gaps still receives Phase 2 questions
- [ ] Topic answered correctly 3 times in one session updates the score; 1 time does not
- [ ] Proximity hint appears in generate_node context when a topic is between 0.60 and 0.69
- [ ] Existing test suite passes
