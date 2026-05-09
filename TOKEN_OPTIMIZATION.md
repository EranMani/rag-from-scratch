# Token Optimization Log
> Records all methods applied (or considered) to reduce token cost in this project.
> Each entry explains why it works, when to apply it, and a real example from this project.
> Extend this document as new techniques are tried.
> Last updated: 2026-05-09

---

## Applied Methods

### 1. Commit-Protocol Split

**Why / When:** Every session boot loads the full protocol file. When you have 24 commits and only need 1, you're loading 23 specs worth of tokens on every `/status` check, every boot, every agent invocation — even when the session has nothing to do with those commits. Apply this at project init or whenever the protocol grows beyond ~5 commits.

**What changed:** `commit-protocol.md` was ~980 lines (24 full commit specs). It is now
~60 lines (index table + parallel groups + protocol rules only). Per-commit detail
blocks moved to `commit-specs/commit-XX.md`. Only the active commit's spec is loaded
per session.

**Estimated saving:** ~6–8k tokens per session boot (23 specs × ~40 lines avg = ~920
lines that were loaded and never used each session).

**Status:** Active — implemented 2026-05-09

**Notes:** The post-commit hook (`post_commit_next_step.py`) parses only the index table,
so the split is transparent to automation. `commit-specs/` added to Claude's domain in
`agent-config.json`.

**Example:** This project's commit-protocol.md was 980 lines. Of those, ~920 lines were
specs for commits that either hadn't started yet or were already done. A simple `/status`
call — which needs only the index table — was loading the full nginx config spec, the EC2
deployment spec, and all 21 other specs it had no use for. After the split, the same
`/status` call loads a 60-line file.

---

### 2. Selective Mira Invocation

**Why / When:** Mira adds value when there's a product decision to pressure-test. On a commit that creates an internal TypedDict, adds a unit test, or configures infra, there's no product decision — invoking her produces zero findings at real token cost.

**What changed:** Mira was previously invoked on every commit. Now invoked only on
commits with user-facing behavior changes: new/modified API endpoints, UI changes,
data the user sees, or interaction model shifts. Internal plumbing commits (schemas,
tests, infra, scoring functions) skip Mira entirely.

**Estimated saving:** ~2–3k tokens on ~14 of 24 commits where Mira would have run
but has no meaningful product input.

**Status:** Active — rule added to `team-preferences.md` 2026-05-09

**Notes:** Rule is dynamic (defined by commit type, not hardcoded commit numbers), so
it survives any future replanning.

**Example:** Commit 07 (`langgraph-state-schema`) creates `AgentState` and `AssessmentOutput` —
internal data structures with no user-visible behavior. Mira has nothing to evaluate.
Commit 17 (`adaptive-graph-integration`) extends `ChatResponse` with `user_level` and
`assessed_topics` — that's a product decision about what data the frontend receives and
what the user sees in their profile panel. Mira runs on 17, not 07.

---

### 3. Model Tiering

**Why / When:** Use this when you can predict the output shape before the agent starts. If the task is "write a one-line LEARNING_LOG entry", the output structure is known — Haiku handles it at ~5× less cost than Sonnet. If the task is "find the subtle async race condition in this LangGraph node", you need Opus's reasoning depth. Match the model to the cognitive demand.

**What changed:** Not every agent runs at Sonnet. Model assignments:
- **Haiku:** Ryan (tech writer), worklog-only updates, GLOSSARY one-liners
- **Sonnet:** Rex, Nova, Aria, Adam (all implementation work) — default
- **Opus:** Viktor (code review), Sage (security) — deep reasoning, use selectively

**Estimated saving:** Haiku costs ~20× less than Opus, ~5× less than Sonnet.
Ryan runs on every commit (LEARNING_LOG entry). Switching Ryan to Haiku alone
saves significant cost across all 24 commits.

**Status:** Active — model assignment table added to `team-preferences.md` 2026-05-09

**Notes:** Model is specified at Agent tool call time, not in agent definition files.
Default (unspecified) is Sonnet. Opus is invoked selectively — not every commit
needs deep review reasoning.

**Example:** Ryan's job on every commit is to write a LEARNING_LOG entry — format is
fixed, inputs are provided (diff + context), no reasoning challenge. Haiku. Viktor
reviewing the cross-domain touches in Commit 17 (Nova writing to Rex's `redis_cache.py`
and `chat.py`) needs to reason about contract violations, cache correctness, and domain
boundary intent. That's Opus. Using Haiku for Viktor or Opus for Ryan are both wrong
in opposite directions.

---

### 4. Diff-Only Context for Quality Gate Reviewers

**Why / When:** Apply on every gate wave. The agent definition file is loaded automatically when `subagent_type` is specified — sending it again in the prompt is like handing someone their own ID card when they already know who they are. Reviewers need the diff, the commit spec, and any interface contracts. Nothing else.

**What changed:** Reviewer agents (Viktor, Sage, Quinn, Mira) previously received
agent identity files + worklog headers + commit spec + diff. Identity files are now
stripped from reviewer context packages. Reviewers receive: diff + active commit spec
+ relevant interface contracts only.

**Estimated saving:** ~1–2k tokens per reviewer, ~3–6k per gate wave across all
4 reviewers. Compounds across all 24 commits.

**Status:** Active — note added to CLAUDE.md commit loop Step 8, 2026-05-09

**Notes:** The agent definition file (`.claude/agents/viktor.md` etc.) is automatically
loaded by the runtime when `subagent_type` is specified. Passing it again in the
context package prompt is redundant. Reviewers know who they are from their definition.

