# TOKEN_RECORDS.md — Per-Commit Token Usage
> One table per commit. Captured at commit time — not reconstructed after the fact.
> Goal: track whether token reduction methods are working while quality holds.
> Quality signal: tests pass · no Viktor hard blocks · learning log entry written.
>
> Companion file: TOKEN_OPTIMIZATION.md — the methods behind the numbers.
> Last updated: 2026-05-12 (Commit 25)

---

## How to Read This

Each commit has:
- **Per-agent row:** agent name, model tier, tokens consumed, tool uses
- **Total row:** sum across all agents invoked this commit (orchestrator reads not included — subagents only)
- **Gate wave:** which reviewers ran, which were skipped and why
- **vs. target:** delta against the ≤60k implementation / ≤15k reviewer target

Token counts come from the `<usage>` block returned by each Agent tool call.
Orchestrator (Claude main context) reads are not captured — only subagent costs.

---

## Commits 01–09

No token data recorded. Tracking began at Commit 10.

---

## Commit 10 — `langgraph-graph-assembly` · 2026-05-10 · Nova

> Gate wave ran at Commit 10: Viktor + Sage + Quinn + Mira (Opus/Sonnet — pre-model-tiering).
> Nova fix pass ran after gate. Gate re-ran. Two full cycles.

| Agent | Model | Tokens | Tool Uses | Notes |
|---|---|---|---|---|
| Nova (implementation) | Sonnet | — | — | not captured individually |
| Viktor | Opus | — | — | not captured individually |
| Sage | Opus | — | — | not captured individually |
| Quinn | Opus | — | — | not captured individually |
| Mira | Sonnet | — | — | not captured individually |
| Ryan | Haiku | — | — | not captured individually |
| **Total (estimated)** | | **~220,000** | — | estimate from TOKEN_OPTIMIZATION.md |

**vs. target:** n/a — rules not yet established at this commit.
**What happened:** First commit with all 4 reviewers active. Gate-fix pass ran (Quinn blocked). Opus across reviewers is the primary cost driver.

---

## Commit 11 — `langgraph-graph-smoke-test` · 2026-05-10 · Nova

> Gate wave: Viktor only (test-only commit — Sage, Quinn, Mira skipped).

| Agent | Model | Tokens | Tool Uses | Notes |
|---|---|---|---|---|
| Nova (implementation) | Sonnet | — | — | not captured individually |
| Viktor | Opus | — | — | not captured individually |
| Ryan | Haiku | — | — | not captured individually |
| **Total (estimated)** | | **~35,000** | — | estimate from TOKEN_OPTIMIZATION.md |

**vs. target:** n/a — rules not yet established at this commit.
**What happened:** Clean commit — test additions only. Viktor found 1 advisory (unused helper). Lowest cost commit so far.

---

## Commit 12 — `langgraph-assessment-scaffold` · 2026-05-10 · Nova

> Gate wave: Viktor + Quinn (new async node + conditional routing).
> Gate-fix pass ran after Viktor blocked on dead `if` statement.
> Gate re-ran on updated diff. Two Viktor passes, two Quinn passes.

| Agent | Model | Tokens | Tool Uses | Notes |
|---|---|---|---|---|
| Nova (implementation) | Sonnet | — | — | not captured individually |
| Viktor (pass 1) | Opus | — | — | not captured individually |
| Quinn (pass 1) | Haiku | — | — | not captured individually |
| Nova (gate-fix) | Sonnet | — | — | not captured individually |
| Viktor (pass 2) | Opus | — | — | not captured individually |
| Ryan | Haiku | — | — | not captured individually |
| **Total (estimated)** | | **~297,000** | — | estimate from TOKEN_OPTIMIZATION.md |

**vs. target:** n/a — new rules established *after* this commit.
**What happened:** Gate-fix cycle alone cost ~66k. Ryan consumed ~54k (read full LEARNING_LOG before writing). This commit triggered Methods 10, 11, 12, 13 in TOKEN_OPTIMIZATION.md.

---

## Commit 13 — `langgraph-assessment-llm` · 2026-05-10 · Nova

> Gate wave: Sage only (external OpenAI API call — triggered immediately).
> Viktor/Quinn skipped (next wave at Commit 15).
> **First commit with Method 6 (conditional gates) applied.**
> **Last commit before Method 13 (execution constraints) applied.**

| Agent | Model | Tokens | Tool Uses | vs. Target |
|---|---|---|---|---|
| Nova (implementation) | Sonnet | 122,128 | 73 | **+62k** over ≤60k |
| Sage | Haiku | 34,369 | 10 | **+19k** over ≤15k |
| Ryan | Haiku | 32,108 | 5 | **+17k** over ≤15k |
| **Total** | | **188,605** | **88** | **+99k over ≤90k** |

**Root causes:**
- Nova: read-modify-read spiral (73 tool uses = ~1,700 tokens overhead/call); mid-task worklog writes echoed growing context
- Sage: read beyond targeted files to trace data flow through state.py, chat.py, provider code
- Ryan: full 99-line template passed + substantive entry output (unavoidable for full entry at the time)

**What changed after this commit:** Method 13 (Execution Constraints) added — ≤25 tool uses, two-phase read/write, one worklog write. Ryan template trimmed 99→38 lines.

---

## Commit 14 — `topic-scoring-service` · 2026-05-10 · Rex

> Gate wave: none (Viktor/Quinn cadence hits at Commit 15).
> Sage not triggered (pure function — no auth, secrets, or external API).
> Mira not triggered (internal service, not user-facing).
> **First commit with Method 13 (Execution Constraints) applied.**

| Agent | Model | Tokens | Tool Uses | vs. Target |
|---|---|---|---|---|
| Rex (implementation) | Sonnet | 45,344 | 25 | ✅ under ≤60k |
| Ryan | Haiku | 26,579 | 5 | **+12k** over ≤15k |
| **Total** | | **71,923** | **30** | ✅ well under ≤90k |

