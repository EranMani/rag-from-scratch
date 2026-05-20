# team-preferences.md

> Claude reads this file at every session boot, immediately after project-state.json.
> These preferences tune agent behavior for this specific project and Team Lead.
> Edit any section at any time — Claude propagates changes to affected agents
> at the start of the next commit loop iteration.
>
> Last updated: 2026-05-09

---

## CRITICAL — Rules Violated in C27 (2026-05-17) — Read Before Every Commit

```
1. NO GATE-FIX PASSES. EVER.
   If Viktor or Sage blocks → surface to Team Lead → fix is its own next commit.
   Do NOT re-invoke the agent and re-run the gate in the same loop.
   Rule already existed in this file. C27 violated it 4 times. Cost: ~300k extra tokens.

2. ALWAYS SPECIFY model: "haiku" IN AGENT CALLS FOR REVIEWERS AND WRITERS.
   Viktor, Sage, Quinn, Mira, Ryan → model: "haiku" — no exceptions.
   Omitting it runs on Sonnet (3× cost). C27 cost ~80–100k extra tokens from this alone.

3. VALIDATE THE SPEC BEFORE INVOKING ANY AGENT.
   - Does the spec actually achieve the stated goal? If goal is "wow" but spec tweaks font sizes → rewrite.
   - Does any UI element interpolate user data into ui.html()? → Change to ui.label().
   A rejected agent pass costs the same tokens as a successful one and produces nothing.

4. TRIAGE GATES BEFORE RUNNING THEM.
   Ask: "What specific risk does this commit introduce that this reviewer can catch?"
   No answer → skip the gate. Running gates for comfort costs money for no benefit.
   See gate triage matrix below.

5. NEVER SPAWN AN AGENT FOR A KNOWN EDIT.
   If the exact file, line, and new content are already known → use Edit directly.
   Agent bootstrap overhead = 10–30k tokens. Edit = ~200 tokens.
   C29 example: 28k tokens spent to change 2 CSS lines that could have been 2 Edit calls.
   Agents are for open-ended exploration only. Known targeted changes use Edit, period.
```

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
Haiku  (fast, low cost):     Viktor, Sage, Quinn, Mira, Ryan — all reviewers and writers
Sonnet (default, balanced):  Rex, Nova, Aria, Adam — all implementation work
Opus   (never):              Banned — too expensive for any use in this project
```

Specify at Agent invocation time via `model: "haiku" | "sonnet"`.
**Opus is never used. No exceptions.**

### Viktor model rule

**Always Haiku.** Viktor reads only the diff and key files, not full worklogs or history.
Pass Viktor the diff path + commit spec summary (not full spec). Viktor must work within
a tight context package — no speculative file reads.

### Sage model rule

**Always Haiku when triggered.** Sage reads only security-relevant files (auth routes,
config, env handling) — not the full diff. Pass targeted file list, not everything.

### Quinn model rule

**Always Haiku when triggered.** Quinn reads only the test file and the source file it tests.
No full codebase scans.

### Mira model rule

**Always Haiku when triggered.** One paragraph prompt max. Mira does not read files.

### Ryan context rule

**Ryan runs every commit — no exceptions.** The LEARNING_LOG is the Team Lead's primary
learning artifact and must stay current.

**Ryan is always invoked. Every commit gets a real entry — not a one-liner from Claude.**
The LEARNING_LOG is the Team Lead's primary learning artifact. Depth scales with commit
complexity (full entry vs. one-liner), but Ryan always writes it — never Claude.

**Entry type rule:**
- Full entry: commit updated ARCHITECTURE.md or DECISIONS.md, had a security finding,
  involved a non-obvious design decision, or introduced a new pattern
- One-liner: routine test addition, config tweak, minor refactor, doc-only commit

**How to invoke Ryan — token-efficient:**

Step 1 — Claude reads the **last 15 lines** of `LEARNING_LOG.md` (Read with
         `offset = file_line_count - 15`). These are the Edit anchor.

Step 2 — Claude builds Ryan's prompt containing:
         a) Full Entry format block only (~38 lines, template lines 51–88) — NOT lines 1–99
         b) The last 15 lines verbatim — so Ryan has the anchor without reading speculatively
         c) A commit brief (150 words max, written by Claude):
            - Commit number, name, date, assignee
            - What changed (2–3 sentences)
            - Key decisions or non-obvious constraints (bullet points)
            - Nova/Rex/agent approach notes (from their worklog — Ryan reads thinking, not just outcome)
            - Files touched
            - Entry type: "full" or "one-liner"

Step 3 — Ryan composes the entry and appends via Edit:
         old_string = [exact last 15 lines Claude provided]
         new_string = [those same 15 lines] + [new entry]
         Ryan may Read LEARNING_LOG.md if needed (hook exemption: one targeted read of
         LEARNING_LOG.md is allowed). Ryan never reads the raw diff — Claude summarizes it.

Target: Ryan under 8k tokens per full entry, under 3k tokens per one-liner.

---

## Context Window Management

```
After every commit:     type /clear — all state is in project files, nothing is lost
Mid-commit threshold:   type /compact when session reaches ~60k tokens without a commit yet
```

**Why /clear after every commit:** The boot sequence reloads everything from project-state.json,
commit-protocol.md, team-preferences.md, and memory files. Conversation history adds zero value
between commits and costs tokens on every subsequent message.

**Why /compact at 60k mid-commit (not /clear):** At 60k without a commit, there is likely
in-flight work (agent implementation, gate findings) that hasn't been persisted yet.
/compact summarizes and frees context while keeping the thread alive.
/clear at that point would lose the in-flight work.

**The post-commit hook prints a /clear reminder automatically after every commit.**

---

## Worklog Archive Trigger

```
Archive threshold: >3 completed sessions per agent (not 5)
Trigger:           /archive-worklog [agent-name]
Timing:            at the start of the session following the threshold being crossed
```

Agents most likely to hit threshold first: Rex (Phases 1–3), Nova (Phases 2–4).

---

## Quality Gate Trigger Rules (updated 2026-05-17)

**Token budget target: ≤60k for implementation commits (Nova, Rex, Aria, Adam); ≤15k per review/doc agent (Viktor, Sage, Quinn, Mira, Ryan).**

### Gate Triage — Ask This Before Every Gate

Before invoking any reviewer, answer: **"What specific risk does this commit introduce that this reviewer can catch?"**
If there is no answer → skip the gate. Do not run gates for comfort or habit.

| Commit type | Viktor | Sage | Quinn | Mira |
|---|---|---|---|---|
| Pure CSS / color / spacing / SVG — no user data, no logic | **skip** | **skip** | **skip** | only if copy/name changes |
| UI layout / component — no user data rendered | **skip** | **skip** | **skip** | only if behavior changes |
| UI renders user-supplied data | **skip** | **run** | **skip** | only if data shape changes |
| New logic / functions / code paths | **run** | conditional | conditional | conditional |
| Auth, secrets, env handling, external API | **run** | **run** | conditional | conditional |
| New service, route, or DB schema | **run** | conditional | **run** | conditional |
| Doc-only / worklog / config tweak | **skip** | **skip** | **skip** | **skip** |

**"Conditional"** = run only if the commit also touches that reviewer's specific domain. Default is skip.

The every-5-commit Viktor+Quinn cadence review still applies as a minimum floor — it is a batch review across accumulated diffs, not a per-commit gate, and is not skippable.

### Viktor — every 5 commits, Haiku
Run on commits 5, 10, 15, 20 (every 5th commit). In a single pass, review all accumulated diffs since the last Viktor wave. Token target: ≤20k per wave.

**How Claude passes context to Viktor:**
- Always pass a `git diff` — NEVER paste full file contents into the prompt.
- Viktor uses Read with line ranges for targeted inspection only — never reads whole files.
- Prompt should contain: diff output only + brief commit name. No spec, no calibration prose.

**Blocking criteria — two tiers only:**

Blocks immediately (system-breaking):
- Import errors that prevent app startup
- Unhandled exceptions that crash the process on the happy path
- Wrong async/sync mixing that blocks the event loop
- Data corruption — wrong merge logic, overwriting instead of appending
- SQL injection, exposed secrets, auth bypass
- Missing required arguments causing `TypeError` at runtime
- Infinite loops or deadlocks

Logged for deferred review (everything else):
- Dead code, unused variables
- Missing or imprecise type annotations
- Style, naming, minor pattern issues
- Performance concerns (unless O(n²) on unbounded input)
- Test quality suggestions, maintainability advisories

**No gate-fix passes.** If Viktor blocks, the fix is its own next commit — never a re-review within the same loop.

### Sage — conditional, Haiku
Trigger **only** when the commit touches:
- Auth dependencies (`get_current_user`, JWT decode, login/register routes)
- Secrets or env var handling (`config.py`, `.env.example`, secret fields)
- External API calls (OpenAI, httpx to third parties)
- File upload or path operations
- Any new public-facing route with user input

Skip Sage on: node internals, schema files, pure test additions, infra config with no secrets,
doc-only commits.

**Blocking criteria — same model as Viktor:**

Blocks immediately:
- Secrets committed to code (API keys, JWT secret hardcoded)
- SQL injection via unguarded dynamic column names
- Auth bypass — unauthenticated access to a protected route
- Critical CVE-level issues that are directly exploitable

Logged for deferred review:
- CWE-209, non-critical information disclosure
- LOW/MEDIUM findings that require an exploitation chain
- Advisory-level findings

**No gate-fix passes.** If Sage blocks, the fix is its own next commit.

### Quinn — every 5 commits, Haiku
Run on the same wave as Viktor (commits 5, 10, 15, 20). Reviews accumulated test coverage across all commits since the last wave.

Skip Quinn between waves — no per-commit coverage checks.

**No gate-fix passes.** Coverage gaps are logged; fixes go into future commits.

### Mira — conditional, Haiku (unchanged rule, model now explicit)
Trigger only on user-facing behavior changes (API shape, UI, data fields the user sees).
Skip on internal plumbing.

### Gate wave execution
Viktor + Quinn run together every 5 commits (commits 5, 10, 15, 20).
Sage runs only on commits that touch auth/secrets/external APIs — regardless of the 5-commit cadence.
Mira runs only on user-facing behavior changes — regardless of the 5-commit cadence.

Do not spin up a gate agent just to confirm "not triggered" — make that call yourself.

### Gate-fix passes — eliminated
There are no gate-fix passes. If a reviewer blocks on a system-breaking issue, the owning agent fixes it in a new dedicated commit — not within the current loop. The gate wave does not re-run.

### Commit message format (required for post-commit hook)
Every commit message must include `Commit #NN` on its own line in the body.
The post-commit hook parses this to auto-update commit-protocol.md and project-state.json.
Without it, state must be updated manually.

