# Commit 49.1 Spec — `slug-add-langgraph`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**
> **Note:** Micro-commit inserted after C49. C49 (Lara) added `langgraph_fundamentals` to
> the curriculum-map and topic-slugs.json as a Phase 3 topic. This commit makes the matching
> src/ changes so the adaptive engine recognises `langgraph_fundamentals` as a valid Phase 3
> topic. Without this, the Phase 3 gate is checked against an incomplete topic set, and
> `langgraph_fundamentals` questions (added in C50) will never be surfaced.

---

### Commit 49.1 — `slug-add-langgraph`

**Commit message:** `feat(EranMani): add langgraph_fundamentals to src slug registries`

**Body:**
Requested by Eran Mani, our team lead: C49 added `langgraph_fundamentals` to the curriculum
as a Phase 3 topic. This commit makes the matching src/ changes — five files — so the
assessment engine and scoring layer treat `langgraph_fundamentals` as a registered Phase 3
topic. Without this, the Phase 3 gate evaluates only `evaluation_and_metrics` and
`production_patterns`, ignoring `langgraph_fundamentals` entirely.

**Assignee:** Nova (src/ files only — no knowledge-base/ files)

**Depends on:** 49 (langgraph_fundamentals must exist in curriculum-map.md before registering it in src/)

**Files touched:**
- `src/agents/state.py` — `TopicScoresDelta`: add `langgraph_fundamentals: float = 0.0` after `production_patterns`; `VALID_MODULE_SLUGS`: add `"langgraph_fundamentals"`
- `src/app/profile/scoring.py` — `PHASE_3_TOPICS`: add `"langgraph_fundamentals"` to the frozenset
- `src/agents/assessment/question_selection.py` — `_ORDERED_SLUGS`: add `"langgraph_fundamentals"` after `"production_patterns"`
- `src/app/ui.py` — `_PROGRESS_PHASES` "Production" entry: add `"langgraph_fundamentals"` to the list
- `src/agents/prompts/assessment.py` — valid topic slugs line: add `langgraph_fundamentals` to the comma-separated list

**This is an additive find-and-add commit — no logic changes.** Every Phase 3 slug registry
in src/ gets one new entry. No new branches, no new conditions, no new functions.

**Testing — done when:**
- [ ] `TopicScoresDelta` in `state.py` has `langgraph_fundamentals: float = 0.0`
- [ ] `VALID_MODULE_SLUGS` in `state.py` contains `"langgraph_fundamentals"`
- [ ] `PHASE_3_TOPICS` in `scoring.py` contains `"langgraph_fundamentals"` (frozenset of 3)
- [ ] `_ORDERED_SLUGS` in `question_selection.py` contains `"langgraph_fundamentals"` after `"production_patterns"`
- [ ] `_PROGRESS_PHASES` "Production" entry in `ui.py` contains `"langgraph_fundamentals"`
- [ ] Assessment prompt in `assessment.py` references `langgraph_fundamentals` in slug list
- [ ] Full test suite passes (`pytest`)
- [ ] No knowledge-base/ files touched

**Gate triage:**
- Viktor: Yes — slug registration change affects Phase 3 gate logic and assessment routing. Quick review.
- Sage: No — no auth, no secrets, no user input boundary.
- Quinn: No — no new routes or services; behavior is slug-list addition only.
- Mira: No — no user-visible behavior change until C50 adds questions.
