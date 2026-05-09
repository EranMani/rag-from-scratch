# Claude Code — Tips & Tricks
> Reference guide for getting the most out of Claude Code's agentic capabilities.
> Each technique includes why it matters, when to use it, and a real-world example.
> Extend this document as new techniques are discovered.
> Last updated: 2026-05-09

---

## 1. Model Selection Per Agent

**Why / When:** Not every task needs the same reasoning power. Haiku costs ~20× less than Opus — using it on predictable, low-complexity tasks cuts cost without any quality loss. Choose the model that matches the task's cognitive demand, not the most expensive one available.

| Shorthand | Full model ID | Cost | Best for |
|---|---|---|---|
| `"haiku"` | claude-haiku-4-5 | ~20× cheaper than Opus | Docs, worklog updates, one-liners, GLOSSARY entries |
| `"sonnet"` | claude-sonnet-4-6 | Mid-tier (default) | All implementation work — Rex, Nova, Aria, Adam |
| `"opus"` | claude-opus-4-7 | Most expensive | Deep code review (Viktor), security analysis (Sage) |

**How to apply:** Pass `model: "haiku"` (or `"sonnet"`, `"opus"`) to the Agent tool call.
If omitted, the agent inherits the parent session's model — currently Sonnet.

**Example:** Ryan writing a one-liner LEARNING_LOG entry after Commit 07 ("AgentState
designed for full arc — schema changes cascade in compiled LangGraph graphs") doesn't
need Sonnet's full reasoning. Haiku produces a clean one-liner for a fraction of the cost.
Viktor reviewing a subtle async/thread interaction in `chain.py`, by contrast, warrants Opus —
the reasoning chain matters.

---

## 2. Parallel Agent Execution

**Why / When:** Sequential agents load duplicate context and wait unnecessarily. Parallel agents share wall-clock time and avoid redundant loading. Use whenever two or more agents have no dependency on each other's output.

**Foreground (blocking):** Default. Claude waits for the result before proceeding.
Use when the result is needed to determine the next step.

**Background (non-blocking):** Pass `run_in_background: true`. Claude continues working
and is notified when the agent completes.
Use when you have genuinely independent work to do in parallel.

**Example:** The quality gate wave (Viktor + Sage + Quinn) — instead of running them
one after another (each loading the same diff three times sequentially), spawn all three
in a single message with `run_in_background: true`. They all read the diff simultaneously.
Total wall time: one agent's duration, not three. Same for Wave B commits 08 and 09 —
both are independent and touch different files.

---

## 3. Worktree Isolation

**Why / When:** When two agents write to the same directory simultaneously, they produce git conflicts or overwrite each other's changes. Worktree isolation gives each agent its own branch copy, so they work independently and results are merged cleanly afterward.

Pass `isolation: "worktree"` to the Agent tool. The agent gets its own isolated git
branch copy and cannot conflict with your working tree or other parallel agents.

**When to use:**
- Any two agents writing to overlapping file paths in the same session
- Wave B (commits 08 + 09 both write to `src/agents/nodes/`)
- Any parallel commit pair that touches shared directories

**Cleanup:** The worktree is automatically cleaned up if the agent makes no changes.
If changes are made, the worktree path and branch name are returned — merge manually.

**Example:** Commits 08 and 09 both create files inside `src/agents/nodes/`. Without
worktree isolation, the second agent to run may overwrite a file the first agent just
created, or trigger a merge conflict that stops the commit. With `isolation: "worktree"`,
each agent writes to its own branch — you then merge both branches into main cleanly.

---

## 4. Context Window Management

**Why / When:** Context windows are finite. A session that hits the limit mid-commit forces a restart, losing all in-flight reasoning and requiring expensive context reconstruction. Managing context proactively keeps sessions productive from start to finish.

**`/compact` command:** Compresses the current conversation history into a summary
and frees context window space. Run mid-session when a session is getting long.
Different from worklog archiving — this compresses the live conversation, not files.

**Archive worklogs (`/archive-worklog [agent]`):** Compresses old sessions in an agent's
worklog file into a short summary paragraph. Keeps the file small permanently.
Trigger after every 3 completed sessions per agent (not 5).

**Context tiers for agent context packages:**
- **Tier 0** (always): project-state.json header + commit index row + agent current state header (≤50 lines)
- **Tier 1** (active work): + active commit spec from `commit-specs/`
- **Tier 2** (deep debugging only): + last 2 worklog sessions + specific DECISIONS.md entries
- **Never load:** Full worklog history, all commit specs simultaneously, complete file trees

**80% context threshold:** When a session approaches 80% of context capacity, trigger
`/archive-worklog` for agents with >3 sessions, compress context packages to Tier 0 + Tier 1,
and alert the Team Lead.

**Example:** By Commit 14, Rex has completed 6 commit sessions. His worklog is ~700 lines.
Without archiving, every context package for Rex includes 700 lines of history — most of
which is Commits 01–03 details that are completely irrelevant to Commit 14's scoring service.
After `/archive-worklog rex`, those 6 sessions compress to a ~50-line summary. The next
context package loads 50 lines instead of 700.

---

## 5. Quality Gate Optimization

**Why / When:** Reviewers don't need to know who they are (already loaded from their agent definition) and they don't need the history of unrelated commits. Sending only the diff and active spec gives them everything required for the review — nothing more.

**Reviewer context package — send only:**
- The diff
- The active commit spec
- Relevant interface contracts (what the agent promises to produce/consume)

**Do NOT send:**
- Agent identity files (the agent definition already provides personality + role)
- Full worklog history
- Unrelated commit specs

Stripping identity files from reviewer context packages saves ~1–2k tokens per reviewer
per gate wave.

**Selective Mira invocation:** Only invoke Mira on commits with user-facing behavior
changes — new API endpoints, UI changes, data the user sees, interaction model shifts.
Skip her on internal plumbing (schemas, tests, infra, scoring functions).

**Sage trigger rule:** Only invoked on commits touching auth, secrets, external API calls,
file operations, or any trust boundary crossing.

**Quinn trigger rule:** New services, new routes, behavior changes. Not needed on
documentation-only or pure refactor commits.

**Example:** Viktor's identity file (`.claude/agents/viktor.md`) is ~150 lines. If sent
to Viktor in every gate wave across all 24 commits, that's 3,600 wasted lines —
Viktor knows who he is. What he needs for Commit 07 is: the `state.py` diff, the Commit 07
spec, and the AgentState interface contract. That's it.

---

## 6. Hooks & Automation

**Why / When:** Manual post-commit steps are error-prone and easy to forget. Hooks make repetitive actions automatic and guaranteed — every commit, every time, without relying on memory.

Hooks are shell commands that execute automatically on Claude Code events, configured
in `.claude/settings.json`. They run outside the model — the harness executes them,
not Claude.

**Available hook events:**
- `PreToolUse` — fires before a specific tool is called
- `PostToolUse` — fires after a specific tool completes
- `Stop` — fires when Claude finishes a response

**Current hooks in this project:**
- `post_commit_next_step.py` — updates commit-protocol.md status and project-state.json after every `git commit`
- `pre_commit_check.py` — validates commit message format and domain boundaries before every commit

**What you can add:**
- Auto-lint after any `Write` call to a `.py` file
- Notify when a background agent completes
- Validate `project-state.json` schema on every write

**`/fewer-permission-prompts` skill:** Analyzes your recent transcripts and adds the
most common read-only operations to the project allowlist in `.claude/settings.json`,
reducing permission prompts on future runs.

**`/update-config` skill:** Use this to configure hooks, add permissions, set env vars,
or modify settings.json. Don't manually edit settings.json for automated behaviors —
use this skill so the configuration is documented.

**Example:** Without `post_commit_next_step.py`, after every commit you'd need to manually
open `commit-protocol.md`, find the right row, update the status, then open
`project-state.json` and update `current_commit`, `commits_done`, and `commits_pending`.
The hook does all of this automatically in under a second — and it's impossible to forget.

---

## 7. Memory System

**Why / When:** Claude starts every session with no memory of previous conversations. Without the memory system, you'd re-explain preferences, decisions, and context every single session. Memory bridges sessions so prior agreements are honored automatically.

Memories persist across sessions and are auto-loaded from `MEMORY.md` at the start
of every conversation.

**Memory types:**
| Type | What it stores | When to save |
|---|---|---|
| `user` | Team Lead role, preferences, expertise | Learning who they are |
| `feedback` | How to behave / what to avoid | Corrections or confirmed approaches |
| `project` | Goals, decisions, blockers, deadlines | When context isn't derivable from code |
| `reference` | Where to find things in external systems | Links to Linear, Grafana, Slack, etc. |

**Memory location:** `C:\Users\[user]\.claude\projects\[project]\memory\`

**What NOT to save in memory:**
- Code patterns, file paths, architecture — read the code instead
- Git history — use `git log`
- Ephemeral task state — use TaskCreate for within-session tracking
- Anything already in CLAUDE.md

**Example:** You told Claude in this session that Mira should only be invoked on
user-facing commits, and that Ryan should run on Haiku. Without saving this to memory,
the next session starts fresh and you'd need to say it again. With a `feedback` memory,
those rules are applied automatically from the first message of every future session.

---

## 8. Skills (Slash Commands) Reference

**Why / When:** Skills are pre-built workflows that encode the right sequence of steps for common operations. Using a skill guarantees the correct procedure is followed — using ad-hoc prompts risks missing a step or getting an inconsistent format.

| Skill | When to use |
|---|---|
| `/status` | Full project status report — commit progress, handoffs, blockers, gate results |
| `/next-step` | Current commit brief + Commit Preview for Team Lead |
| `/handoff-check` | Verify all open handoffs have been actioned before starting a commit |
| `/review-request` | Ad-hoc Viktor code review outside the commit loop |
| `/security-audit` | Ad-hoc Sage security review outside the commit loop |
| `/qa-check` | Ad-hoc Quinn coverage review outside the commit loop |
| `/archive-worklog` | Compress old sessions for a specified agent |
| `/replan` | Mid-project replanning — revises commit-protocol.md |
| `/rollback` | Rollback protocol for reverting a bad commit |
| `/archaeology` | Onboard to an existing codebase — maps structure before planning |
| `/loop` | Run a prompt or command on a recurring interval within a session |

**Example:** Starting a session by typing `/status` gives you the full structured report
(commit table, handoffs, blockers, last gate results) in one consistent format — every
time. Asking "what's the status of the project?" without the skill produces a prose
answer that varies in structure and may miss the handoff check.

---

## 9. TaskCreate for Within-Session Tracking

**Why / When:** Complex commits have multiple sequential steps — write the file, run the tests, verify the handoff was consumed, update the worklog. TaskCreate lets you mark each step done as you go, so nothing is missed and you know exactly where you are mid-commit.

`TaskCreate` tracks work within the current conversation. Use it when breaking a
commit into discrete steps you want to mark off as you go.

**Not the same as memory** — tasks are ephemeral and don't persist to the next session.
Memory is for facts about the project or Team Lead that should survive across sessions.

**Example:** Commit 07 involves creating 3 new files, verifying 3 import test gates,
and writing a worklog entry. Without TaskCreate, it's easy to commit before checking
that `AssessmentOutput` validates correctly with a sample dict. With TaskCreate, each
gate is a task — you can't mark it complete without actively confirming it.

---

## 10. Scheduling & Background Routines

**Why / When:** Some tasks need to happen on a schedule (nightly backups, recurring health checks) or need to repeat within a session (polling for a build result). Scheduling prevents these from blocking your main workflow or requiring manual intervention.

**`/loop` skill:** Runs a prompt or command on a repeating interval within a session.
Use for polling, monitoring, or recurring checks (e.g., "check build status every 5 minutes").

**`CronCreate`:** Schedules a remote agent to run on a cron schedule, outside of your
current session. Use for daily backups, nightly test runs, or recurring health checks.

**`ScheduleWakeup`:** Wakes up the current session at a future time. Useful in `/loop`
mode when you want to self-pace work iterations.

**Example:** After Commit 22 ships the deployment scripts, you could set up a daily
`CronCreate` that runs `scripts/health-check.sh` against the EC2 instance and reports
back if the stack is unhealthy — without you needing to remember to check it manually.

---

## 11. ExitPlanMode & Plan Approval

**Why / When:** Starting to build before the approach is agreed wastes effort and tokens. ExitPlanMode forces a pause for explicit Team Lead approval before any code is written — catching wrong assumptions early, when they're cheap to fix.

When `/plan` mode is active, `ExitPlanMode` surfaces the plan to the Team Lead for
approval before any code is written. This is the correct way to get sign-off on an
approach — do not start implementing until `ExitPlanMode` has been called and the
Team Lead has responded with explicit approval.

**Example:** Before Nova builds `AgentState` in Commit 07, presenting the full TypedDict
field list via ExitPlanMode lets the Team Lead catch a missing field (e.g., `trace_id`)
before the schema is baked into the compiled graph. Changing a compiled LangGraph schema
in Commit 12 would require re-running every node test — catching it at plan approval costs zero.

---

## 12. Background vs. Foreground Agents — Decision Rule

**Why / When:** Defaulting everything to foreground wastes time. Defaulting everything to background makes it hard to sequence dependent work. Knowing which to use keeps sessions fast without creating ordering problems.

| Situation | Use |
|---|---|
| You need the result to determine the next action | Foreground (default) |
| The agent is one of several gate reviewers running in parallel | Background |
| You want to continue other work while the agent runs | Background |
| The agent writes to files you'll then read | Foreground (wait for completion) |

Never poll a background agent — you will be notified automatically when it completes.

**Example:** `/archaeology` runs foreground — its output (the codebase map) is what
you use to build the commit protocol, so you can't proceed without it. The quality gate
wave runs background — Viktor, Sage, and Quinn can all read the same diff simultaneously
while you update the documentation checklist. You wait for their results before surfacing
the approval prompt, but you don't have to sit idle while they run.