```
[conventional-commit subject line]

[body — what and why]

Commit #NN
-- AgentName

Co-Authored-By: AgentName <email>
```

---

## Parallelization Preferences

```
Quality gate wave:       parallel among triggered agents only (not always all 4)
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

## Universal Tool Use Cap — ALL Agents, No Exceptions

**25 tool uses maximum for every agent invoked. This applies to Viktor, Sage, Quinn, Mira, Ryan, Nova, Rex, Aria, and Adam equally.**

If an agent hits 25 and is not done, it stops and reports. Claude does not re-invoke to continue — the agent reports what remains and Claude surfaces it to the Team Lead.

This cap is not negotiable. Viktor running 59 tool uses in a wave review is the same failure mode as Nova running 73 in an implementation. Both drain tokens. Both are orchestrator failures from omitting the constraint in the invocation prompt.

---

## Execution Constraints — Include Verbatim in Every Invocation

### Implementors (Nova, Rex, Aria, Adam)

```
EXECUTION CONSTRAINTS:
- Max tool uses: 25. Plan your reads upfront. Batch your writes. If you hit 25 and aren't done, stop and report.
- Two phases only: Phase 1 — all reads. Phase 2 — all writes. No reads in Phase 2.
- Do not re-read any file you have already read this session.
- Worklog: one write at task completion only. No mid-task worklog updates.
- Test runs: maximum 2. On second failure, report what failed and stop — do not loop.
- Code comments: one line max, functional only. No explanatory prose, no narration.
```

### Reviewers (Viktor, Sage, Quinn)

```
EXECUTION CONSTRAINTS:
- Max tool uses: 25. If you hit 25 and aren't done, stop and report findings so far.
- Work from the diff provided. Do NOT read files speculatively.
- Only Read a file if a specific line in the diff is ambiguous — max 15 lines per targeted read.
- Do not read files to understand context you can infer from the diff.
```

### Ryan

```
EXECUTION CONSTRAINTS:
- Max tool uses: 5. Use Edit only — do not Read the target file.
- All context comes from Claude's prompt. If something is unclear, note it and proceed.
```

### Mira

```
EXECUTION CONSTRAINTS:
- Max tool uses: 5. Do not read any files — assess only from the brief Claude provides.
```

**Why these constraints exist:**
Nova's Commit 13 ran 73 tool uses at 122k tokens. Viktor's Commit 15 wave ran 59 tool uses at 61k tokens.
Both cases are the same root cause: no explicit cap in the invocation prompt. The two-phase protocol eliminates the read-modify-read spiral. The reviewer cap eliminates speculative full-file reads on diffs.

---

## Token Records Rule

**TOKEN_RECORDS.md must be updated before every Team Lead approval prompt — no exceptions.**

- Add one commit entry per commit, using the same table structure as existing entries
- Token counts come from the `<usage>` block returned by each Agent tool call result
- Capture: agent name, model tier, exact token count, tool use count, delta vs. target
- If an agent was not triggered, omit its row (don't add a zero row)
- This is the orchestrator's job — no agent needed, no extra invocation

**Why this matters:** The file exists to track whether token reduction methods are working.
A missing entry makes the comparison table useless. An estimated entry is worse than useless —
it masks real regressions. Exact numbers only.

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

## Agent Names and subagent_type Identifiers

**The `subagent_type` field in Agent tool calls must use the identifier column — not the role name.**
Mira's role is "Product" but her subagent_type is `"mira"`. Getting this wrong silently fails the invocation.

| Role | Name | subagent_type |
|---|---|---|
| Orchestrator | Claude | `claude` |
| Backend | Rex | `rex` |
| DevOps | Adam | `adam` |
| Frontend | Aria | `aria` |
| AI Engineer | Nova | `nova` |
| Product | **Mira** | `mira` (NOT "product") |
| Code Reviewer | Viktor | `viktor` |
| Security | Sage | `sage` |
| QA | Quinn | `quinn` |
| Tech Writer | Ryan | `ryan` |
| Curriculum | Lara | `lara` |

---

## Reviewer Prompt Format — Hard Limit

**Sage, Mira, Quinn, and Viktor prompts must follow this template exactly. No exceptions.**

```
[1 sentence: what this commit does — no more]

