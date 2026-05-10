# Token Optimization Log
> Records all methods applied (or considered) to reduce token cost in this project.
> Each entry explains why it works, when to apply it, and a real example from this project.
> Extend this document as new techniques are tried.
> Last updated: 2026-05-10 (Methods 14–16 added — constraint enforcement hardening)

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
| Viktor | **Every 5 commits** (commits 5, 10, 15, 20) | All other commits |
| Sage | Auth/secrets/external APIs/file ops/new public routes — **any commit, immediately** | Node internals, schema files, test additions, infra config, doc-only |
| Quinn | **Every 5 commits**, same wave as Viktor | All other commits |
| Mira | User-facing API shape, UI, data the user sees — **any commit, immediately** | Internal plumbing (nodes, schemas, infra, scoring functions) |
| Ryan | **Every commit** — tight brief, no raw diff | Never skip |

**Gate-fix passes: eliminated.** If a reviewer blocks, the fix goes into the next commit — never a re-review within the same loop.

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

**Why lines 1–99 only (updated: now ~38 lines):** The template section is stable and small. The entries section grows without bound. After Commit 12 cost 54k tokens largely from a 99-line template, this was tightened further — Claude now passes only the Full Entry format block (~38 lines, template lines 51–88), not the full header + one-liner section. Ryan's context is always ~38 lines of format + 150-word brief, regardless of how many commits have been made.

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

### 10. 5-Commit Gate Cadence + System-Breaking-Only Blocking

**Why / When:** Commit 12 cost ~297k tokens despite being a straightforward scaffold commit. The breakdown: Nova implementation (65k) + Viktor first pass (50k) + Quinn (44k) + Nova gate-fix (30k) + Viktor re-review (36k) + Ryan (54k) + commit (19k). The gate-fix cycle alone cost 66k tokens to fix a dead `if` statement — a non-breaking style issue that could have waited or been fixed in the next commit. The root problem: Viktor was blocking on things that didn't break anything.

**What changed:** Three decisions made together:

1. **Viktor + Quinn cadence: every 5 commits.** They run on commits 5, 10, 15, 20 — reviewing all accumulated diffs in one pass, not per commit. Sage and Mira keep their existing triggers (immediately on relevant commits).

2. **Blocking criteria narrowed to system-breaking only.** Viktor and Sage now only hard-block on code that will break the system at runtime: crashes, data corruption, auth bypass, exploitable security holes, import failures. Everything else — dead code, missing annotations, style, minor patterns — goes into a deferred log and surfaces at the 5-commit review, not as an immediate stop.

3. **Gate-fix passes eliminated.** If a reviewer blocks, the fix is the next commit in the queue. No re-review within the same loop. This removes an entire class of expensive back-and-forth cycles.

**The reasoning behind "system-breaking only":** For a portfolio project at learning pace, the cost of a ghost `if` statement existing for 5 commits is zero — it doesn't affect users, it doesn't cascade, it can be cleaned up. The cost of catching it immediately is a full gate-fix cycle. The tradeoff is obvious at this scale. A production system serving real users would have a different calculus.

**Estimated saving:** Commit 12 under the new rules: Nova implementation (~40k) + Sage if triggered (~5k) + Ryan (~8k) + commit (~5k) = ~55–60k total. No Viktor/Quinn until commit 15. No gate-fix pass. Saving vs. actual: ~240k tokens on this one commit.

Over the 12 remaining commits: Viktor/Quinn run 2–3 times total instead of 12 times. Gate-fix passes: zero. Estimated cumulative saving: 800k–1.2M tokens.

**Status:** Active — updated `team-preferences.md` 2026-05-10

**What this trades away:** Issues caught at commit 12 may be present in commits 13–16 before Viktor sees them. If Nova repeats a pattern mistake across 4 commits, the fix is larger. Acceptable tradeoff at portfolio scale — not the right call for a production codebase with real users.

**Example:** Commit 12's gate-fix cycle: Viktor flagged a dead `if state.get("assessment_error"): return "update_profile" / return "update_profile"` — both branches returning the same value. Correct finding. But this doesn't crash the app, doesn't corrupt data, doesn't break any user. Under the new model: Viktor notes it in his deferred log at commit 15, Nova fixes it in a one-line cleanup. Cost: 0 extra tokens at commit 12. Under the old model: gate-fix pass + re-review = 66k tokens.

