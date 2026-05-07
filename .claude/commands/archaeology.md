# /archaeology — Existing Codebase Onboarding Protocol

Triggered when: the project already has code and `/init` detects an existing codebase,
or the Team Lead explicitly runs `/archaeology`.

**This is a read-only discovery phase. No commits are made. No files are changed.**
**No agent writes new code. Every agent reads, analyses, and reports.**

Duration: one session. All six phases complete before the commit index is proposed.
The output of archaeology feeds directly into `/init` Phase 2 — it replaces the
agent consultation questions for domains that already have code.

---

## Before You Start

Ask the Team Lead two questions before invoking any agent:

**1. What's the goal of this engagement?**
```
[ ] Add a new feature to existing system
[ ] Refactor or modernize existing code
[ ] Fix known bugs or technical debt
[ ] Scale or harden the existing system
[ ] Take over maintenance of an abandoned project
[ ] Other: ___
```

The goal shapes what the archaeology focuses on. "Add a feature" means the agents
focus on integration points. "Modernize" means they catalogue every pattern that will change.
"Take over maintenance" means they go deeper on stability and risk.

**2. What do you already know about this codebase?**

Ask the Team Lead to share anything they know: rough age, known problem areas,
recent incidents, original authors, any documentation that exists.
This primes the agents before they read a single file.

---

## PHASE 1 — Structural Mapping (Claude)

Claude reads these files directly — no agent invocation needed:

```
README.md / README.rst / README.txt  (any README variant)
package.json / pyproject.toml / Cargo.toml / go.mod / pom.xml (manifest)
docker-compose.yml / docker-compose.yaml
.env.example / .env.sample
Makefile
.github/workflows/ (all CI files)
Top-level folder structure (ls -la, one level deep)
```

Claude produces a **Structural Map**:

```markdown
## Structural Map — [Project Name]

**Language / Runtime:** [detected]
**Framework:** [detected]
**Package manager:** [detected]
**Database:** [detected or unknown]
**Cache/Queue:** [detected or unknown]
**Container setup:** [yes/no — details]
**CI/CD:** [yes/no — platform]
**Test framework:** [detected or unknown]
**Estimated codebase age:** [from git log --oneline | wc -l and earliest commit date]
**Commit count:** [git log --oneline | wc -l]
**Last commit:** [git log -1 --pretty="%ar by %an"]

**Top-level domains detected:**
- [folder]: [apparent purpose]
- [folder]: [apparent purpose]

**Assigned domain owners (preliminary):**
- [folder] → [Backend / DevOps / Frontend / AI / Unknown]

**What we know nothing about yet:**
- [list any major folders or systems with no README or obvious structure]
```

Surface the Structural Map to the Team Lead. Ask:
> "Does this match your understanding? Anything missing or wrong?"
Adjust before proceeding.

---

## PHASE 2 — Backend Archaeology (Backend Engineer)

Run in parallel with Phase 3 and Phase 4.

**What to read (in this order):**

```
1. All model/schema files (ORM models, Pydantic schemas, TypeScript types, etc.)
2. All service/business logic files
3. All route/controller/handler files
4. Database migration files (all of them — not just the latest)
5. Configuration and settings files
6. All test files
7. Any existing ARCHITECTURE.md, DECISIONS.md, ADRs, or design docs
```

**What to produce — Backend Archaeology Report:**

```markdown
## Backend Archaeology Report

### What's Built (inventory)
List every major component that exists and appears complete:
- [component]: [one sentence on what it does]
- [component]: [one sentence]

### What's Partially Built
List anything that appears started but incomplete:
- [component]: [what exists] / [what's missing]
- [component]: [what exists] / [what's missing]

### Existing Conventions — CRITICAL
This section is written into the agent's identity file before any new code is written.
Agents MUST match these conventions in all new work — even if the conventions differ
from the agent's defaults.

**Naming patterns:**
- Models: [e.g. snake_case class names, singular nouns]
- Services: [e.g. service functions named verb_noun]
- Routes: [e.g. /resource/{id} pattern, plural nouns]
- Variables: [e.g. snake_case throughout]
- Error types: [e.g. HTTPException with detail dict, or custom exception classes]

**Code patterns:**
- Database access: [e.g. sync Session vs async AsyncSession]
- Return types: [e.g. typed Pydantic models vs dicts vs raw ORM objects]
- Error handling: [e.g. try/except at route level vs service level vs both]
- Validation: [e.g. Pydantic v1 validators vs v2 model_validator]
- Authentication: [e.g. how auth is checked — middleware, decorator, manual in each route]
- Logging: [e.g. stdlib logging with specific format, structlog, print statements]

**Test patterns:**
- Test framework: [pytest / unittest / jest / etc.]
- Test structure: [e.g. one test file per service, or per route]
- Fixture pattern: [e.g. pytest fixtures in conftest.py vs inline setup]
- Mocking pattern: [e.g. unittest.mock vs pytest-mock vs manual stubs]
- Test database: [e.g. in-memory SQLite vs test Postgres vs mocked session]

### Technical Debt Inventory
Rank by impact. Be specific — file and line where possible.

| Severity | Location | Problem | Impact if not fixed |
|---|---|---|---|
| 🔴 High | [file:line] | [what's wrong] | [what breaks] |
| 🟡 Medium | [file:line] | [what's wrong] | [what breaks] |
| 🟢 Low | [file:line] | [what's wrong] | [what breaks] |

### Test Coverage Assessment
- Total test files: [N]
- What's well covered: [list]
- What has no tests: [list]
- What's tested but incorrectly: [list]
- Overall assessment: [adequate / partial / minimal / none]

### Integration Points
List every place the backend connects to external systems:
- [system]: [how it's connected] — [is the connection well-structured or fragile?]

### What I Will NOT Touch
Explicit list of code that is working, stable, and should not be modified unless
explicitly scoped into a commit:
- [component]: [reason to leave alone]
```