## Diff
[git diff verbatim]

## What to check
- [specific risk 1 — one sentence]
- [specific risk 2 — one sentence]
- [specific risk 3 — one sentence, max]

[Under 200 words total before the diff. No pre-analysis. No explanatory prose.
No "here's what I think is safe." No background context beyond the diff itself.]
```

**Why this limit exists:** C37 and C38 both had Sage/Mira at 30–34k tokens against a ≤15k target.
The overage was almost entirely prompt tokens — verbose invocations, not reviewer tool use.
A tight prompt + diff costs ~8–12k. A verbose prompt + diff costs 30–40k. The diff is the same size in both cases.

---

## Claude Behaviour Rules

These rules apply to Claude (the orchestrator) directly — not to sub-agents.

```
1. Always address the Team Lead as "Eran" when raising issues, surfacing blockers,
   flagging findings, or asking for approval. Never use generic "you".

2. Before saying "I don't have X" or "I don't know X", check the project files first
   — team-preferences.md, memory files, CLAUDE.md, project-state.json are the first
   places to look. One targeted Read costs nothing compared to a wrong answer.

3. Ad-hoc commit messages (work requested by Eran outside the formal commit protocol)
   must open the body with the EXACT phrase (copy it verbatim — no variations):

       Requested by Eran Mani, our team lead:

   WRONG (seen in past commits — never use these):
       "Requested by EranMani:"             ← missing title, wrong name format
       "Requested by Eran:"                 ← missing title
       "Requested by EranMani, our team lead:" ← wrong name format (no space)

   CORRECT:
       "Requested by Eran Mani, our team lead: <one sentence what was asked>"

   This must be the very first line of the commit body, before any other description.