---

### 11. Tiered Context Loading — Summary Companion Files

**Why / When:** Every agent invocation was loading LEARNING_LOG.md (848 lines at C12, ~1700 by C24), DECISIONS.md (313 lines), and ARCHITECTURE.md (232 lines) by default — even when the agent only needed a quick structural overview. This is a flat tax that compounds with project age: every new commit adds to these files, so every subsequent invocation costs more. The fix is to convert flat taxes into usage-based costs.

**What changed:** Four new files created and wired into ORCHESTRATION.md + CLAUDE.md:
- `LEARNING_LOG_SUMMARY.md` — one-liner per entry (C01–C12); Ryan appends one line per commit in the same pass as the full entry
- `ARCHITECTURE_SUMMARY.md` — 8-line system overview; Claude updates when ARCHITECTURE.md changes
- `DECISIONS_INDEX.md` — 36 one-liner decisions; replaces DECISIONS.md as the always-loaded file

All three summaries are always loaded (~50 lines total). Full docs loaded on demand only — e.g., an agent building a node that touches AgentState pulls the relevant DECISIONS.md section, not all 313 lines.

**LEARNING_LOG eviction rule:** When entry count reaches 40, Ryan compresses the oldest 20 into an era block (`learning-log-archive-era[N].md`) before writing the new entry. The file never grows unbounded.

**Maintenance obligation:** Every agent that writes to a full doc updates its summary in the same pass. Enforced by the Step 9 checklist. An outdated summary is worse than none — it actively misleads.

**Estimated saving:** ~1,400 lines of docs replaced by ~50 lines of summaries on typical invocations. Across 12 remaining commits, most agents never need the full docs — estimated 300–500k tokens saved in total invocation overhead.

**Status:** Active — implemented 2026-05-10, committed f0a64d7

---

### 12. Pre-Commit Contract Validation (Linter Gate)

**Why / When:** Pattern mistakes — wrong node signature, sync LLM call, blocking I/O inside async generator — were caught by Viktor at commit N but may have propagated across commits N-1 through N-4 before the 5-commit review fires. A pattern present in 4 commits means 4 files to fix instead of 1. The linter catches violations at the commit they're introduced, when the blast radius is 1 file.

**What changed:** `CONTRACTS.md` created with all project-wide interface contracts (node function signatures, LLM invocation pattern, blocking I/O placement, state key constraints, dynamic SQL allowlist standard, SSE event schema, auth dependency rules). Step 7.5 added to the commit loop in ORCHESTRATION.md: a lightweight linter subagent runs after tests pass, before the gate wave. Context: diff + CONTRACTS.md only — no identity file, no history. If it fails, it returns the exact violated rule to the owning agent immediately, without spending any Viktor tokens.

**Estimated saving:** Each prevented gate-fix cycle saves ~66k tokens (Commit 12 actual cost of a fix pass). The linter costs ~2–3k tokens per commit (12 commits × ~2.5k = ~30k total). Break-even: it needs to prevent one gate-fix cycle across the remaining 12 commits. Expected to prevent 2–4 based on the pattern of Viktor findings in commits 07–12.

**Status:** Active — CONTRACTS.md + ORCHESTRATION.md Step 7.5 implemented 2026-05-10, committed f0a64d7

---

### 13. Implementor Execution Constraints

**Why / When:** Apply to every implementor invocation. Each tool use in a long-running agent session adds a full context echo — at 73 tool uses and 122k tokens, Commit 13's Nova was paying ~1,700 tokens of overhead per tool call on average. The read-modify-read spiral (read file → write partial → re-read file → continue writing) is the primary driver. Mid-task worklog writes compound this: every incremental update re-echoes the full growing context before the agent can continue.

**What changed:** Every implementor prompt (Nova, Rex, Aria, Adam) now includes a verbatim constraint block:

