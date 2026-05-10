# Token Optimization Log
> Records all methods applied (or considered) to reduce token cost in this project.
> Each entry explains why it works, when to apply it, and a real example from this project.
> Extend this document as new techniques are tried.
> Last updated: 2026-05-10

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

**Why / When:** Use this when you can predict the output shape before the agent starts. If the task is "write a one-line LEARNING_LOG entry", the output structure is known — Haiku handles it at ~5× less cost than Sonnet. Match the model to the cognitive demand, and never pay for reasoning you don't need.

**What changed (updated 2026-05-10):** Two tiers only — Opus is banned entirely.
- **Haiku:** Viktor, Sage, Quinn, Mira, Ryan — all reviewers and writers
- **Sonnet:** Rex, Nova, Aria, Adam — all implementation work
- **Opus:** ~~banned~~ — Commit 10 gate wave proved Opus at scale is unsustainable

**Estimated saving:** Commit 10's gate wave cost ~180k tokens on 4 Opus/Sonnet reviewer agents run twice. At Haiku, the same wave costs ~15–20k. Over 14 remaining commits, banning Opus saves hundreds of thousands of tokens.

**Status:** Active — updated `team-preferences.md` 2026-05-10

**Notes:** Model is specified at Agent tool call time. Default (unspecified) inherits parent model (Sonnet). Haiku is sufficient for reviewers because their task is structured: read a diff, apply a checklist, report findings. They don't need deep open-ended reasoning — they need pattern recognition and rule application.

**Example:** Viktor reviewing Commit 10's async streaming code on Haiku found all three advisories (dead code, stale comment, chain.py placeholder) and confirmed the two gate fixes were correct. The same findings that previously cost ~60k tokens on Opus cost ~8k on Haiku. The quality difference on well-defined review tasks is smaller than expected.

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

### 6. Conditional Quality Gate Triggers

**Why / When:** Running Viktor + Sage + Quinn + Mira on every commit regardless of what changed is the single largest avoidable token cost in the loop. A commit that adds a LangGraph node has no auth surface, no new routes, and no user-facing API change — Sage, Quinn, and Mira have nothing to evaluate. Invoking them produces zero findings at real cost.

**What changed (updated 2026-05-10):** Each reviewer now has an explicit trigger condition.

| Reviewer | Trigger | Skip when |
|---|---|---|
| Viktor | **Every commit** | Never skip |
| Sage | Auth/secrets/external APIs/file ops/new public routes with user input | Node internals, schema files, test additions, infra config, doc-only |
| Quinn | New service, new route, behavior change to existing route, new LangGraph node | Schema-only, infra, test-only additions, pure refactors |
| Mira | User-facing API shape, UI, data the user sees | Internal plumbing (nodes, schemas, infra, scoring functions) |
| Ryan | **Every commit** — tight brief, no raw diff | Never skip |

**Gate-fix pass rule:** If a reviewer blocks, fix and re-run **only the blocking reviewer** — not the full wave. Exception: if the fix touches a different domain, re-run all triggered reviewers.

**Estimated saving:** Commit 10 ran 4 agents twice = 8 reviewer passes. Under the new rules, Commit 10 would trigger Viktor + Sage (external API call, new public route, secrets) + Quinn (new route, behavior change) + Mira (API shape changed JSON → SSE) — so all 4 triggered, but on Haiku instead of Opus/Sonnet, and the fix pass re-runs only Quinn (the blocker). 4 + 1 = 5 passes at Haiku ≈ 30k tokens vs the actual 290k.

For a typical internal commit (e.g., Commit 11 graph smoke test): Viktor only. 3 agents skipped entirely.

**Status:** Active — Quality Gate Trigger Rules added to `team-preferences.md` 2026-05-10

**Example:** Commit 11 (`langgraph-graph-smoke-test`) adds integration tests, no new routes, no auth touches, no API shape changes. Gate wave: Viktor (Haiku) only. Sage, Quinn, and Mira all skip. Estimated: 5–8k tokens for the entire gate wave.

---

### 7. Quality Gate Pre-Brief for Implementors

**Why / When:** When Nova's first implementation pass misses things Viktor will catch, you get two Nova passes + two Viktor passes instead of one each. The fix is to tell Nova upfront what Viktor checks. This costs ~100 tokens in the invocation prompt and routinely prevents an entire re-review cycle worth 50–100k tokens.

**What changed:** All implementor invocations (Nova, Rex, Aria, Adam) now include a standard "Viktor will check:" list in the prompt:
- All collection types explicitly typed (not bare `list`/`dict`)
- Finite-value string fields use `Literal[...]`
- Documented constraints enforced in code (not just docstrings)
- Test file exists covering all spec gate conditions
- No domain boundary violations