**Notes:**
- Rex hit the 25 tool-use cap exactly — two-phase discipline held.
- Ryan over target: full entry (ARCHITECTURE.md + DECISIONS.md updated) — full entries cost ~25k; one-liners should cost ~3k. Not a regression.
- No gate wave = lowest-cost commit type. Commit 15 will show gate wave cost at the new Haiku cadence.

**Compared to Commit 13:** 188,605 → 71,923 tokens (**−62% reduction**). Implementation agent alone: 122,128 → 45,344 (**−63%**).

---

## Commit 15 — `fix-score-delta-semantics` · 2026-05-10 · Rex

> Gate wave: none (Viktor already ran on this wave; no re-run per no-gate-fix-pass rule).
> Sage not triggered. Mira not triggered.
> Ryan: one-liner (bug fix — not architectural).

| Agent | Model | Tokens | Tool Uses | vs. Target |
|---|---|---|---|---|
| Rex (implementation) | Sonnet | 61,967 | 11 | **+2k** over ≤60k (marginal) |
| Ryan | Haiku | 50,023 | 4 | **+35k** over ≤15k |
| **Total** | | **111,990** | **15** | over ≤75k combined |

**Notes:**
- Rex: 11 tool uses (well under 25 cap) — two-phase discipline held cleanly. Fix was a 2-line change + 14 new tests.
- Ryan: 50k for a one-liner is anomalous — suggests the Edit anchor was large or Ryan did unexpected reads. Expected ~3k. One-liner entries should be investigated.
- Viktor anomaly from the blocked attempt (59 tool uses) logged separately in the attempt entry above.

**Compared to blocked attempt (Nova + gates):** 260,447 → 111,990 tokens. The fix-in-own-commit approach is dramatically cheaper than a gate-fix-re-review cycle even with Ryan's anomaly.

---

## Commit 15 (attempt) — `profile-update-node` · 2026-05-10 · Nova

> Gate wave: Viktor + Quinn (5-commit cadence wave).
> Sage not triggered (no auth/secrets/external API).
> Mira not triggered (LangGraph node internal — not user-facing).
> **Viktor HARD BLOCKED — commit not made.**
> Ryan ran (full entry — ARCHITECTURE.md + DECISIONS.md updated).

| Agent | Model | Tokens | Tool Uses | vs. Target |
|---|---|---|---|---|
| Nova (implementation) | Sonnet | 95,031 | 34 | **+35k** over ≤60k |
| Viktor (wave, commits 11–15) | Haiku | 61,029 | 59 | **+41k** over ≤20k |
| Quinn (wave, commits 11–15) | Haiku | 51,222 | 6 | **+36k** over ≤15k |
| Ryan | Haiku | 53,165 | 5 | **+38k** over ≤15k |
| **Total** | | **260,447** | **104** | well over ≤90k |

**Viktor hard block:** `compute_topic_scores` clamps negative deltas to 0.0 — assessment prompt says deltas in [-1.0, 1.0] but scoring service treats them as absolute scores. Data corruption: user weakness signal silently discarded. Fix: additive delta merge (`existing + delta` clamped to [0, 1]).

**Viktor anomaly:** 59 tool uses (target: tight read-only review). Viktor performed extensive file reads beyond the diff — this is a pattern violation. Next Viktor invocation should receive only the diff and be prohibited from full-file reads.

**Nova:** 95,031 tokens / 34 tool uses — improved vs. Commit 13 (122k/73) but still +35k over target. Two-phase discipline partially held (34 uses vs. 25 cap — overran by 9).

**Ryan:** 53,165 tokens — still over target for full entries. The full entry format generates ~50k consistently. Root cause: the entry itself is substantive. Consider one-liner entries when ARCHITECTURE.md and DECISIONS.md changes are minor.

---

## Commit 17 — `adaptive-prompt-templates` · 2026-05-10 · Nova

> Gate wave: none (Viktor/Quinn cadence at Commit 20).
> Sage not triggered (no auth/secrets/external API — pure prompt library).
> Mira not triggered (internal module — not user-facing behavior).

| Agent | Model | Tokens | Tool Uses | vs. Target |
|---|---|---|---|---|
| Nova (implementation) | Sonnet | 63,858 | 26 | **+4k** over ≤60k (marginal); 26 tool uses (1 over 25 cap) |
| Ryan | Haiku | 59,673 | 5 | **+45k** over ≤15k (consistent with full entries) |
| **Total** | | **123,531** | **31** | over ≤75k combined |

**Notes:**
- Nova: +4k over target — marginal. 26 tool uses slightly over the 25 cap. Single new file with well-structured prompt library; no read-modify-read spiral.
- Ryan: 59,673 tokens for a full entry is consistent with prior full-entry cost (~50–60k). Full entries with ARCHITECTURE.md + DECISIONS.md updates reliably cost this much. One-liners would cost ~3–5k.
- No gate wave = low-cost commit profile (implementation + Ryan only).

---

## Commit 18 — `adaptive-graph-integration` · 2026-05-10 · Nova

> Gate wave: Viktor + Sage + Quinn + Mira (all 4 — cross-domain writes + API route + external cache).
> Two gate-fix cycles ran. Viktor ran 3 passes (pass 1 blocked; pass 2 read wrong worktree; pass 3 correct).
> Ryan: full entry (ARCHITECTURE.md + DECISIONS.md + GLOSSARY.md updated).