```
EXECUTION CONSTRAINTS:
- Max tool uses: 25. Plan your reads upfront. Batch your writes. If you hit 25 and aren't done, stop and report.
- Two phases only: Phase 1 — all reads. Phase 2 — all writes. No reads in Phase 2.
- Do not re-read any file you have already read this session.
- Worklog: one write at task completion only. No mid-task worklog updates.
- Test runs: maximum 2. On second failure, report what failed and stop — do not loop.
- Code comments: one line max, functional only. No explanatory prose, no narration.
```

Token budget target revised: ≤60k for implementation agents (Sonnet), ≤15k per review/doc agent (Haiku).

**Estimated saving:** Commit 13 Nova: 73 tool uses, 122k tokens. A comparable commit with constraints applied should run 20–25 tool uses at 50–70k tokens — a 40–50% reduction. The two-phase protocol eliminates the read-after-write spiral. The worklog constraint eliminates mid-task context echo. The test limit prevents open-ended fix loops.

**Status:** Active — Implementor Execution Constraints section added to `team-preferences.md` 2026-05-10; triggered by Commit 13 actual (122k / 73 tool uses)

**Example:** Commit 13 Nova's 73 tool uses included: read assess.py, read state.py, read graph.py, read existing tests, write prompts/__init__.py, re-read assess.py, write assess.py, write assessment.py, run tests (first pass), fix and re-run, write test additions, write worklog (incrementally, multiple times). With two-phase: Phase 1 reads assess.py + state.py + existing tests (3 reads). Phase 2 writes all output files + runs tests twice + writes worklog once. Estimated: 15–20 tool uses instead of 73.

---

### 14. Constraints Baked into Agent Identity Files

**Why / When:** Apply once, permanently. Execution constraints existed only in `team-preferences.md` and required Claude to manually copy them into every agent invocation prompt. Viktor hit 59 tool uses in the Commit 15 wave (61k tokens) and Nova hit 34 uses (over the 25 cap) in the same session — both because Claude omitted the constraint block. A rule that depends on orchestrator memory will be forgotten.

**What changed:** The verbatim constraint block for each agent type was added directly to the agent's identity file (`.claude/agents/*.md`) in a dedicated `## Execution Constraints` section:

- **Implementors (Nova, Rex, Aria, Adam):** 25-tool cap, two-phase read/write, no mid-task worklog writes, max 2 test runs — added to `ai-engineer.md`, `backend.md`, `frontend.md`, `devops.md`
- **Reviewers (Viktor, Sage, Quinn):** 25-tool cap, diff-only, targeted reads only — added to `reviewer.md`, `security.md`, `qa.md`
- **Ryan:** 5-tool cap, Edit-only — added to `tech-writer.md`
- **Mira:** 5-tool cap, no file reads — added to `product.md`

**Why this works:** Agent identity files are loaded automatically by the runtime when `subagent_type` is specified — before the prompt is even read. The constraints now fire unconditionally, regardless of what Claude includes or omits in the invocation prompt.

**Estimated saving:** Prevents the Viktor-59-tool-use scenario (61k tokens) and Nova-34-tool-use scenario. Across remaining commits, preventing one such overrun per commit = 30–60k tokens saved per occurrence.

**Status:** Active — implemented 2026-05-10, committed 731860e

**Notes:** This is a defense-in-depth layer. The constraint block in the identity file + the runtime hook (Method 15) + Claude including the constraint in the invocation prompt = three independent layers. All three must fail simultaneously for an overrun to occur.

**Example:** Viktor's Commit 15 wave used 59 tool uses (61k tokens, 2.4× over the ≤25 cap). Root cause: Claude's invocation prompt omitted the reviewer constraint block. With constraints in the identity file, Viktor reads his constraint on boot — before any invocation prompt is processed. Same finding quality, 25 tool uses max.

---

### 15. Runtime Tool-Use Cap (PreToolUse Hard Block)

**Why / When:** Methods 13 and 14 rely on the LLM following instructions. An LLM can lose track of a constraint as context grows — it's probabilistic, not deterministic. A runtime hook that intercepts tool calls before they execute provides a hard guarantee that no agent can exceed 25 tool uses, regardless of whether it "remembers" the constraint.

**What changed:** `hooks/tool_cap_enforce.py` registered as `PreToolUse` with empty-string matcher (fires on all tool calls). Logic:

