# commit-protocol.md — [PROJECT NAME]
> The canonical build sequence. Every commit planned before any code is written.
> Each commit is atomic — one concern, one owner, one clear test gate.
> No commit is made without Team Lead approval. No two commits are combined.
> Status is maintained automatically by post_commit_next_step.py.

---

## Commit Index

| # | Name | Assignee | Status |
|---|---|---|---|
| 01 | project-foundation | devops | pending |
| 02 | database-models | backend | pending |
| 03 | schema-migrations | backend | pending |
| 04 | request-response-schemas | backend | pending |
| 05 | core-dependencies | backend | pending |
| 06 | [domain]-service-routes | backend | pending |
| 07 | [domain]-service-routes | backend | pending |
| 08 | cache-layer | backend | pending |
| 09 | background-worker | backend | pending |
| 10 | worker-dlq | backend | pending |
| 11 | [ai-feature-foundation] | ai-engineer | pending |
| 12 | [ai-tools] | ai-engineer | pending |
| 13 | [ai-route] | ai-engineer | pending |
| 14 | circuit-breaker | ai-engineer | pending |
| 15 | load-balancer-rate-limiter | devops | pending |
| 16 | test-infrastructure | backend | pending |
| 17 | unit-tests-[domain] | backend | pending |
| 18 | integration-tests-[domain] | backend | pending |
| 19 | agent-tool-tests | ai-engineer | pending |
| 20 | worker-tests | backend | pending |

## Parallel Groups

The following commits can execute simultaneously. Claude invokes agents in parallel
for each wave. All agents in a wave must complete before the next wave begins.

```
Wave A (after commit 15): 16 test-infrastructure [backend]
Wave B (after 16):        17 unit-tests + 19 agent-tool-tests [backend ∥ ai-engineer]
Wave C (after 17):        18 integration-tests [backend]
Wave D (after 19):        [any independent ai-engineer test commits] [ai-engineer ∥ ai-engineer]
Wave E (after 18):        20 worker-tests [backend]
```

---

## Commits in Detail

---

### Commit 01 — `project-foundation`

**Commit message:** `chore: project foundation — docker, env, folder structure`

**Body:**
Sets up the full project skeleton before any application code is written.
Everything a developer needs to run the project locally from a clean clone.

Includes:
- docker-compose.yml / equivalent container orchestration
- Dockerfile / application image
- .env.example — all required env vars documented
- src/ folder structure (adapt to project tech stack)
- main.py / app entry point — bare app with health check route
- pyproject.toml / package.json / equivalent dependency manifest
- .gitignore
- Makefile / equivalent developer-experience commands

**Assignee:** DevOps Engineer

**Testing — done when:**
- [ ] `make up` (or equivalent) starts all services with no errors
- [ ] Health check endpoint returns 200 OK
- [ ] All required services (DB, cache, etc.) are reachable from the app container
- [ ] .env.example contains every variable referenced in code

---

### Commit 02 — `database-models`

**Commit message:** `feat: [ORM] database models ([Entity1], [Entity2], ...)`

**Body:**
Defines the full relational schema as ORM models.

[Customize: list your entities and their key fields]

**Assignee:** Backend Engineer

**Testing — done when:**
- [ ] All models import without errors
- [ ] Relationships are navigable (e.g. `entity.related`)
- [ ] No circular imports

---

### Commit 03 — `schema-migrations`

**Commit message:** `chore: [migration tool] setup and initial schema migration`

**Assignee:** Backend Engineer

**Testing — done when:**
- [ ] Migration runs without errors against a fresh database
- [ ] All tables exist after migration
- [ ] Downgrade cleanly removes the tables

---

[Continue adding commits following the same pattern. Each commit needs:]
[- Commit message (exact, final)]
[- Body (what it includes)]
[- Assignee]
[- Testing gate (checkbox list, each verifiable)]

---

## Protocol Rules

1. Commits are made in the order listed above. No skipping.
2. Each commit requires Team Lead approval before it is made.
3. The assignee does the work. Input needed from another agent → handoff note.
4. Testing gate must be fully satisfied before Team Lead approves.
5. If a commit reveals a prior commit needs changing, surface to Team Lead first.
6. ARCHITECTURE.md is updated if a decision changes during implementation.
7. Scope overflow is logged immediately — never silently absorbed.