---

## PHASE 3 — Infrastructure Archaeology (DevOps Engineer)

Run in parallel with Phase 2 and Phase 4.

**What to read:**

```
Dockerfile / docker-compose.yml / docker-compose.*.yml
.github/workflows/*.yml (all CI files)
nginx.conf / caddy.conf / any proxy config
.env.example / any env documentation
Makefile / scripts/ directory
kubernetes/ / k8s/ / helm/ (if present)
Any deployment scripts or runbooks
```

**What to produce — Infrastructure Archaeology Report:**

```markdown
## Infrastructure Archaeology Report

### Infrastructure Topology
- Services running: [list each container/process and what it does]
- How they connect: [networking, ports, service discovery]
- Persistent volumes: [what data persists, how]
- Entry point: [how traffic enters the system]

### Environment Variables
Complete inventory of all env vars the system uses:

| Variable | Defined in .env.example? | Has default? | Required? | Notes |
|---|---|---|---|---|
| [VAR_NAME] | yes/no | yes/no | yes/no | [note] |

Flag any env vars referenced in code but missing from .env.example.
Flag any in .env.example but apparently unused.

### CI/CD Assessment
- Platform: [GitHub Actions / GitLab CI / Jenkins / none]
- Jobs that run: [list]
- What triggers them: [push / PR / manual / scheduled]
- Passing / failing: [if visible]
- Missing jobs: [e.g. no test job, no lint, no deploy]

### Infrastructure Gaps
Things that should exist but don't:
- [ ] Health checks on all services
- [ ] All env vars documented in .env.example
- [ ] Container build caching
- [ ] Separate test compose file
- [ ] [any other gaps found]

### What Works, What Doesn't
- Known to be working: [list]
- Known to be broken or missing: [list]
- Unknown / not tested: [list]

### Conventions
- How the team does deployments: [manual / script / CI / unknown]
- How the team runs locally: [make command / docker-compose up / custom / unknown]
- Any tribal knowledge encoded in Makefile targets: [list non-obvious targets]
```

---

## PHASE 4 — Security Surface Mapping (Sage)

Run in parallel with Phase 2 and Phase 3.

**What to read:**

```
All route/controller files (looking for input handling)
All authentication and authorization code
All places where credentials, tokens, or secrets are handled
All external API integration code
Any file upload or filesystem access code
All database query construction
```

**What to produce — Security Surface Map:**

```markdown
## Security Surface Map

### Attack Surface Inventory
Every place where external input enters the system:

| Entry point | Input validation | Auth checked? | Risk level |
|---|---|---|---|
| [route/function] | [none/partial/full] | [yes/no/partial] | [LOW/MED/HIGH/CRITICAL] |

### Existing Vulnerabilities
Findings from the current codebase — not hypothetical, actually present:

🔒 [SEVERITY] — [file:line]
Threat: [what an attacker can do]
Mechanism: [how]
Mitigation needed: [specific fix]

### Security Debt
Patterns that aren't acute vulnerabilities but create risk over time:
- [pattern]: [file examples] — [risk it creates]

### What's Already Secure
Explicitly note what's being handled well — so agents don't accidentally break it:
- [mechanism]: [why it's sound]

### Secrets Assessment
- Secrets management approach: [env vars / secret manager / hardcoded / mixed]
- Any secrets found in code or git history: [yes — details / no]
- Recommendation: [what to keep / what to change]
```

---

## PHASE 5 — Baseline Quality Review (Viktor)

Runs after Phases 2–4 complete (needs their outputs as context).

**What to read:** All backend code, plus the Backend Archaeology Report.

**What to produce — Baseline Quality Report:**