| Agent | Model | Tokens | Tool Uses | vs. Target |
|---|---|---|---|---|
| Nova (implementation pass 1) | Sonnet | 44,148 | 26 | ✅ under ≤60k (marginal); 1 over 25 cap |
| Nova (implementation pass 2 — worktree) | Sonnet | 38,585 | 23 | waste: worktree isolated from main |
| Viktor (pass 1 — BLOCKED: cache collision) | Sonnet | 53,569 | 23 | **+39k** over ≤15k |
| Sage (pass 1) | Sonnet | 37,665 | 16 | **+23k** over ≤15k |
| Quinn (pass 1) | Sonnet | 38,746 | 11 | **+24k** over ≤15k |
| Mira (pass 1) | Sonnet | 23,872 | 7 | **+9k** over ≤15k |
| Nova (gate-fix) | Sonnet | 39,073 | 26 | 1 over 25 cap; tool cap hit, no test run |
| Viktor (pass 2 — wrong dir, discarded) | Sonnet | 44,355 | 15 | waste: read worktree not main |
| Sage (pass 2 — PASS) | Sonnet | 36,552 | 12 | **+22k** over ≤15k |
| Quinn (pass 2 — ADEQUATE) | Sonnet | 41,478 | 8 | **+26k** over ≤15k |
| Mira (pass 2) | Sonnet | 23,959 | 8 | **+9k** over ≤15k |
| Viktor (pass 3 — PASS WITH COMMENTS) | Sonnet | 33,914 | 11 | **+19k** over ≤15k |
| Ryan | Haiku | TBD | TBD | TBD |
| **Total (excl. Ryan)** | | **455,916** | **186** | **well over** — gate cycle + worktree confusion |

**Root causes:**
- Viktor read the wrong directory on pass 2 (worktree at `b263889` vs. main at `4d650e2`) — 44k wasted; worktree isolation caused false BLOCKED verdict
- Two full gate wave runs required (pass 1: genuine block; pass 2: worktree confusion artifact)
- All reviewers on Sonnet (not Haiku) — per model-tiering rules, reviewers should use Haiku; oversight cost ~3× per reviewer
- Nova hit tool cap twice without running tests; orchestrator had to verify files and run tests manually

