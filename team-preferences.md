# team-preferences.md

> Claude reads this file at every session boot, immediately after project-state.json.
> These preferences tune agent behavior for this specific project and Team Lead.
> Edit any section at any time — Claude propagates changes to affected agents
> at the start of the next commit loop iteration.
>
> Last updated: 2026-05-09

---

## Project Context

```
Project name:      rag-from-scratch
Team Lead:         EranMani
Phase:             existing codebase — feature build
Deadline pressure: low (learning-paced, quality over speed)
Public-facing:     yes (portfolio on AWS EC2 + custom domain)
```

---

## Viktor — Code Review Calibration

```
Overall strictness: balanced
```

| Concern type       | Behavior | Notes |
|--------------------|----------|-------|
| Style / formatting | comment  | project uses no linter currently — flag obvious issues |
| Typing discipline  | concern  | strict on all new code; existing untyped code is not retroactively flagged |
| Error handling     | concern  | strict — public-facing portfolio app |
| Test coverage      | comment  | Quinn handles coverage bar; Viktor flags structural gaps only |
| Documentation      | ignore   | Ryan handles docs |
| Performance        | concern  | flag O(n²) and above; flag blocking calls in async routes |
| Concurrency        | concern  | always flag — async/thread interactions are a known risk area |

```
Additional Viktor instructions:
Cross-domain touches (Nova writing to Rex's files, or Aria consuming unstable contracts)
must be explicitly flagged, not silently approved. The commit spec identifies any
cross-domain touches in advance — Viktor verifies they match what was declared.
LangGraph node code: verify every node writes only to its declared AgentState keys.
No node should write keys it doesn't own.
```

---

## Sage — Security Calibration

```
System exposure:  fully-public (AWS EC2 + custom domain)
Compliance req:   none
```

| Finding level | Behavior   | Notes |
|---------------|------------|-------|
| CRITICAL      | hard block | always |
| HIGH          | block      | public routes; flag on internal-only routes |
| MEDIUM        | flag       | bundle into approval prompt |
| LOW           | bundle     | bundle into approval prompt |
| INFO          | suppress   | unless explicitly asked |

```
Additional Sage instructions:
JWT secret: flag any commit that could result in the default "dev-only-change-in-production"
secret being used in production. The .env.prod.example validation guard in Commit 22
is the mitigation — verify it ships correctly.
OpenAI API key: must come from env only. Flag any hardcoding immediately.
/api/ingest auth gate: verify it stays present after any refactor of documents.py.
Monitoring endpoints (Grafana, Kibana, Prometheus): must not be publicly accessible
without auth — verify nginx config in Commit 21 gates them correctly.
```

---

## Quinn — Coverage Calibration

```
Coverage bar: pragmatic
```

| Coverage type     | Behavior | Notes |
|-------------------|----------|-------|
| Happy path        | required | all new services and routes |
| Edge cases        | required | profile service (null fields, empty scores), LangGraph fallback edge |
| Error paths       | required | assessment failure, circuit breaker open, unauthenticated requests |
| Integration tests | required | after Phase 3 and Phase 4 complete (Commits 11, 23) |
| Performance tests | optional | not required in this phase |

```
Additional Quinn instructions:
Tests ship with the code they test — not in a separate end-of-project batch.
Commits 05 (profile service) and 14 (scoring service) must include tests in the same commit.
Commit 11 (graph smoke test) is a hard gate before Phase 4 begins.
Commit 23 (integration tests) covers the full adaptive pipeline end-to-end.
```

---

## Mira — Product Review Calibration

```
Invocation rule: dynamic (not every commit)
```

Invoke Mira when the commit introduces or changes **user-facing behavior**:
- New or modified API endpoints (shape, fields, error codes)
- UI changes (layout, interaction model, displayed data)
- Data the user sees (profile fields, response fields, status badges)
- Any creative design decision about what the user experiences

Skip Mira on internal plumbing: state schema files, test-only commits, pure infra
config, scoring pure functions, LangGraph node internals, worklog/doc-only commits.

---

## Model Assignments

```
Haiku  (fast, low cost):     Ryan, worklog-only updates, GLOSSARY one-liners
Sonnet (default, balanced):  Rex, Nova, Aria, Adam — all implementation work
Opus   (deep reasoning):     Viktor and Sage — selectively, by commit complexity (see below)
```

Specify at Agent invocation time via `model: "haiku" | "sonnet" | "opus"`.
Default if unspecified: Sonnet.

### Viktor model tier rule

| Commit type | Viktor model |
|---|---|
| Schema / TypedDict / Pydantic models / constants | Sonnet |
| Single-domain CRUD routes, simple nodes, test files | Sonnet |
| Multi-domain wiring, cross-agent contracts, async patterns | Opus |
| Auth logic, JWT, secrets, security-sensitive code | Opus |
| Complex state machines, concurrent patterns, streaming | Opus |