1. If `tool_cap.json` has `active: false` → exit 0 (not in a subagent session, skip)
2. If the tool call is Write/Read/Edit to `tool_cap.json` itself → exit 0 (always allow orchestrator file management)
3. If the tool call is `Agent` spawning → exit 0 (orchestrator action, not a subagent tool use)
4. Increment counter. If count > 25 → exit 2 (BLOCK with message). Agent cannot proceed.

Exit code 2 in Claude Code's hook system means the tool call is hard-blocked — it does not execute. The agent receives the stderr message and must stop.

**Estimated saving:** Prevents runaway agents. At the token rates observed (Nova: ~1,700 tokens overhead per tool call at 73 uses), blocking at 26 instead of 73 saves ~80k tokens on a Nova spiral. For Viktor at 59 uses vs 25: ~56k tokens saved.

**Status:** Active — implemented 2026-05-10, committed ac29adf

**Notes:** Fail-open by design: any I/O error reading/writing `tool_cap.json` causes exit 0 (allow through). A broken hook must never block legitimate work. The counter file `hooks/tool_cap.json` is committed to the repo and holds `active: false` at rest.

**Example:** Nova exceeds 25 tool calls while reading files speculatively. Tool call #26 triggers `tool_cap_enforce.py`. Script reads `active: true`, count becomes 26, 26 > 25 → exit 2. Nova receives: "TOOL CAP REACHED — nova has used 25/25 tools. STOP NOW. Report what you completed, what files changed, and what remains." Nova stops. Orchestrator reads the partial report.

---

### 16. Auto-Wired Cap Lifecycle (Agent Tool Hooks)

**Why / When:** Method 15 requires `tool_cap.json` to have `active: true` during agent execution. The original design had the orchestrator write this flag manually before/after each `Agent()` invocation. That reintroduced a human-error vector — if Claude forgot the Write call, no enforcement. The fix: wire the flag to the `Agent` tool itself so it sets and clears automatically with zero orchestrator action.

**What changed:** Two new hooks registered in `.claude/settings.json`:

- `PreToolUse:Agent` → `hooks/tool_cap_start.py` — fires before every `Agent()` call; sets `active: true`, extracts agent name from `subagent_type`, resets `count: 0`
- `PostToolUse:Agent` → `hooks/tool_cap_end.py` — fires after every `Agent()` returns (success or error); resets `active: false`, `count: 0`

The orchestrator no longer touches `tool_cap.json`. The runtime manages it.

**Execution sequence:**
```
Orchestrator calls Agent(subagent_type="nova")
  PreToolUse:Agent  → tool_cap_start.py  → active=true,  count=0   (automatic)
  PreToolUse:""     → tool_cap_enforce.py → Agent call excluded     (automatic)
  [subagent runs — each tool call counted and blocked at 26]
  PostToolUse:Agent → tool_cap_end.py    → active=false, count=0   (automatic)
```

**Estimated saving:** Eliminates one entire failure mode (forgot-to-set-flag). No direct token saving — it's a correctness guarantee that ensures Method 15 actually fires on every subagent invocation.

**Status:** Active — implemented 2026-05-10, committed 873ee14

**Notes:** Limitation: not safe for nested `Agent()` calls — the inner Agent spawn would reset count to 0 and then PostToolUse would set active=false, breaking the outer agent's cap. This project does not use nested agents. If it ever does, per-agent counter files are the fix.

**Example:** Without Method 16, the sequence was: Claude writes `tool_cap.json` (active=true) → calls `Agent()` → agent runs → Claude writes `tool_cap.json` (active=false). If Claude forgot step 1, the entire cap was inactive. With Method 16: PreToolUse:Agent fires unconditionally when `Agent()` is called — there is no step 1 for Claude to forget.

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

