# Commit 33 Spec — `documentation`
> **Project:** rag-from-scratch · **Assignee:** Ryan · **Load only for the active commit.**

---

### Commit 33 — `documentation`

**Commit message:** `docs: README, architecture overview, getting started guide`

**Body:**
Complete documentation pass for the portfolio project. Covers the full system including
the curriculum-driven adaptive assessment model introduced in Commits 22–25.

`README.md`:
- Project description and north star
- Tech stack overview with reasoning
- Architecture diagram (ASCII or Mermaid)
- How to run locally (`docker compose up`)
- How to run with monitoring stack (`docker compose --profile monitoring up`)
- Environment variables (reference `.env.example`)
- Overview of the adaptive learning model (curriculum phases, test-based scoring)

`GETTING_STARTED.md` (update existing file):
- Step-by-step local setup
- How to create an account and test the adaptive agent
- How to inspect your profile progression
- How the curriculum phases work (what to expect as a new user)

`docs/API_REFERENCE.md`:
- All endpoints: `/api/auth/register`, `/api/auth/login`, `/api/auth/me`,
  `/api/profile/me`, `/api/chat`, `/api/ingest`, `/api/health`, `/metrics`
- Request/response schemas

**Assignee:** Ryan (`ryan.tech.writer.agent@gmail.com`)

**Files touched:**
- `README.md`
- `GETTING_STARTED.md`
- `docs/API_REFERENCE.md` (new)

**Depends on:** 31

**Testing — done when:**
- [ ] `README.md` has a working quickstart (someone with Docker can run it from scratch following the README)
- [ ] All API endpoints are documented with example request/response
- [ ] Architecture diagram reflects the actual system (LangGraph graph, curriculum assessment, profile flow, caching)
- [ ] Adaptive learning model section accurately describes the 3-phase curriculum and scoring model
