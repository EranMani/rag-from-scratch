# commit-protocol.md — RAG from Scratch
> The canonical build sequence. Every commit planned before any code is written.
> Each commit is atomic — one concern, one owner, one clear test gate.
> No commit is made without Team Lead approval. No two commits are combined.
> Status is maintained automatically by post_commit_next_step.py.

---

## Commit Index

| # | Name | Assignee | Status |
|---|---|---|---|
| 01 | auth-gate-on-ingest | backend | ✅ done · 2026-05-08 |
| 02 | config-and-naming-cleanup | backend | ✅ done · 2026-05-08 |
| 03 | wire-conversation-history | backend | ✅ done · 2026-05-08 |
| 04 | user-profile-db-schema | backend | ✅ done · 2026-05-09 |
| 05 | user-profile-service | backend | ✅ done · 2026-05-09 |
| 06 | user-profile-api | backend | ✅ done · 2026-05-09 |
| 07 | langgraph-state-schema | ai-engineer | ✅ done · 2026-05-09 |
| 08 | langgraph-retrieve-node | ai-engineer | ✅ done · 2026-05-09 |
| 09 | langgraph-generate-node | ai-engineer | ✅ done · 2026-05-09 |
| 10 | langgraph-graph-assembly | ai-engineer | ✅ done · 2026-05-10 |
| 11 | langgraph-graph-smoke-test | ai-engineer | ✅ done · 2026-05-10 |
| 12 | langgraph-assessment-scaffold | ai-engineer | ✅ done · 2026-05-10 |
| 13 | langgraph-assessment-llm | ai-engineer | ✅ done · 2026-05-10 |
| 14 | topic-scoring-service | backend | ✅ done · 2026-05-10 |
| 15 | fix-score-delta-semantics | backend | ✅ done · 2026-05-10 |
| 16 | profile-update-node | ai-engineer | ✅ done · 2026-05-10 |
| 17 | adaptive-prompt-templates | ai-engineer | ✅ done · 2026-05-10 |
| 18 | adaptive-graph-integration | ai-engineer | ✅ done · 2026-05-10 |
| 19 | profile-ui-panel | frontend | ✅ done · 2026-05-10 |
| 20 | dynamic-chat-ui | frontend | ✅ done · 2026-05-10 |
| 21 | production-compose | devops | ✅ done · 2026-05-10 |
| 22 | rag-curriculum-design | curriculum-specialist | ✅ done · 2026-05-11 |
| 23 | scoring-model-product-spec | product + curriculum-specialist | ✅ done · 2026-05-11 |
| 24 | assessment-engine-rewrite | ai-engineer | ✅ done · 2026-05-11 |
| 25 | profile-scoring-rewrite | backend | ✅ done · 2026-05-12 |
| 26 | nginx-config | devops | pending |
| 27 | aws-ec2-deployment | devops | pending |
| 28 | integration-tests | backend + ai-engineer | pending |
| 29 | documentation | tech-writer | pending |

---

## Parallel Groups

```
Wave A (Phase 1):    01 ∥ 02 ∥ 03  — all touch distinct files, no shared state
Wave B (Phase 3):    08 ∥ 09       — retrieve_node and generate_node are independent
Wave C (Phase 8):    28 (integration tests — single owner pair, no further split)
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