4. Before every agent spawn, ask this question aloud:
   "Do I already know the exact file, the exact lines, and the exact new content?"
   If yes → use Edit directly. No agent. No exception.
   Spawning Aria to change 2 CSS lines (C29) cost 28k tokens. Edit would have cost ~200.
```

---

## Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-05-08 | Initial creation | /init protocol complete |
| 2026-05-09 | Added Mira dynamic invocation rule | Only invoke on user-facing commits to reduce token cost |
| 2026-05-09 | Added Model Assignments section | Haiku/Sonnet/Opus tiering to reduce cost without quality loss |
| 2026-05-17 | Strengthened commit attribution rule #3 | Repeated violations using wrong phrase "Requested by EranMani:" instead of "Requested by Eran Mani, our team lead:" |
| 2026-05-09 | Added Worklog Archive Trigger section | Lower threshold (3 sessions) for proactive archiving |
| 2026-05-09 | Added worktree isolation note to Parallelization | Needed for Wave B (commits 08+09) |
| 2026-05-09 | Viktor model tier rule added | Two Opus passes on Commit 07 schema cost 107k tokens — Opus only for complex/auth/concurrent commits |
| 2026-05-09 | Ryan context rule added | Ryan read full LEARNING_LOG (55k tokens) just to append one entry — pass format template inline instead |
| 2026-05-09 | Quality Gate Pre-Brief section added | Nova ran twice on Commit 07 — pre-brief prevents Viktor blocks by front-loading what he checks |
| 2026-05-09 | Orchestrator Read Discipline section added | Speculative file reads compound across session history — read only when about to edit |
| 2026-05-10 | Opus banned entirely; all reviewers → Haiku | Commit 10 used ~220k tokens — 4-agent Opus/Sonnet gate wave is unsustainable |
| 2026-05-10 | Quality Gate Trigger Rules added | Conditional gates: Sage/Quinn only on specific commit types; re-run only the blocking reviewer on fix pass |
| 2026-05-10 | Ryan runs every commit — tight brief only, no raw diff | LEARNING_LOG is the Team Lead's primary learning artifact; must stay current |
| 2026-05-10 | Token budget target set: 11–15k per commit | Team Lead hard requirement — current 60–70k average is unsustainable |
| 2026-05-10 | Ryan protocol overhauled — always invoked, uses Edit anchor Claude provides, never reads the file | Ryan read 48k tokens to append one entry by reading the full LEARNING_LOG; fix: Claude hands Ryan the last 15 lines as anchor |
| 2026-05-10 | Viktor token target set to ≤25k; Claude passes git diff not full file contents | Claude pasting 532-line test file into Viktor prompt wasted ~20k tokens |
| 2026-05-10 | Viktor + Quinn cadence changed to every 5 commits; gate-fix passes eliminated | Commit 12 cost ~297k tokens — review+fix+re-review cycle is unsustainable |
| 2026-05-10 | Viktor blocking criteria narrowed to system-breaking only; everything else logged | Ghost if-else triggered a full gate-fix pass — disproportionate for a non-breaking issue |
| 2026-05-10 | Sage blocking criteria updated to match Viktor model (block only on critical exploitable issues) | Consistency with new Viktor model; LOW/MEDIUM findings go to deferred log |
| 2026-05-10 | Ryan template trimmed — pass Full Entry format block only (~38 lines), not lines 1–99 | Ryan consumed 54k tokens in Commit 12 largely due to oversized template in prompt |
| 2026-05-10 | Implementor Execution Constraints section added; token budget target revised to ≤60k/≤15k | Nova hit 122k / 73 tool uses in Commit 13 — read-modify-read spiral and mid-task worklog writes are the root cause |
| 2026-05-10 | **Universal 25-tool-use cap extended to ALL agents** — Viktor, Sage, Quinn, Mira, Ryan included | Viktor hit 59 tool uses in the Commit 15 wave (61k tokens). Nova hit 34 in the same session. Both caused by Claude omitting constraints from invocation prompts. Cap now universal — no agent type exempt. Reviewer and Ryan constraint blocks added. |
| 2026-05-17 | **CRITICAL callout added at top of file** — 3 rules violated in C27 at cost of ~300k extra tokens | (1) Gate-fix passes run 4× in C27 despite being explicitly banned — rule existed, Claude ignored it. (2) Reviewers ran on Sonnet not Haiku — model: "haiku" never specified in Agent calls. (3) Spec not validated before Aria invocation — pass 1 rejected (186k wasted), retry introduced CWE-79 XSS. |
| 2026-05-17 | **Gate triage matrix added** — skip gates when commit has no applicable risk | Team Lead directive: running Viktor+Sage+Mira on a CSS-only commit is wasteful. Gates must serve a purpose, not be run by default. Matrix defines skip/run per reviewer per commit type. Pure CSS/style: zero gates. User data in UI: Sage only. New logic: Viktor only. |
| 2026-05-17 | **No-agent-for-known-edits rule added** — CRITICAL rule #5, Claude Behaviour Rule #4, plus CLAUDE.md Non-Negotiable #10 and ORCHESTRATION.md STEP 4 and Claude thinking process | C29: Aria spawned to change 2 CSS lines, cost 28k tokens. Edit would have cost ~200. Rule now in every file Claude reads at boot. |
| 2026-05-20 | **Reviewer prompt format section added + subagent_type reference table** | C37/C38: Sage/Mira at 30–34k (target ≤15k) — overage was verbose invocation prose, not reviewer tool use. C38: Mira invoked with subagent_type "product" (wrong) → wasted 20k on failed invocation + nonsensical recovery agent. |
| 2026-05-20 | **Ryan hook expanded to also allow LEARNING_LOG_SUMMARY.md** | Hook granted LEARNING_LOG.md exemption after C37 but not its companion file — Ryan blocked on LEARNING_LOG_SUMMARY.md in C38, requiring Claude to write both entries. |