| Session type | Commits 01–10 actual | Commit 11–12 actual | C13 actual | Target (C14+) |
|---|---|---|---|---|
| Boot sequence only | ~10k | ~3k | ~3k | ~3k |
| Implementation agent (Sonnet) | ~30–50k | ~65k | **122k** | ≤60k |
| Sage security review (Haiku) | ~20k | not triggered | **34k** | ≤15k |
| Ryan LEARNING_LOG full entry (Haiku) | ~50k | ~54k | **32k** | ≤15k |
| Gate wave — all 4 triggered (Haiku) | ~180k | ~94k | — | ~15–20k (5-commit batch) |
| Gate wave — Viktor only (Haiku) | ~60k | ~50k | — | eliminated between waves |
| Gate-fix re-run | ~60k | ~66k | — | **eliminated** |
| **Full commit — Sage triggered (no gate wave)** | **~260k** | **~297k** | **~188k** | **≤90k** |
| **Full commit — no gate wave, no Sage** | **~200k** | n/a | — | **≤75k** |
| **5-commit gate wave (Viktor + Quinn, Haiku)** | n/a | n/a | — | **~20–30k total** |

**Hard target (updated):** ≤60k implementation agent · ≤15k per review/doc agent · ≤90k full commit with Sage triggered.

---

### Commit 13 — Per-Agent Breakdown

| Agent | Model | Tokens | Tool Uses | Target | Delta |
|---|---|---|---|---|---|
| Nova | Sonnet | 122,128 | 73 | ≤60k | **+62k** |
| Sage | Haiku | 34,369 | 10 | ≤15k | **+19k** |
| Ryan | Haiku | 32,108 | 5 | ≤15k | **+17k** |
| **Total (subagents)** | | **188,605** | **88** | **≤90k** | **+99k** |

**Root causes by agent:**
- **Nova (+62k):** Read-modify-read spiral. 73 tool uses = ~1,700 tokens context-echo overhead per call. Mid-task worklog writes echoed growing context repeatedly. → Fixed by Execution Constraints (Method 13).
- **Sage (+19k):** Read files beyond the diff despite targeted prompt — went to `state.py`, `chat.py`, and provider code to trace the data flow. Defensible but expensive. → Partially addressed by tighter targeted-file-only wording.
- **Ryan (+17k):** High-context prompt (template + 15-line anchor + 300-word brief) + substantive LEARNING_LOG entry output. Largely unavoidable for a full entry. → One-liner entries will cost ~3k; full entries are a fixed cost.

---

**What changed at Commit 13 (rules added post-commit):**
Gate-fix passes eliminated · Viktor/Quinn cadence every 5 commits · Ryan template trimmed 99 → 38 lines · Viktor/Sage block only on system-breaking issues · **Implementor Execution Constraints added** · **Token budget targets revised to ≤60k/≤15k**

**Actual vs. target tracking:**

| Commit | Actual (subagents) | Target | Delta | Root cause |
|---|---|---|---|---|
| 10 | ~220k | — | baseline | All rules established after this |
| 11 | ~35k | — | good | Test-only, Viktor only |
| 12 | ~297k | 55k | 5.4× | Gate-fix pass + oversized prompts |
| 13 | **188k** | ≤90k | **2.1×** | Nova read-modify-read spiral (rules not yet applied) |
| 14 | **72k** | ≤75k | **✅ under** | First commit with Method 13 applied — Rex hit 25 cap exactly |
| 15 (attempt) | **260k** | ≤90k | **2.9×** | Viktor 59 tool uses (61k) — constraint block omitted from invocation; Nova 34 tool uses (+35k); Viktor hard-blocked |
| 15 (fix) | **112k** | ≤75k | over | Rex 11 tool uses ✅; Ryan anomaly 50k for one-liner (root cause: large Edit anchor) |
| 16 | TBD | ≤75k | — | First commit with Methods 14+15+16 all active |
| 17+ | TBD | ≤75k | — | Full three-layer enforcement |

**What changed after Commit 15:**
Methods 14 (constraints in identity files) + 15 (PreToolUse hard block) + 16 (auto-wired lifecycle) all implemented. Commit 16 is the first commit where all three layers fire together.

**Viktor anomaly (Commit 15 attempt):** 59 tool uses / 61k tokens against a ≤25 / ≤20k target. Root cause: Claude omitted the reviewer constraint block from the invocation prompt. Fixed by Method 14 (baked into `reviewer.md`) + Method 15 (hard block at 26). Not possible to repeat under the current setup.

*Updated 2026-05-10 — Methods 14, 15, 16 added post-Commit 15 session. Commit 14 actual: 72k ✅. Commit 15 attempt: 260k (Viktor hard block). Commit 15 fix: 112k.*
