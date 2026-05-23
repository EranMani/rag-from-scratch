# Commit 56 Spec — `documentation`
> **Project:** rag-from-scratch · **Assignee:** Ryan · **Load only for the active commit.**
> **Note:** Formerly Commit 33, renumbered multiple times, now 56 (replan 2026-05-23). Scope updated: 10-topic curriculum (document_ingestion + langgraph_fundamentals replacing langchain_fundamentals); mastery-matched routing; AI-generated questions described.

---

### Commit 56 — `documentation`

**Commit message:** `docs: README, architecture overview, getting started guide`

**Body:**
Complete documentation pass for the portfolio project. Covers the full system including
the curriculum-driven adaptive assessment model, 10-topic 3-phase curriculum, mastery-matched
question routing, AI-generated hybrid questions, phase gate progression with visible unlock
moments, and the full UI.

`README.md`:
- Project description and north star
- Tech stack overview with reasoning
- Architecture diagram (ASCII or Mermaid)
- How to run locally (`docker compose up`)
- How to run with monitoring stack (`docker compose --profile monitoring up`)
- Environment variables (reference `.env.example`)
- Overview of the adaptive learning model: 10 topics, 3 phases, mastery-matched question routing,
  AI-generated questions, test-based scoring, phase gates, passive + active assessment, MCQ format

`GETTING_STARTED.md` (update existing file):
- Step-by-step local setup
- How to create an account and complete onboarding placement
- How to interact with the adaptive agent
- How the system tailors questions to your mastery level
- How to inspect your profile progression in the Knowledge Profile sidebar
- How the curriculum phases work — what topics are in each phase, what unlocks what,
  and what happens when you pass a gate (visual unlock + in-chat announcement)
- Note: the app itself is built on LangGraph — learners studying langgraph_fundamentals
  are learning the architecture of the system they are using

`docs/API_REFERENCE.md`:
- All endpoints: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`,
  `/api/profile/me`, `/api/chat`, `/api/ingest`, `/api/onboarding/status`,
  `/api/onboarding/diagnostic`, `/api/onboarding/complete`, `/api/health`, `/metrics`
- Request/response schemas

**Curriculum overview for README (10 topics, 3 phases):**
- Phase 1 — Foundations: embeddings_and_similarity, rag_pipeline_architecture
- Phase 2 — Core Components: chunking_strategies, vector_databases, retrieval_methods, context_and_prompting, document_ingestion
- Phase 3 — Production: evaluation_and_metrics, production_patterns, langgraph_fundamentals

**Assignee:** Ryan (`ryan.tech.writer.agent@gmail.com`)

**Files touched:**
- `README.md`
- `GETTING_STARTED.md`
- `docs/API_REFERENCE.md` (new)

**Depends on:** 55 (integration tests complete — documentation reflects final tested behavior)

**Testing — done when:**
- [ ] `README.md` has a working quickstart (someone with Docker can run it from scratch)
- [ ] All API endpoints documented with example request/response (including onboarding endpoints)
- [ ] Architecture diagram reflects the actual system
- [ ] Adaptive learning model section accurately describes the 10-topic curriculum, 3 phases, mastery-matched routing, AI-generated questions, and phase gates
- [ ] GETTING_STARTED.md explains the unlock progression a new user will experience
- [ ] `langchain_fundamentals` is not mentioned as an active topic anywhere in user-facing docs
