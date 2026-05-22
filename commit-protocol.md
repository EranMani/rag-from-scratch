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
| 26 | ui-foundation | frontend | ✅ done · 2026-05-17 |
| 27 | ui-header | frontend | ✅ done · 2026-05-17 |
| 28 | ui-chat | frontend | ✅ done · 2026-05-17 |
| 29 | ui-sidebar-admin | frontend | ✅ done · 2026-05-17 |
| 30 | ui-landing-page | frontend | ✅ done · 2026-05-19 |
| 30.5 | ui-landing-raf-guard | frontend | ✅ done · 2026-05-19 |
| 31 | ui-auth-pages | frontend | ✅ done · 2026-05-19 |
| 32 | ui-chat-shell | frontend | ✅ done · 2026-05-19 |
| 33 | question-bank-mcq | curriculum-specialist | ✅ done · 2026-05-19 |
| 34 | phase-gate-enforcement | ai-engineer | ✅ done · 2026-05-20 |
| 35 | mcq-assessment-engine | ai-engineer | ✅ done · 2026-05-20 |
| 35.5 | mcq-assessment-engine-fix | ai-engineer | ✅ done · 2026-05-20 (folded into 35) |
| 36 | onboarding-level-check | ai-engineer | ✅ done · 2026-05-20 |
| 37 | mcq-chat-ui | frontend | ✅ done · 2026-05-20 |
| 38 | progression-ui | frontend | ✅ done · 2026-05-20 |
| 38.5 | knowledge-profile-ui | frontend | ✅ done · 2026-05-20 |
| 39 | scoring-correctness | backend + ai-engineer | ✅ done · 2026-05-20 |
| 40 | langchain-curriculum | curriculum-specialist | ✅ done · 2026-05-20 |
| 41 | gate-remediation | ai-engineer | ✅ done · 2026-05-20 |
| 42 | rag-specialist-persona | claude | ✅ done · 2026-05-20 |
| 43 | phase-unlock-agent | ai-engineer | ✅ done · 2026-05-21 |
| 44 | phase-unlock-ui | frontend | ✅ done · 2026-05-21 |
| 45 | rag-specialist-content | rag-specialist | ✅ done · 2026-05-21 |
| 45.1 | novice-prompt-comprehension | ai-engineer | ✅ done · 2026-05-22 |
| 45.2 | open-question-delivery | ai-engineer | ✅ done · 2026-05-22 |
| 45.3 | question-type-balance | ai-engineer | ✅ done · 2026-05-22 |
| 45.4 | question-difficulty-degradation | ai-engineer | pending |
| 46 | nginx-config | devops | pending |
| 47 | aws-ec2-deployment | devops | pending |
| 48 | integration-tests | backend + ai-engineer | pending |
| 49 | documentation | tech-writer | pending |

---

## Parallel Groups

```
Wave A (Phase 1):    01 ∥ 02 ∥ 03  — all touch distinct files, no shared state
Wave B (Phase 3):    08 ∥ 09       — retrieve_node and generate_node are independent
Wave C (Phase 8):    28 (integration tests — single owner pair, no further split)
Wave D (Progression): 33 ∥ 34      — knowledge-base only (Lara) vs AI layer (Nova), no shared files
Wave E (Progression): 35 ∥ 36      — both depend on 34; 35 also needs 33
Wave F (Scoring):     39 ∥ 40      — scoring fixes (Rex+Nova) vs LangChain curriculum (Lara), no shared files
Wave G (Content):     44 ∥ 45      — phase unlock UI (Aria) vs RAG Specialist content (Lara+Specialist), no shared files
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
