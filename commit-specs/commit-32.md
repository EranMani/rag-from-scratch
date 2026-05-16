# Commit 32 Spec — `integration-tests`
> **Project:** rag-from-scratch · **Assignee:** Rex + Nova · **Load only for the active commit.**

---

### Commit 32 — `integration-tests`

**Commit message:** `test: full graph integration tests and edge case coverage`

**Body:**
Integration tests that exercise the full LangGraph pipeline with real profile state
transitions. These are end-to-end tests, not unit tests — they verify that commits
07–25 work correctly as a system, including the curriculum-driven assessment and
8-slug scoring model.

Test scenarios:
- Fresh user (no profile): graph runs, test question administered, profile created with first scores
- Return user (existing profile): graph runs, test answer evaluated, delta merged into existing scores
- Assessment failure: graph takes fallback edge, profile not updated, answer still returned
- Anonymous user (`user_id=None`): graph runs, no profile writes, no error
- Empty knowledge base (no docs): graph returns graceful "no information" answer
- Phase gate check: user at Phase 1 passing threshold advances to Phase 2 topic testing
- Score migration: existing profile with pre-replan slugs migrates correctly on startup

**Assignee:** Rex + Nova (coordinate — Rex owns profile assertions, Nova owns graph assertions)

**Files touched:**
- `tests/test_integration.py` (new)

**Depends on:** 25 (all features complete)

**Testing — done when:**
- [ ] All 7 test scenarios pass
- [ ] Tests do not require a live OpenAI key (Ollama or stubbed provider)
- [ ] Profile state in SQLite is verifiably correct after each scenario
- [ ] DB migration idempotency confirmed in a dedicated test scenario
