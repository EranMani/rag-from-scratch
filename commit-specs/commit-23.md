# Commit 23 Spec — `integration-tests`
> **Project:** rag-from-scratch · **Assignee:** Rex + Nova · **Load only for the active commit.**

---

### Commit 23 — `integration-tests`

**Commit message:** `test: full graph integration tests and edge case coverage`

**Body:**
Integration tests that exercise the full LangGraph pipeline with real profile state
transitions. These are end-to-end tests, not unit tests — they verify that commits
07–17 work correctly as a system.

Test scenarios:
- Fresh user (no profile): graph runs, assessment runs, profile created with first scores
- Return user (existing profile): graph runs, assessment merges delta into existing scores
- Assessment failure: graph takes fallback edge, profile not updated, answer still returned
- Anonymous user (`user_id=None`): graph runs, no profile writes, no error
- Empty knowledge base (no docs): graph returns graceful "no information" answer

**Assignee:** Rex + Nova (coordinate — Rex owns profile assertions, Nova owns graph assertions)

**Files touched:**
- `tests/test_integration.py` (new)

**Depends on:** 17 (all features complete)

**Testing — done when:**
- [ ] All 5 test scenarios pass
- [ ] Tests do not require a live OpenAI key (Ollama or stubbed provider)
- [ ] Profile state in SQLite is verifiably correct after each scenario
