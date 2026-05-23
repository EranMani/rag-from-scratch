# Commit 47.1 Spec — `slug-swap-document-ingestion`
> **Project:** rag-from-scratch · **Assignee:** Nova · **Load only for the active commit.**
> **Note:** Micro-commit inserted after C47. C47 (Lara) archives langchain_fundamentals from knowledge-base/ and adds document_ingestion to the curriculum. This commit makes the matching src/ changes so the adaptive engine recognises document_ingestion as a valid Phase 2 topic and stops gating Phase 2 on the now-question-less langchain_fundamentals slug.

---

### Commit 47.1 — `slug-swap-document-ingestion`

**Commit message:** `feat(EranMani): swap langchain_fundamentals → document_ingestion in src slug registries`

**Body:**
Requested by Eran Mani, our team lead: C47 archived `langchain_fundamentals` from the curriculum and replaced it with `document_ingestion`. This commit makes the matching src/ changes — five files — so the assessment engine and scoring layer treat `document_ingestion` as a registered Phase 2 topic. Without this, Phase 2 advancement is permanently blocked (langchain_fundamentals has no questions) and document_ingestion is invisible to the engine.

**Assignee:** Nova (src/ files only — no knowledge-base/ files)

**Depends on:** 47 (document_ingestion must exist in curriculum-map.md before registering it in src/)

**Files touched:**
- `src/agents/state.py` — `VALID_MODULE_SLUGS`: remove `"langchain_fundamentals"`, add `"document_ingestion"`; `TopicScores`: remove `langchain_fundamentals: float = 0.0`, add `document_ingestion: float = 0.0`
- `src/app/profile/scoring.py` — `PHASE_2_TOPICS`: remove `"langchain_fundamentals"`, add `"document_ingestion"`
- `src/agents/assessment/question_selection.py` — `_ORDERED_SLUGS`: replace `"langchain_fundamentals"` with `"document_ingestion"` in the same Phase 2 position
- `src/app/ui.py` — Core topics list: replace `"langchain_fundamentals"` with `"document_ingestion"`
- `src/agents/prompts/assessment.py` — slug list in assessment prompt: replace `langchain_fundamentals` with `document_ingestion`

**This is a find-and-replace commit — no logic changes.** Every occurrence of `langchain_fundamentals` in src/ is replaced with `document_ingestion`. No new branches, no new conditions, no new functions.

**Testing — done when:**
- [ ] `VALID_MODULE_SLUGS` in `state.py` contains `"document_ingestion"` and does not contain `"langchain_fundamentals"`
- [ ] `TopicScores` in `state.py` has `document_ingestion: float = 0.0` and no `langchain_fundamentals` field
- [ ] `PHASE_2_TOPICS` in `scoring.py` contains `"document_ingestion"` and not `"langchain_fundamentals"`
- [ ] `_ORDERED_SLUGS` in `question_selection.py` contains `"document_ingestion"` in Phase 2 position, no `"langchain_fundamentals"`
- [ ] Core topics list in `ui.py` contains `"document_ingestion"`, not `"langchain_fundamentals"`
- [ ] Assessment prompt in `assessment.py` references `document_ingestion`, not `langchain_fundamentals`
- [ ] Full test suite passes (`pytest`)
- [ ] No knowledge-base/ files touched

**Gate triage:**
- Viktor: Yes — slug registration change affects assessment routing logic. Quick review.
- Sage: No — no auth, no secrets, no user input boundary.
- Quinn: No — no new routes or services; behavior is slug-list change only.
- Mira: No — no user-visible behavior change (topic name change will be reflected once questions exist in C48).
