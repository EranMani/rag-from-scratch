# Commit 49 Spec — `documentation`
> **Project:** rag-from-scratch · **Assignee:** Ryan · **Load only for the active commit.**
> **Note:** This was formerly Commit 33, renumbered to 36 (replan 2026-05-19), then to 42 (replan 2026-05-19), then to 49 (replan 2026-05-20). Scope expanded: 9-topic curriculum (langchain_fundamentals added), phase unlock UX, scoring correctness model, and RAG Specialist agent.

---

### Commit 49 — `documentation`

**Commit message:** `docs: README, architecture overview, getting started guide`

**Body:**
Complete documentation pass for the portfolio project. Covers the full system including
the curriculum-driven adaptive assessment model, 9-topic 3-phase curriculum, phase gate
progression with visible unlock moments, and the full UI.

`README.md`:
- Project description and north star
- Tech stack overview with reasoning
- Architecture diagram (ASCII or Mermaid)
- How to run locally (`docker compose up`)
- How to run with monitoring stack (`docker compose --profile monitoring up`)
- Environment variables (reference `.env.example`)
- Overview of the adaptive learning model (9 topics, 3 phases, test-based scoring,
  phase gates, passive + active assessment, MCQ format)

`GETTING_STARTED.md` (update existing file):
- Step-by-step local setup
- How to create an account and complete onboarding placement
- How to interact with the adaptive agent
- How to inspect your profile progression in the Knowledge Profile sidebar
- How the curriculum phases work — what topics are in each phase, what unlocks what,
  and what happens when you pass a gate (visual unlock + in-chat announcement)

`docs/API_REFERENCE.md`:
- All endpoints: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`,
  `/api/profile/me`, `/api/chat`, `/api/ingest`, `/api/onboarding/status`,
  `/api/onboarding/diagnostic`, `/api/onboarding/complete`, `/api/health`, `/metrics`
- Request/response schemas

**Assignee:** Ryan (`ryan.tech.writer.agent@gmail.com`)

**Files touched:**
- `README.md`
- `GETTING_STARTED.md`
- `docs/API_REFERENCE.md` (new)

**Depends on:** 48 (integration tests complete — documentation reflects final tested behavior)

**Testing — done when:**
- [ ] `README.md` has a working quickstart (someone with Docker can run it from scratch)
- [ ] All API endpoints are documented with example request/response (including onboarding endpoints)
- [ ] Architecture diagram reflects the actual system
- [ ] Adaptive learning model section accurately describes the 9-topic curriculum, 3 phases, phase gates, and unlock moments
- [ ] GETTING_STARTED.md explains the unlock progression a new user will experience