```markdown
## Baseline Quality Report

### Overall Assessment
[One paragraph. Is this codebase in good shape, passable shape, or troubled shape?
Be direct. The Team Lead needs an accurate picture, not a diplomatic one.]

### Patterns to Preserve
Code patterns in this codebase that are well-done and should be continued:
- [pattern]: [why it's good] — [example file]

### Patterns to Correct Going Forward
Patterns that exist in old code but should NOT be used in new code.
New code written by agents must use the corrected pattern.
Old code is not touched unless explicitly scoped.

| Old pattern | Corrected pattern | Found in | New code must use |
|---|---|---|---|
| [what exists] | [what to use instead] | [files] | [corrected pattern] |

### Technical Debt Priority
Which debt should be fixed before adding new features (if any):
- 🔴 Must fix before new work: [specific items]
- 🟡 Fix during relevant commits: [specific items]
- 🟢 Low priority, log and leave: [specific items]

### New Code Standards
Given the existing codebase conventions, here are the standards agents must follow
for ALL new code written in this project:
[This section is copied directly into each agent's identity file]

- [standard 1]
- [standard 2]
- [standard 3]
```

---

## PHASE 6 — Claude Synthesizes

Claude reads all four archaeology reports. No agent invocation — this is Claude's work.

**Produce the Archaeology Synthesis:**

```markdown
## Archaeology Synthesis — [Project Name]

### What Exists (Baseline)
[Commit-equivalent summary of what's already built — organized by the same phases
the commit protocol would use: Foundation, Data, Core Logic, API, etc.]

### What's Missing
Organized by impact on the engagement goal:

**Blocking — must exist before new work can land:**
- [gap]: [why it blocks]

**Important — needed for quality or completeness:**
- [gap]: [what it affects]

**Nice to have — out of scope for this engagement:**
- [gap]: [why deferred]

### Conventions Snapshot (for agent identity files)
[Condensed version of all convention findings — goes into each agent's identity file
as a "Project Conventions" section before the engagement begins]

### Risk Register
The top 3 risks that could derail this engagement:
1. [risk]: [likelihood] — [mitigation]
2. [risk]: [likelihood] — [mitigation]
3. [risk]: [likelihood] — [mitigation]

### Proposed Commit Index
[Draft commit sequence starting from the current state — not from commit 01.
Each commit represents a delta: what we're adding, changing, or fixing.
Nothing that already works is re-committed.]

Example framing for existing-project commits:
  ✓ "feat: add rate limiting to existing order routes"
  ✓ "test: add missing coverage for meal service edge cases"
  ✓ "fix: resolve N+1 query in ingredient availability check"
  ✗ "feat: order service" (already exists — don't re-commit what's there)
```

---

## PHASE 7 — Conventions Written Into Agent Files

Before Claude presents findings to the Team Lead, Claude updates each active agent's
identity file with a **Project Conventions** section:

```markdown
## Project Conventions — [Project Name]
*Written during archaeology on [date]. All new code must match these patterns.*

**Must follow (existing patterns to continue):**
- [convention]: [example from codebase]

**Must NOT use (old patterns being corrected):**
- [old pattern] → use [new pattern] instead

**Project-specific non-negotiables:**
- [anything the archaeology revealed that is specific to this project]
```

This runs before any commit is made. It is the mechanism that prevents agents from
imposing their defaults on a codebase with established conventions.

---

## PHASE 8 — Present to Team Lead

Claude surfaces the full synthesis. Structure:

```
## Archaeology Complete — [Project Name]

**What we found:**
[2–3 sentences on the state of the codebase — honest, direct]

**What already works (don't touch without a specific commit):**
[list]

**What's missing that we need to build:**
[list — organized by blocking / important / deferred]

**Top risks:**
1. [risk and mitigation]
2. [risk and mitigation]

**Conventions locked in for all agents:**
[summary of the key conventions captured]

**Proposed commit sequence:**
[full table — starting from where the project is now]

Questions before I write commit-protocol.md:
1. Does this match your understanding of the codebase?
2. Are there known issues I didn't find that should be in the commit sequence?
3. Is the scope right — anything to add or defer?
4. Any existing code you want me to explicitly mark as off-limits?
```

Wait for explicit Team Lead approval before writing any files.

---

## Archaeology Non-Negotiables

- Never make a commit during archaeology. Not even "just a quick fix."
  If Sage finds a CRITICAL vulnerability, log it and flag it — don't touch it.
  It becomes the first commit in the protocol.

- Never impose agent defaults on existing code. Viktor's standards describe
  new code only. Old code is catalogued, not silently corrected.

- Never assume something doesn't exist because you didn't find it in 30 seconds.
  Read the codebase. Search for the pattern. Confirm absence before reporting absence.

- Always capture conventions before proposing any new commits.
  An engagement that starts without conventions captured will produce
  new code that fights the existing code. That is worse than the original debt.

- The commit index for an existing project starts at the current state.
  Commit 01 is not "project foundation" — it is the first thing that needs to change.