**Estimated saving:** ~50–100k tokens on commits where the first implementation pass would otherwise miss a Viktor concern.

**Status:** Active — Quality Gate Pre-Brief section added to `team-preferences.md` 2026-05-09

**Example:** Commit 07 Nova first pass: bare `docs: list`, `user_level: str`, `cache_hit: str`, no test file. Viktor blocked on all four. Nova fixed them. Full re-review. Total: 4 agent passes. With a pre-brief, Nova's first pass includes `list[Document]`, `Literal[...]` types, field validators, and a test file. Viktor sees a clean diff. 2 agent passes instead of 4.

---

### 8. Ryan Context Restriction (updated 2026-05-10)

**Why / When:** Ryan reads the full `LEARNING_LOG.md` before writing each entry to match the format. The file grows by ~100 lines per commit. By Commit 24 it will be 2,400+ lines — Ryan reads all of it just to append 10 lines. Even on Haiku, this compounds to thousands of wasted tokens per commit. The fix is template injection, not skipping Ryan — the LEARNING_LOG is the Team Lead's primary learning artifact and must be updated every commit.

**What changed:** Ryan never reads `LEARNING_LOG.md`. Instead:
1. **Claude** reads lines 1–99 only (the header + Entry Format Reference — the template section, not the entries)
2. Claude embeds those lines verbatim in Ryan's prompt — this guarantees format consistency without reading entries
3. Claude passes a 150–200 word commit brief (written by Claude, not the raw diff)
4. Claude signals entry type: "full" or "one-liner"
5. Ryan appends using `Write` — never reads the file first

**Why lines 1–99 only:** The template section is stable and small. The entries section grows without bound. Separating them means Ryan's context is always ~100 lines of template + ~200 word brief, regardless of how many commits have been made.

**Estimated saving:** Commit 07 Ryan: 55k tokens (read 400-line file, wrote 50 lines). New approach: ~3k tokens (100-line template + brief + write). Saving: ~52k tokens for that one Ryan call. Across 14 remaining commits: ~728k tokens saved.

**Status:** Active — Ryan context rule updated in `team-preferences.md` 2026-05-10

**Example:** At Commit 24, LEARNING_LOG.md will be ~2,400 lines. Old approach: Ryan reads all 2,400 lines on Haiku before writing 10 new lines. New approach: Claude reads lines 1–99 (the template), passes a 200-word brief, Ryan appends. Ryan's context is identical at Commit 1 and Commit 24 — the template doesn't grow.

---

### 9. Orchestrator Read Discipline

**Why / When:** Every file read in the main session context adds to the running conversation history. That history is re-sent with every subsequent message in the session. Reading ARCHITECTURE.md + GLOSSARY.md + DECISIONS.md + 3 commit specs "just in case" adds 500+ lines to the context that compounds across every subsequent tool call.

**What changed:** Files are read only at the moment they are needed for a specific decision or edit. No speculative reads. If a file will be edited, read it immediately before the edit — not at session start.

**Estimated saving:** 5–15k tokens per session depending on how many files would have been speculatively loaded.

**Status:** Active — Orchestrator Read Discipline section added to `team-preferences.md` 2026-05-09

**Example:** Commit 07 session: ARCHITECTURE.md, GLOSSARY.md, DECISIONS.md, commit-specs/07, 09, 10, project-state.json, state.py, nova-worklog.md, test_agent_state.py all loaded into main context sequentially. Most of these were read before they were needed. Reading ARCHITECTURE.md at the moment of editing it (not 20 messages earlier) would have eliminated those lines from all intermediate context windows.

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

| Session type | Before (Commits 01–10) | Target (Commit 11+) |
|---|---|---|
| Boot sequence only | ~10k | ~3k |
| Full commit loop — implementation (Sonnet) | ~30–50k | ~8–12k |
| Gate wave — all 4 triggered (Haiku) | ~180k | ~15–20k |
| Gate wave — Viktor only (Haiku) | ~60k | ~5–8k |
| Gate-fix re-run — blocking reviewer only | ~60k | ~3–5k |
| Ryan LEARNING_LOG entry | ~50k | ~2–3k |
| **Full commit end-to-end (typical internal)** | **~200k** | **~12–18k** |
| **Full commit end-to-end (complex, all gates)** | **~300k** | **~25–35k** |

**Hard target:** 11–15k per commit for internal/plumbing commits. ≤35k for complex
commits where all gates are triggered.

*Updated 2026-05-10 based on Commit 10 actual cost (~220k) and new Haiku + conditional-gate rules.*
