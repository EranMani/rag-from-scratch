# commit-protocol.md — RAG from Scratch
> The canonical build sequence. Every commit planned before any code is written.
> Each commit is atomic — one concern, one owner, one clear test gate.
> No commit is made without Team Lead approval. No two commits are combined.
> Status is maintained automatically by post_commit_next_step.py.

---

## Commit Index

| # | Name | Assignee | Status |
|---|---|---|---|
| 01 | auth-gate-on-ingest | backend | pending |
| 02 | config-and-naming-cleanup | backend | pending |
| 03 | wire-conversation-history | backend | pending |
| 04 | user-profile-db-schema | backend | pending |
| 05 | user-profile-service | backend | pending |
| 06 | user-profile-api | backend | pending |
| 07 | langgraph-state-schema | ai-engineer | pending |
| 08 | langgraph-retrieve-node | ai-engineer | pending |
| 09 | langgraph-generate-node | ai-engineer | pending |
| 10 | langgraph-graph-assembly | ai-engineer | pending |
| 11 | langgraph-graph-smoke-test | ai-engineer | pending |
| 12 | langgraph-assessment-scaffold | ai-engineer | pending |
| 13 | langgraph-assessment-llm | ai-engineer | pending |
| 14 | topic-scoring-service | backend | pending |
| 15 | profile-update-node | ai-engineer | pending |
| 16 | adaptive-prompt-templates | ai-engineer | pending |
| 17 | adaptive-graph-integration | ai-engineer | pending |
| 18 | profile-ui-panel | frontend | pending |
| 19 | dynamic-chat-ui | frontend | pending |
| 20 | production-compose | devops | pending |
| 21 | nginx-config | devops | pending |
| 22 | aws-ec2-deployment | devops | pending |
| 23 | integration-tests | backend + ai-engineer | pending |
| 24 | documentation | tech-writer | pending |

---

## Parallel Groups

```
Wave A (Phase 1):    01 ∥ 02 ∥ 03  — all touch distinct files, no shared state
Wave B (Phase 3):    08 ∥ 09       — retrieve_node and generate_node are independent
Wave C (Phase 7):    23 (integration tests — single owner pair, no further split)
```

---

## Commit Specs

Full specifications for each pending commit live in `commit-specs/`.
Load `commit-specs/commit-XX.md` (active commit only) when executing a step.
Completed commit specs do not need to be loaded.

---

## Protocol Rules

1. Commits are made in the order listed. No skipping.
2. Each commit requires Team Lead approval before it is made.
3. The assignee does the work. Cross-domain touches are flagged as handoffs before the commit, not discovered after.
4. Testing gate must be fully satisfied before approval is surfaced.
5. If a commit reveals a prior commit needs changing — stop. Surface to Team Lead first.
6. `ARCHITECTURE.md`, `DECISIONS.md`, `GLOSSARY.md` are updated by Claude before every approval prompt.
7. Scope overflow is logged immediately — never silently absorbed.
8. Viktor reviews every commit. Sage reviews any commit touching auth, secrets, or external API calls.