**Example:** Viktor's `.claude/agents/viktor.md` is ~150 lines of review philosophy,
calibration rules, and domain scope. Sending it in every gate wave across 24 commits =
3,600 wasted lines for Viktor alone. Across all four reviewers, the identity-file waste
compounds to ~12,000 lines over the full project. Removing them from context packages
costs nothing — Viktor still behaves identically because the runtime already loaded
his definition.

---

### 5. Proactive Worklog Archiving

**Why / When:** Apply before a worklog's sessions start compounding. Don't wait until it's already causing problems. By session 4, you're already paying for 3 sessions of history on every load — the right trigger is 3 sessions, not 5.

**What changed:** Archive trigger lowered from >5 completed sessions to >3.
`/archive-worklog` compresses old sessions into a short summary paragraph, keeping
worklog files small permanently.

**Estimated saving:** Cumulative — prevents 5–10k token bleed in later sessions
when worklogs grow. Rex will hit threshold first (~Commit 14); Nova shortly after.

**Status:** Active — threshold updated in `team-preferences.md` and CLAUDE.md, 2026-05-09

**Notes:** Archiving compresses the worklog *file*. The `/compact` command compresses
the *live conversation history* — these are complementary, not duplicates.

**Example:** Rex completes Commits 01–06 (6 sessions) across Phase 1. Without archiving,
by Commit 14 his worklog holds ~700 lines of Phase 1 detail — Commit 01 auth fixes,
Commit 02 typo corrections, all of it. When Nova loads Rex's current state to understand
the profile API interface, she gets 700 lines. After `/archive-worklog rex`, those 6
sessions compress to a ~60-line summary: key interfaces Rex owns, decisions that carry
forward, open handoffs to Nova. 90% smaller, zero information loss for current work.

---

## Planned / Not Yet Applied

### `/compact` Mid-Session

**Why / When:** Use this when a session has gone through many back-and-forth iterations — typically after a gate wave with multiple blocking findings that required multiple fix-and-resubmit cycles. Each exchange adds to the conversation history and approaches the context limit faster than a clean single-pass session.

**What it does:** Compresses the current conversation history into a summary when
a session gets long. Frees context window space without ending the session.

**When to apply:** Sessions with many back-and-forth iterations, or any session that
hits the 80% context threshold warning.

**Estimated saving:** Situational — most valuable on long multi-step commit sessions.

**Status:** Planned — apply reactively when sessions get long

**Example:** A commit that required 3 Viktor passes (finding → fix → re-review → fix →
re-review) builds up a long conversation history. By the time you're constructing the
final approval prompt, you're carrying all that back-and-forth. `/compact` summarizes
it to "Viktor flagged X, Y, Z — resolved in passes 2 and 3" without losing the key
findings that need to appear in the approval prompt.

---

### Worktree Isolation for Parallel Commits

**Why / When:** Required any time two parallel agents write to the same directory. Without it, you either serialize the commits (losing the parallelism benefit) or risk mid-session conflicts that require resolution work — which itself costs tokens.

**What it does:** `isolation: "worktree"` in Agent tool calls gives parallel agents
isolated git branch copies. Prevents agents from re-reading files that the other
agent just changed, and prevents merge conflicts mid-session.

**When to apply:** Wave B (commits 08 + 09 — both write to `src/agents/nodes/`).

**Estimated saving:** Indirect — avoids wasted re-reads and conflict resolution overhead.

**Status:** Planned — apply when Wave B is triggered

**Example:** Wave B — commits 08 and 09 both create files in `src/agents/nodes/`.
Without worktrees, if Nova-08 writes `retrieve.py` and Nova-09 writes `generate.py`
simultaneously, one agent may see the other's uncommitted file as unexpected working
tree state, stall, or produce a conflict that requires a separate resolution pass.
With `isolation: "worktree"`, each works on its own branch copy — results are merged
via standard git after both agents complete, with no in-session conflict risk.

---

## Rejected / Not Worth It

### Loading Only Active Worklog Header (Not Full Current State)

**Why / When considered:** The Current State Header is ≤50 lines — trimming it to 10 would save ~40 lines per agent load. Seemed like an easy win.

**Considered:** Loading only the first 10 lines of a worklog instead of the full
Current State Header (≤50 lines).

**Why rejected:** The 50-line budget is deliberate and already tight. The most
critical information — open handoffs and key interface contracts — often appears in
lines 10–50. Trimming below that risks silently dropping a handoff that would require
an entire rework commit to fix. The cost of a missed handoff (rework + gate wave) far
exceeds the cost of 40 extra lines on every load.

**Example:** Rex's Current State Header line 15 reads: "Nova (Commit 10): when LangGraph
replaces chain.py, format_history() MUST be carried forward — named deliverable, not
optional." If the header were trimmed to 10 lines, this handoff disappears. Nova builds
Commit 10 without knowing about it. The bug surfaces in Commit 11's smoke test. Fixing
it costs a new commit, a new gate wave, and documentation updates — easily 5–10× the
cost of the 40 lines saved.

---

## Token Budget Benchmarks

| Session type | Estimated tokens (before optimization) | Estimated tokens (after) |
|---|---|---|
| Boot sequence only | ~10k | ~3k |
| Full commit loop (one agent) | ~30–40k | ~18–22k |
| Quality gate wave (4 reviewers parallel) | ~10–15k | ~6–9k |
| Documentation commit (Ryan on Haiku) | ~5k | ~1–2k |

*Estimates based on observed session costs through Commit 06. Actual costs vary
by diff size and agent worklog length. Update this table as real measurements are collected.*
