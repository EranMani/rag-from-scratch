# Commit 55 Spec — `integration-tests`
> **Project:** rag-from-scratch · **Assignee:** Rex + Nova · **Load only for the active commit.**
> **Note:** Formerly Commit 32, renumbered multiple times, now 55 (replan 2026-05-23). Scope updated: langchain_fundamentals slug removed; document_ingestion and langgraph_fundamentals added; mastery-matched routing (C46) and AI question generation (C52) added to test scenarios.

---

### Commit 55 — `integration-tests`

**Commit message:** `test: full graph integration tests and edge case coverage`

**Body:**
Integration tests that exercise the full LangGraph pipeline with real profile state
transitions. These are end-to-end tests, not unit tests — they verify that commits
07–52 work correctly as a system, including the curriculum-driven assessment,
10-slug scoring model (document_ingestion and langgraph_fundamentals replacing
langchain_fundamentals), mastery-matched question routing, scoring correctness fixes,
phase gate remediation, phase unlock announcements, and AI-generated questions.

Test scenarios:
- Fresh user (no profile): graph runs, test question administered, profile created with first scores
- Return user (existing profile): graph runs, test answer evaluated, delta merged into existing scores
- Assessment failure: graph takes fallback edge, profile not updated, answer still returned
- Anonymous user (`user_id=None`): graph runs, no profile writes, no error
- Empty knowledge base (no docs): graph returns graceful "no information" answer
- Phase gate check: user at Phase 1 passing threshold advances to Phase 2 topic testing
- Score migration: existing profile with pre-replan slugs migrates correctly on startup
- Mastery-matched routing (C46): novice user receives novice-difficulty questions; advanced user receives advanced-difficulty questions; fallback tier logic when target tier empty
- document_ingestion slug (C47–C48): slug is valid, Phase 2 eligible, selectable for intermediate users
- langgraph_fundamentals slug (C49–C50): slug is valid, Phase 3 eligible, selectable for advanced/expert users
- Bank expansion (C51): novice user is not served the same question twice across 3 consecutive sessions on the same topic
- AI question generation (C52): generated questions served when LLM succeeds; bank fallback when generation fails; generated_question_pool cached within session and not regenerated
- Scoring correctness (C39): single correct MCQ does NOT update topic score (session_question_count < 3 guard)
- Passive score isolation (C39): passive delta does not decay an existing MCQ-earned score
- Phase 1 remediation (C41): intermediate user with Phase 1 gap receives a Phase 1 question
- Gate passage detection (C43): mastery_level transition sets gate_just_passed correctly
- Unlock announcement (C43): gate_just_passed triggers announcement in generated response; clears after one turn

**Assignee:** Rex + Nova (coordinate — Rex owns profile assertions, Nova owns graph assertions)

**Files touched:**
- `tests/test_integration.py` (new)

**Depends on:** 52 (all features complete — mastery routing, curriculum restructure, question banks, AI generation)

**Testing — done when:**
- [ ] All test scenarios pass
- [ ] Tests do not require a live OpenAI key (Ollama or stubbed provider)
- [ ] Profile state in SQLite is verifiably correct after each scenario
- [ ] DB migration idempotency confirmed in a dedicated test scenario
- [ ] Mastery routing scenarios pass (novice → novice questions, advanced → advanced questions)
- [ ] document_ingestion and langgraph_fundamentals slugs are valid and selectable
- [ ] AI generation fallback scenario passes (validation failure → bank question, no error)
- [ ] Scoring correctness scenarios pass (single-question no-update, passive isolation)
- [ ] Gate remediation scenario passes (intermediate + Phase 1 gap)
