# Commit 48 Spec — `integration-tests`
> **Project:** rag-from-scratch · **Assignee:** Rex + Nova · **Load only for the active commit.**
> **Note:** This was formerly Commit 32, renumbered to 35 (replan 2026-05-19), then to 41 (replan 2026-05-19), then to 48 (replan 2026-05-20 — 7 learning flow commits inserted). Scope expanded to cover scoring correctness fixes (Commit 39), gate remediation (Commit 41), phase unlock agent (Commit 43), and langchain_fundamentals slug.

---

### Commit 48 — `integration-tests`

**Commit message:** `test: full graph integration tests and edge case coverage`

**Body:**
Integration tests that exercise the full LangGraph pipeline with real profile state
transitions. These are end-to-end tests, not unit tests — they verify that commits
07–45 work correctly as a system, including the curriculum-driven assessment,
9-slug scoring model (now including langchain_fundamentals), scoring correctness
fixes, phase gate remediation, and phase unlock announcements.

Test scenarios:
- Fresh user (no profile): graph runs, test question administered, profile created with first scores
- Return user (existing profile): graph runs, test answer evaluated, delta merged into existing scores
- Assessment failure: graph takes fallback edge, profile not updated, answer still returned
- Anonymous user (`user_id=None`): graph runs, no profile writes, no error
- Empty knowledge base (no docs): graph returns graceful "no information" answer
- Phase gate check: user at Phase 1 passing threshold advances to Phase 2 topic testing
- Score migration: existing profile with pre-replan slugs migrates correctly on startup
- Scoring correctness (Commit 39): single correct MCQ does NOT update topic score (session_question_count < 3 guard)
- Passive score isolation (Commit 39): passive delta does not decay an existing MCQ-earned score
- Phase 1 remediation (Commit 41): intermediate user with Phase 1 gap receives a Phase 1 question
- langchain_fundamentals slug (Commit 41): slug is valid, Phase 2 eligible, selectable for intermediate users
- Gate passage detection (Commit 43): mastery_level transition sets gate_just_passed correctly
- Unlock announcement (Commit 43): gate_just_passed triggers announcement in generated response; clears after one turn

**Assignee:** Rex + Nova (coordinate — Rex owns profile assertions, Nova owns graph assertions)

**Files touched:**
- `tests/test_integration.py` (new)

**Depends on:** 45 (all features and content complete)

**Testing — done when:**
- [ ] All test scenarios pass
- [ ] Tests do not require a live OpenAI key (Ollama or stubbed provider)
- [ ] Profile state in SQLite is verifiably correct after each scenario
- [ ] DB migration idempotency confirmed in a dedicated test scenario
- [ ] Scoring correctness scenarios pass (single-question no-update, passive isolation)
- [ ] Gate remediation scenario passes (intermediate + Phase 1 gap)