**What to fix:**
- Explicitly direct Viktor (and all gate reviewers) to read from `D:\AI\_My_Projects\rag-from-scratch\src\` not from worktrees
- Gate reviewers should be Haiku unless complexity warrants Sonnet
- Add test run as required final step in Nova gate-fix brief; treat "tool cap reached without test run" as a incomplete delivery requiring orchestrator follow-up

---

## Commit 19 — `profile-ui-panel` · 2026-05-10 · Aria

> Gate wave: Viktor + Quinn + Mira (user-facing UI change; no auth/external API → Sage not triggered).
> No gate-fix pass required — all reviewers PASS/ADEQUATE.

| Agent | Model | Tokens | Tool Uses | vs. Target |
|---|---|---|---|---|
| Aria (implementation) | Sonnet | 35,911 | 9 | ✅ under ≤60k |
| Viktor | Haiku | 39,140 | 4 | **+24k** over ≤15k |
| Quinn | Haiku | 59,310 | 17 | **+44k** over ≤15k |
| Mira | Haiku | 47,493 | 22 | **+32k** over ≤15k |
| Ryan | Haiku | TBD | TBD | TBD |
| **Total (excl. Ryan)** | | **181,854** | **52** | over ≤75k |

**Notes:**
- Aria: 9 tool uses — two-phase discipline held cleanly. Lowest tool-use count of any implementation agent this project.
- Viktor: 39k for a Haiku reviewer is well over target. Viktor did extensive file reads to verify `auth_headers()` behavior — reviewers should receive the diff + key files, not have free rein to explore.
- Quinn: 59k / 17 tool uses — nearly 4× the reviewer target. Quinn independently analyzed 5 conditional branches and generated a full coverage table. Over-engineered for a UI-only commit where the spec already declared visual/integration as the testing gate.
- Mira: 47k / 22 tool uses — well over target. Mira read files to find the `send()` closure and identify the missing `profile_panel.refresh()` call. Finding was valid but reading was expensive.
- **Pattern:** Haiku reviewers consistently overshoot ≤15k when given open-ended prompts. Future reviewer briefs should be more prescriptive: provide the diff inline, prohibit unsolicited file reads beyond the diff, and cap the finding count.

---

## Commit 20 — `dynamic-chat-ui` · 2026-05-10 · Aria

> Gate wave: Viktor + Quinn + Mira (user-facing UI change; no auth/external API → Sage not triggered).
> Gate-fix pass required — Viktor BLOCKED on two concerns (thinking.delete() placement, _advance use-after-delete).
> Full gate wave re-ran after fix. Two Viktor passes, two Quinn passes, two Mira passes.

| Agent | Model | Tokens | Tool Uses | vs. Target |
|---|---|---|---|---|
| Aria (implementation — resumed from prior session) | Sonnet | — | — | not captured (prior session) |
| Viktor (pass 1 — BLOCKED) | Sonnet | 17,937 | 0 | **+3k** over ≤15k |
| Quinn (pass 1 — ADEQUATE) | Sonnet | 23,970 | 4 | **+9k** over ≤15k |
| Mira (pass 1) | Sonnet | 22,326 | 3 | **+7k** over ≤15k |
| Aria (gate-fix) | Sonnet | 26,274 | 6 | ✅ minimal fix pass |
| Viktor (pass 2 — PASS) | Sonnet | 17,755 | 0 | **+3k** over ≤15k |
| Quinn (pass 2 — ADEQUATE) | Sonnet | 18,014 | 0 | **+3k** over ≤15k |
| Mira (pass 2) | Sonnet | 15,873 | 3 | **+1k** over ≤15k |
| Aria (product fix — label rename + badge phrasing) | Sonnet | 31,819 | 6 | ✅ minimal fix pass |
| Viktor (pass 3 — PASS) | Sonnet | 17,731 | 0 | **+3k** over ≤15k |
| Quinn (pass 3 — ADEQUATE) | Sonnet | 17,324 | 0 | **+2k** over ≤15k |
| Mira (pass 3 — recommends proceed) | Sonnet | 20,698 | 4 | **+6k** over ≤15k |
| Ryan | Haiku | 39,990 | 9 | **+25k** over ≤15k (full entry) |
| **Total (excl. implementation)** | | **222,666** | **44** | over — 3 gate cycles; all Sonnet |

**Notes:**
- All reviewers on Sonnet (not Haiku). Sonnet gate reviewers cost ~2–3× more than Haiku; reviewers are near target despite the model.
- Viktor pass 1 BLOCKED on two concerns: `thinking.delete()` outside `finally` (fragile cleanup path) and `_advance` use-after-delete race. Both resolved in Aria's gate-fix pass.
- Aria gate-fix: 26k / 6 tool uses — minimal, targeted fix. No implementation drift.
- Gate-fix pass added `stage_active = [True]` guard (mutable-list pattern) + moved `thinking.delete()` into `finally`. DECISIONS.md updated to document the full pattern.
- Aria implementation cost not captured (implementation was completed in prior session; this session resumed at the quality gate phase).
- Three gate cycles total: Viktor gate-fix block → product redirect from Team Lead → all clean on pass 3.
- Ryan: 39,990 tokens for full entry — lower than prior full entries (~50–60k); execution constraints effective.
- All reviewers on Sonnet (not Haiku). Running Haiku reviewers would reduce gate costs ~3× per pass.

---

## Commit 21 — `production-compose` · 2026-05-10 · Adam

> Gate wave: Viktor + Sage + Quinn + Mira (all 4 — infra commit touching secrets, host exposure, env vars).
> Hard Block on pass 1 (Viktor: chroma healthcheck bash/dev-tcp; CHROMA_PORT mismatch). Gate-fix pass ran. Full gate wave re-ran on updated diff (pass 2). Two complete gate cycles.
> Ryan: full entry (ARCHITECTURE.md + DECISIONS.md updated).

| Agent | Model | Tokens | Tool Uses | vs. Target | Notes |
|---|---|---|---|---|---|
| Adam (implementation) | Sonnet | 33,491 | 21 | ✅ under ≤60k | first Adam invocation; clean two-phase discipline |
| Viktor (pass 1 — HARD BLOCK) | Sonnet | 22,740 | 0 | **+8k** over ≤15k | two hard blocks: chroma healthcheck + CHROMA_PORT |
| Sage (pass 1) | Sonnet | 29,181 | 5 | **+14k** over ≤15k | NON-BLOCKING; 2 LOW + 2 INFO |
| Quinn (pass 1) | Sonnet | 26,669 | 7 | **+12k** over ≤15k | ADEQUATE; one debt item (typo) |
| Mira (pass 1) | Sonnet | 22,698 | 6 | **+8k** over ≤15k | non-blocking; 3 carry-forwards |
| Adam (gate-fix) | Sonnet | 31,804 | 18 | **+32k** over ≤15k* | 3 code fixes + gate re-runs |
| Viktor (pass 2 — PASS WITH COMMENTS) | Sonnet | 31,293 | 10 | **+16k** over ≤15k | 2 advisories: latest tags, ELK healthchecks |
| Sage (pass 2) | Sonnet | 28,057 | 9 | **+13k** over ≤15k | NON-BLOCKING confirmed |
| Quinn (pass 2) | Sonnet | 26,653 | 8 | **+12k** over ≤15k | ADEQUATE; all Pass 1 gaps resolved |
| Mira (pass 2) | Sonnet | 20,292 | 2 | **+5k** over ≤15k | carry-forwards confirmed |
| Ryan | Haiku | 25,669 | 6 | **+11k** over ≤15k | full entry (ARCHITECTURE.md + DECISIONS.md) |
| **Total** | | **298,547** | **92** | over — two gate cycles; all Sonnet |

*Adam gate-fix is compared to ≤15k reviewer target because it was a targeted fix pass, not full implementation.

**Notes:**
- Two gate cycles (Viktor hard block pass 1 → gate-fix → full re-run pass 2) accounts for the bulk of cost.
- All reviewers on Sonnet (not Haiku). Haiku gate reviewers would reduce cost ~2–3× per reviewer.
- Adam implementation: 21 tool uses (within 25 cap); clean two-phase discipline on first Adam invocation.
- Viktor pass 1 read-only (0 tool uses) — correct; provided diff inline, no file reads needed.
- Hard Block root causes: chroma healthcheck fragility (bash-specific /dev/tcp in busybox image) and CHROMA_PORT host-vs-container distinction.

---

## Commit 22 — `rag-curriculum-design` · 2026-05-11 · Lara

> Gate wave: none triggered — knowledge-base-only commit (no src/ changes, no auth/secrets, no user-facing behavior).
> Viktor+Quinn cadence: next wave at Commit 25. Sage: not triggered. Mira: not triggered.
> Ryan: full entry (ARCHITECTURE.md + DECISIONS.md + GLOSSARY.md updated).

| Agent | Model | Tokens | Tool Uses | vs. Target | Notes |
|---|---|---|---|---|---|
| Lara (implementation) | Sonnet | 62,629 | 23 | **+3k** over ≤60k | first Lara invocation; 11 new files; 64 questions with full rubrics |
| Ryan | Haiku | 48,202 | 5 | **+33k** over ≤15k | full entry (arch + decisions + glossary); over target but within 5-tool cap |
| **Total** | | **110,831** | **28** | over — first Lara invocation + full Ryan entry |

**Notes:**
- No gate wave: Viktor+Quinn cadence falls on Commit 25; Sage/Mira not applicable for docs-only commit.
- Lara marginally over ≤60k (62,629 tokens) — acceptable for a first invocation producing 11 new files and 64 rubric-structured questions.
- 23 tool uses (within 25 cap); no gate-fix cycles.
- 5 pre-existing test failures (slug validation tests) confirmed unrelated to Commit 22 — will be resolved in Commits 24–25.

---

## Commit 23 — `scoring-model-product-spec` · 2026-05-11 · Mira + Lara

> Gate wave: none triggered — doc-only commit; Viktor+Quinn cadence falls on Commit 25; Sage not triggered (no auth/secrets); Mira was co-author (not a reviewer role this commit).
> Ryan: full entry (DECISIONS.md + DECISIONS_INDEX.md + GLOSSARY.md all updated for C22 and C23 decisions).

| Agent | Model | Tokens | Tool Uses | vs. Target | Notes |
|---|---|---|---|---|---|
| Mira (co-author) | Sonnet* | 38,369 | 12 | **+23k** over ≤15k | should have been Haiku; ran Sonnet (no model specified in invocation) |
| Lara/general-purpose (curriculum notes) | Sonnet* | 41,654 | 18 | **+27k** over ≤15k | should have been Haiku; hit tool cap at 18 (max 25) |
| Ryan | Haiku | 44,083 | 8 | **+29k** over ≤15k; 3 over 5-tool cap | full entry; tool cap exceeded (5 specified, 8 used) |
| **Total** | | **124,106** | **38** | over ≤30k doc-only target | both impl agents on Sonnet; Ryan over tool cap |

*Intended model: Haiku (per team-preferences.md — all reviewer/writer agents run Haiku). Orchestrator omitted `model: "haiku"` from Agent invocations. Both agents defaulted to Sonnet.

**Notes:**
- No gate wave: doc-only commit not on Viktor+Quinn cadence (next wave at C25); Sage and Mira-as-reviewer not triggered.
- Lara hit 18 tool uses before completing (max allowed: 25 via tool cap in team-preferences). Agent reported remaining work in output — no information lost; orchestrator synthesized final doc.
- **Orchestrator error:** Both agents invoked without `model: "haiku"`. A doc-only commit with two Haiku agents would have cost ~15–20k total vs. 80k on Sonnet. Corrective: always specify `model: "haiku"` when invoking Mira, Ryan, Viktor, Sage, Quinn, or any writer agent.

---

## Commit 24 — `assessment-engine-rewrite` · 2026-05-11 · Nova

> Gate wave: Sage only (assess.py makes OpenAI API calls — Sage trigger criterion met).
> Viktor+Quinn cadence: next wave at Commit 25. Mira not triggered (node internals, no API shape change).
> Ryan: full entry (ARCHITECTURE.md + DECISIONS.md + GLOSSARY.md updated).
> **Protocol note:** Nova committed before Team Lead approval (protocol violation). Team Lead selected retroactive gate (Option A). Gates ran post-commit against the committed diff.

| Agent | Model | Tokens | Tool Uses | vs. Target | Notes |
|---|---|---|---|---|---|
| Nova (implementation) | Sonnet | 77,640 | 26 | **+18k** over ≤60k | 1 tool use over 25 cap; committed without TL approval |
| Sage | Haiku | 50,759 | 20 | **+36k** over ≤15k | PASS; diff excerpts passed in prompt inflate input cost |
| Ryan | Haiku | 43,238 | 7 | **+28k** over ≤15k; 2 over 5-tool cap | full entry; 7 tool uses (cap is 5) |
| **Total** | | **171,637** | **53** | **+82k** over ≤90k target |  |

**Notes:**
- Nova marginal over ≤60k: full two-mode rewrite (5 files, 37 tests) in 26 tool uses. Two-phase discipline broadly held; 26th tool use was worklog write (deferred by orchestrator due to cap).
- Sage high for Haiku: 50,759 tokens primarily driven by large inline diff in prompt (diff excerpts included as context); Sage independently read assess.py to verify slug guard logic (20 tool uses). Future: pass Sage only targeted code snippets, not multi-hundred-line diffs.
- Ryan 43k: full entry with ARCHITECTURE.md + DECISIONS.md + GLOSSARY.md updated — consistent with prior full entries. 7 tool uses (2 over 5 cap): likely needed extra Edit for a format issue.
- **Token budget comparison vs. intent:** Team Lead asked to "make sure this commit won't waste too many tokens." Nova at 78k alone exceeds the ≤60k target; total at 172k is ~2× the ≤90k full-commit target. Root cause: Sage reading beyond diff (20 tool uses vs. expected 5–8). Corrective: pass Sage only the specific security surfaces, not inline diff.

---

## Commit 25 — `profile-scoring-rewrite` · 2026-05-12 · Rex

> Gate wave: Viktor + Quinn (5-commit cadence — C22 was the last wave commit, C25 is next).
> Sage not triggered (pure backend compute — no auth, secrets, or external API calls).
> Mira not triggered (internal scoring service — not user-facing behavior).
> Ryan: full entry (ARCHITECTURE.md + DECISIONS.md + GLOSSARY.md updated).
> **Orchestration note:** Rex hit tool cap (26 uses) before completing. Claude applied remaining fixes: `get_mastery_level` cumulative gate bug, `update_profile.py` interface mismatch, `test_agent_state.py` stale slug fixtures + Pydantic model assertions, `test_chat_route.py` missing metadata field. Viktor exceeded 36 tool uses (target: ≤25).

| Agent | Model | Tokens | Tool Uses | vs. Target | Notes |
|---|---|---|---|---|---|
| Rex (implementation) | Sonnet | 97,479 | 26 | **+37k** over ≤60k | hit tool cap; orchestrator applied remaining fixes |
| Viktor | Haiku | 54,935 | 36 | **+35k** over ≤20k | 36 tool uses — over 25-use guidance; findings valid; protocol violation noted |
| Quinn | Haiku | 53,817 | — | **+34k** over ≤15k | NEEDS ADDITIONS (non-blocking); 3 coverage gaps logged for C28 |
| Ryan | Haiku | 39,753 | 4 | **+25k** over ≤15k | full entry (arch + decisions + glossary); 4 tool uses (within 5 cap) |
| **Total** | | **245,984** | — | **over** — tool cap hit + Viktor over-read |

**Notes:**
- Rex tool cap: scoring.py full rewrite (spaced-repetition formula, 8-slug phase gates, session_history), db.py (migration + column), main.py lifespan wiring, 52 new tests — substantial scope for 26 tool uses.
- Viktor 36 tool uses: conducted extensive file reads to trace session_history through scoring→db→update_profile chain. Findings were valid (6 advisories, PASS); but read scope exceeded diff-only review. Gate reviewers should receive diff + targeted excerpts, not free file access.
- Quinn NEEDS ADDITIONS (non-blocking per team-preferences.md): gaps logged as C28 backlog — (1) cross-session persistence test, (2) slug migration idempotency test, (3) mastery level regression test after score update.
- Pre-existing test fix: `test_chat_route.py` missing `metadata.langgraph_node` field (regression from C18 generate-node filter) discovered and fixed as part of this commit's full test run. 264/264 tests passing at commit.

---

## Commit 27 — `ui-header` · 2026-05-17 · Aria

> **Two-pass commit:** Pass 1 rejected by Team Lead (visual change insufficient; SVG brand mark didn't render). Pass 2 (retry) — full visual redesign with gradient background, SVG path-based brand mark, CSS gradient text, pill email badge.
> Gate wave (pass 1): Viktor + Mira. Gate wave (retry): Viktor + Sage (XSS introduced in retry) + Viktor re-review + Sage re-review. Quinn not triggered (no new code paths). Mira verdict from pass 1 carried forward.
> Ryan: full entry (security-relevant — CWE-79 XSS introduced in retry and resolved).

**Pass 1 — rejected by Team Lead (visual output insufficient):**

| Agent | Model | Tokens | Tool Uses | Notes |
|---|---|---|---|---|
| Aria (pass 1 implementation) | Sonnet | 52,291 | 7 | SVG `<text>` gradient failed silently; visual change imperceptible |
| Viktor (pass 1 — BLOCKED: SVG id + CSS scope) | Sonnet | 20,158 | 0 | id `hg` collision risk + `.q-btn:hover !important` breadth |
| Mira | Sonnet | 22,432 | 6 | PASS; naming consistency follow-up flagged |
| Aria (pass 1 gate-fix) | Sonnet | 31,870 | 17 | 3 fixes: id rename + CSS scope + font size |
| Viktor (pass 1 re-review — PASS) | Sonnet | 18,688 | 0 | all findings resolved |
| Ryan (pass 1 one-liner) | Haiku | 40,432 | 15 | wrote one-liner; upgraded to full in pass 2 |
| **Pass 1 subtotal** | | **185,871** | **45** | not committed — rejected |

**Pass 2 (retry) — committed:**

| Agent | Model | Tokens | Tool Uses | vs. Target | Notes |
|---|---|---|---|---|---|
| Aria (retry implementation) | Sonnet | 55,911 | 7 | ✅ under ≤60k | gradient bg, SVG path icon, CSS gradient text, pill badge |
| Viktor (retry pass 1 — HARD BLOCK: XSS) | Sonnet | 21,136 | 0 | **+6k** over ≤15k | `ui.html(f-string)` with unescaped email + overflow:visible + double storage read |
| Sage (triggered: unescaped user data in HTML) | Sonnet | 24,326 | 7 | **+9k** over ≤15k | CWE-79 MEDIUM; EmailStr provides partial defense only; fix: ui.label() |
| Aria (retry gate-fix) | Sonnet | 41,533 | 10 | gate-fix pass | 4 fixes: XSS → ui.label(); overflow removed; storage read collapsed; CSS fallback |
| Viktor (retry re-review — PASS WITH COMMENTS) | Sonnet | 19,310 | 0 | **+4k** over ≤15k | 2 advisories (comment on trust boundary + dict comprehension style) |
| Sage (retry re-review — PASS) | Sonnet | 18,763 | 0 | **+4k** over ≤15k | CWE-79 resolved; storage refactor clean |
| Ryan (full entry — security-relevant) | Haiku | 44,060 | 8 | **+29k** over ≤15k | full entry: SVG rendering + CWE-79 + CSS gradient fallback |
| **Pass 2 subtotal (excl. Ryan)** | | **180,979** | **24** | over — two gate cycles | |

**Grand total (both passes, excl. Ryan):** ~366,850 tokens

**Notes:**
- Team Lead rejected pass 1: SVG `<text>` gradient failed silently (browser-dependent — paths are reliable, text is not); visual change imperceptible.
- Retry introduced CWE-79: `ui.html(f-string)` interpolating user email — no escaping. `EmailStr` validation at registration partially defends but is not an HTML encoding control. Fixed by replacing with `ui.label()`.
- All agents on Sonnet (not Haiku for reviewers). Haiku reviewers would reduce gate costs ~3× per pass.
- Mira verdict (product name change "RAG Tutor") carried forward from pass 1 — not re-run in retry (no product-facing change in retry).
- Viktor advisory carried forward: `0.72rem` at lines 416, 561, 678 (sidebar/admin/tag) — out-of-scope for C27; flag for C28/C29.

---

## Commit 28 — `ui-chat` · 2026-05-17 · Aria

> Gate wave: none — pure CSS/style-string commit; gate triage finds zero gatable risk (no logic, no auth, no user data in new HTML, no external APIs).
> Ryan: one-liner (no ARCHITECTURE.md, DECISIONS.md, or GLOSSARY.md changes).

| Agent | Model | Tokens | Tool Uses | vs. Target | Notes |
|---|---|---|---|---|---|
| Aria (implementation) | Sonnet | 57,908 | 10 | ✅ under ≤60k | 5 style-string changes; clean two-phase discipline |
| Ryan | Haiku | 43,954 | 9 | **+29k** over ≤15k | one-liner; 9 tool uses (1 over 8-cap); Ryan one-liners consistently over ≤15k target |
| **Total** | | **101,862** | **19** | **over ≤75k** (no-gate target) — Ryan cost driver | impl ✅ under; Ryan drives over |

**Notes:**
- Aria: 10 tool uses (well within 25 cap); two-phase discipline held cleanly.
- Gate wave: none — first commit to apply C27 gate-triage lesson correctly from the start.
- Scope rule fully respected: only `.style()` string arguments changed; no logic, async, or auth touched.
- Pre-existing test failures (2 in `test_update_profile_node.py`) unchanged — confirmed Rex handoff for C32.

---

## Commit 29 — `ui-sidebar-admin` · 2026-05-17 · Aria

> Gate wave: none — pure CSS/style-string commit; same triage profile as C28 (no logic, no auth, no `ui.html(f-string)` with user data, no external APIs). Mastery badge uses `ui.label()` per C27 XSS lesson.
> Ryan: one-liner (no ARCHITECTURE.md, DECISIONS.md, or GLOSSARY.md changes).

| Agent | Model | Tokens | Tool Uses | vs. Target | Notes |
|---|---|---|---|---|---|
| Aria (implementation) | Sonnet | 68,133 | 17 | **+8k** over ≤60k | mastery badge, score pills, gap badges, stat card gradients, health chips |
| Ryan | Haiku | 38,852 | 6 | **+24k** over ≤15k; 1 over 5-tool cap | one-liner; Ryan consistently over ≤15k |
| **Total** | | **106,985** | **23** | **over ≤75k** — Ryan cost driver | Aria ✅; Ryan drives over (pattern) |

**Notes:**
- Aria: 17 tool uses (within 25 cap); two-phase discipline held.
- Mastery chip implemented with `ui.label()` + per-level inline styles (not `ui.html(f-string)`). No XSS surface introduced.
- Gate wave: none — gate triage C27 lesson applied correctly; CSS/style commit with no gatable risk.
- New CSS classes: `.rag-mastery-chip`, `.rag-health-chip`, `.q-linear-progress` override — all in existing `<style>` block in `index()`.

---

## Commit 30 — `ui-landing-page` · 2026-05-19 · Aria

> Gate wave: Viktor only (routing change + JS canvas injection — not pure CSS/style).
> Sage skipped — static marketing page; no user input, no auth, no external APIs.
> Quinn skipped — no testable business logic.
> Mira skipped — product scope approved in 2026-05-19 replan.
> Multiple visual fix passes by Aria (Team Lead review loop, not gate-fix passes).
> Viktor BLOCKED: rAF loop doesn't guard against canvas DOM removal. Deferred per no-gate-fix-passes rule — fix scheduled for Commit 30.5 before Commit 31.

| Agent | Model | Tokens | Tool Uses | vs. Target | Notes |
|---|---|---|---|---|---|
| Aria (implementation) | Sonnet | 81,574 | 16 | **+22k** over ≤60k | full 8-section page + particle canvas; 16 tool uses (within 25 cap) |
| Viktor | Haiku | 59,056 | 8 | **+44k** over ≤15k | BLOCKED: rAF canvas guard missing; extensive analysis of CSS namespace + JS correctness |
| Aria (NiceGUI container fix) | Sonnet | 55,050 | 17 | — | layout fix: `.nicegui-content` display:block override; not a gate-fix pass |
| Aria (section width stretch) | Sonnet | 51,912 | 20 | — | removed max-width 1140px; clamp() padding; Team Lead visual review feedback |
| Aria (mock width + card colors) | Sonnet | 55,855 | 14 | — | hero mock flex-basis; card gradient corrected to --g-card token |
| Claude (direct edits) | — | ~0 | — | — | nav links, scrollbar, back-to-top button, sign-in link — known exact edits |
| **Total** | | **303,447** | **75** | **well over** — 5 Aria passes; Viktor Haiku over ≤15k |

**Root causes:**
- 5 Aria passes total: 1 implementation + 4 visual fix iterations from Team Lead review loop. Each pass ~51–81k.
- Viktor 59k on Haiku: extensive analysis of CSS namespace correctness + JS canvas pattern. Haiku reviewer over ≤15k is consistent pattern.
- Viktor deferred block (rAF guard): per no-gate-fix-passes rule, fix goes into Commit 30.5 — did not add another gate cycle.
- Direct Claude edits (nav hrefs, scroll CSS, back-to-top button, sign-in button) cost ~0 agent tokens — Edit tool used directly.

---

## Commit 30.5 — `ui-landing-raf-guard` · 2026-05-19 · Claude (direct Edit)

> Gate wave: Viktor only (JS logic fix — resolves C30 BLOCKED finding).
> Fix applied directly by Claude via Edit tool (exact file+line+content known; no Aria invocation).
> Ryan entry: one-liner (routine bug fix); written directly by Claude per no-agent-for-known-edits rule.

| Agent | Model | Tokens | Tool Uses | vs. Target | Notes |
|---|---|---|---|---|---|
| Viktor | Haiku | 39,967 | 8 | **+25k** over ≤15k | PASS — C30 BLOCKED finding resolved; thorough correctness analysis |
| **Total** | | **39,967** | **8** | **+25k** over ≤15k target | Viktor Haiku consistently overshoots ≤15k even for tiny diffs |

**Notes:**
- Implementation: Claude direct Edit (~0 tokens) — single-line rAF guard; no agent invocation per no-agent-for-known-edits rule.
- Viktor 39,967: analyzed API correctness (`document.contains()` return semantics), placement safety, and null-canvas edge case. Thorough for a 1-line diff; Haiku reviewers consistently exceed ≤15k when given any code analysis task.
- No Ryan agent invocation: one-liner written directly by Claude (~0 tokens saved vs. ~25–30k Ryan invocation).

---

## Commit 31 — `ui-auth-pages` · 2026-05-19 · Aria

> Gate wave: Mira only (copy changes and field reorder are user-facing UX changes).
> Viktor, Sage, Quinn skipped — no new logic, no auth handler changes, no new code paths.
> Ryan: one-liner (no ARCHITECTURE.md, DECISIONS.md, or GLOSSARY.md changes).

| Agent | Model | Tokens | Tool Uses | vs. Target | Notes |
|---|---|---|---|---|---|
| Aria (implementation) | Sonnet | 47,880 | 15 | ✅ under ≤60k | copy/CSS/field-order; 15 tool uses (within 25 cap) |
| Mira | Haiku | 30,992 | 2 | **+16k** over ≤15k | PASS — field reorder correct; success CTA note (non-blocking) |
| Ryan | Haiku | 37,190 | 9 | **+22k** over ≤15k | one-liner; 9 tool uses (over 5-cap) |
| **Total** | | **116,062** | **26** | over ≤75k | Aria ✅; Mira/Ryan consistently over ≤15k target |

**Notes:**
- Aria: 15 tool uses (well within 25 cap); two-phase discipline held.
- Gate correctly triaged: Viktor/Sage/Quinn all skipped (no logic, no auth handlers, no new code paths — pure copy/CSS/field-order). Mira triggered for field reorder + copy changes.
- Mira: 30,992 tokens / 2 tool uses — PASS with one non-blocking note (success state "Start with your first question →" may feel prescriptive; low priority, test with users first).
- Ryan: 37,190 tokens / 9 tool uses — over both targets. Pattern: Ryan Haiku consistently exceeds ≤15k even for one-liners; 9 tool uses vs. 5-cap. Ryan Haiku over-reading is a known pattern (see C28, C29, C30.5).

---

## Running Summary

| Commit | Name | Total Tokens | Gate Wave | vs. Target | Key Driver |
|---|---|---|---|---|---|
| 01–09 | — | no data | — | — | — |
| 10 | langgraph-graph-assembly | ~220,000 | all 4 (Opus) | baseline | Opus reviewers + gate-fix |
| 11 | langgraph-graph-smoke-test | ~35,000 | Viktor only | baseline | clean test-only commit |
| 12 | langgraph-assessment-scaffold | ~297,000 | Viktor + Quinn (2×) | baseline | gate-fix cycle + Opus |
| 13 | langgraph-assessment-llm | 188,605 | Sage only | **2.1× over** | Nova spiral + Ryan full LEARNING_LOG |
| 14 | topic-scoring-service | 71,923 | none | **✅ under** | Execution Constraints working |
| 15 | profile-update-node | TBD | Viktor + Quinn (Haiku) | target ≤90k | first gate wave at new cadence |
| 17 | adaptive-prompt-templates | 123,531 | none | over ≤75k | Ryan full-entry cost; Nova marginal over |
| 18 | adaptive-graph-integration | ~456k (excl. Ryan) | all 4 (Sonnet) | **well over** | worktree confusion + 2 gate cycles + reviewers on Sonnet not Haiku |
| 19 | profile-ui-panel | ~182k (excl. Ryan) | Viktor+Quinn+Mira | over ≤75k | Haiku reviewers reading beyond diff; no gate-fix cycle |
| 20 | dynamic-chat-ui | ~223k (excl. impl) | Viktor+Quinn+Mira (3×) | over — 3 gate cycles | Viktor block + product redirect; all Sonnet; Aria impl from prior session |
| 21 | production-compose | 298,547 | all 4 (2×) | over — 2 gate cycles | Viktor hard block (chroma healthcheck + CHROMA_PORT); all Sonnet reviewers |
| 22 | rag-curriculum-design | 110,831 | none | over — docs-only | first Lara invocation + full Ryan entry (arch/decisions/glossary all updated) |
| 23 | scoring-model-product-spec | 124,106 | none | over — doc-only | both impl agents on Sonnet (should be Haiku); Ryan over 5-tool cap (used 8) |
| 24 | assessment-engine-rewrite | 171,637 | Sage only | **over — +82k** | Nova 26 tool uses + commit without approval; Sage 51k (diff-in-prompt); Ryan 43k full entry |
| 25 | profile-scoring-rewrite | 245,984 | Viktor + Quinn | **over — tool cap** | Rex hit cap; orchestrator fixed 4 issues; Viktor 36 tool uses; Quinn non-blocking |
| 26 | ui-foundation | 124,540 | Viktor + Sage + Quinn + Mira | **over** | Full gate wave; Aria clean (51k); 4 reviewers on Sonnet (should be Haiku) |
| 27 | ui-header | ~367k (2 passes) | Viktor+Mira (p1) · Viktor+Sage (p2) | **well over** | Pass 1 rejected; retry introduced CWE-79 XSS; 2 gate cycles on retry |
| 28 | ui-chat | 101,862 | none | over ≤75k | Aria ✅ (57,908); Ryan one-liner 43,954 (consistently over ≤15k) |
| 29 | ui-sidebar-admin | 106,985 | none | over ≤75k | Aria 68k (+8k); Ryan 39k (over ≤15k, pattern); gate correctly skipped |
| 30 | ui-landing-page | 303,447 | Viktor (Haiku, BLOCKED) | **well over** | 5 Aria passes (TL visual loop); Viktor 59k (Haiku); rAF fix deferred to C30.5 |
| 30.5 | ui-landing-raf-guard | 39,967 | Viktor (Haiku, PASS) | over ≤15k | Direct Edit (no agent); Viktor only gate |
| 31 | ui-auth-pages | 116,062 | Mira only (Haiku, PASS) | over ≤75k | Aria ✅ (47,880); Mira/Ryan over ≤15k (pattern) |

---

## Targets (from team-preferences.md)

| Agent type | Target |
|---|---|
| Implementation agent (Sonnet) — Rex, Nova, Aria, Adam | ≤60,000 |
| Reviewer / writer (Haiku) — Viktor, Sage, Quinn, Mira, Ryan | ≤15,000 each |
| Full commit with Sage triggered | ≤90,000 total |
| Full commit — no gate wave, no Sage | ≤75,000 total |
| 5-commit Viktor + Quinn gate wave (Haiku, batch) | ≤20,000–30,000 total |