Default to **Sonnet**. Upgrade to **Opus** only when the commit crosses multiple domains,
touches auth/secrets, or involves subtle async/concurrent logic where shallow review misses
the real risk.

### Ryan context rule

Do NOT pass Ryan the full `LEARNING_LOG.md`. Instead, pass:
1. The format template inline in the prompt (copy from the Entry Format Reference section)
2. The diff + commit context
3. Instruction to `Write` (append) to the file — not to read it first

LEARNING_LOG.md grows with every commit. Reading the whole file on Haiku for a one-liner
entry wastes 50k+ tokens per commit. The format template in the prompt is sufficient.

---

## Worklog Archive Trigger

```
Archive threshold: >3 completed sessions per agent (not 5)
Trigger:           /archive-worklog [agent-name]
Timing:            at the start of the session following the threshold being crossed
```

Agents most likely to hit threshold first: Rex (Phases 1–3), Nova (Phases 2–4).

---

## Parallelization Preferences

```
Quality gate wave:       always parallel (Viktor + Sage + Quinn simultaneously)
Commit parallelization:  use when possible (Wave A: commits 01/02/03, Wave B: 08/09)
Parallel commits:        use worktree isolation (isolation: "worktree") to prevent file conflicts
```

---

## Communication Preferences

```
Approval prompt length:  normal
Status report length:    normal
Escalation threshold:    low — escalate early rather than resolve autonomously
```

```
Tone preference:
Direct. No excessive preamble. Lead with what decision the Team Lead needs to make.
Each commit approval prompt should include: what was built, what the test gate showed,
any concerns from the quality gate, and a clear "Approve to commit?" question.
Team Lead is learning — explain non-obvious technical decisions briefly when surfacing them.
```

---

## Quality Gate Pre-Brief (for implementors)

When invoking an implementor agent (Nova, Rex, Aria, Adam), include a short
"Viktor will check:" list in the invocation prompt so the agent anticipates common
blocking findings before the first gate pass.

Standard pre-brief for all implementors:
```
Viktor will check:
- All collection types are explicitly typed (list[X], not bare list; dict[K,V], not bare dict)
- All string fields with finite valid values use Literal[...], not str
- Any documented constraint is enforced in code (frozenset, validator, etc.) — not just in a docstring
- A test file exists with all spec gate conditions covered
- No domain boundary violations (node writes only declared AgentState keys)
```

Add commit-specific items where the spec has known sharp edges.
This costs ~100 tokens per invocation and routinely prevents an entire Viktor block + re-review cycle.

---

## Orchestrator Read Discipline

Do NOT read files speculatively in the main context. Read a file only at the moment
you need its content to make a decision or write an edit.

Wrong: reading ARCHITECTURE.md + DECISIONS.md + GLOSSARY.md at session start "just in case"
Right: reading ARCHITECTURE.md immediately before editing it, then GLOSSARY.md immediately before editing it

Each speculative file read adds to the running conversation history and compounds cost
across all subsequent messages in the session.

---

## Scope and Speed Tradeoffs

```
When tests fail mid-loop:     stop and fix before proceeding
When Viktor raises a concern: assess severity first, then decide
When a commit takes too long: flag at 2x estimate
Scope overflow policy:        log and stop — Team Lead decides whether to expand
```

---

## Agent Names for This Project

```
Orchestrator:   Claude
Backend:        Rex
DevOps:         Adam
Frontend:       Aria
AI Engineer:    Nova
Product:        Mira
Code Reviewer:  Viktor
Security:       Sage
QA:             Quinn
Tech Writer:    Ryan
```

---

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-05-08 | Initial creation | /init protocol complete |
| 2026-05-09 | Added Mira dynamic invocation rule | Only invoke on user-facing commits to reduce token cost |
| 2026-05-09 | Added Model Assignments section | Haiku/Sonnet/Opus tiering to reduce cost without quality loss |
| 2026-05-09 | Added Worklog Archive Trigger section | Lower threshold (3 sessions) for proactive archiving |
| 2026-05-09 | Added worktree isolation note to Parallelization | Needed for Wave B (commits 08+09) |
| 2026-05-09 | Viktor model tier rule added | Two Opus passes on Commit 07 schema cost 107k tokens — Opus only for complex/auth/concurrent commits |
| 2026-05-09 | Ryan context rule added | Ryan read full LEARNING_LOG (55k tokens) just to append one entry — pass format template inline instead |
| 2026-05-09 | Quality Gate Pre-Brief section added | Nova ran twice on Commit 07 — pre-brief prevents Viktor blocks by front-loading what he checks |
| 2026-05-09 | Orchestrator Read Discipline section added | Speculative file reads compound across session history — read only when about to edit |
