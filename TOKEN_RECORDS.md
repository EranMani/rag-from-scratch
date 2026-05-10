# TOKEN_RECORDS.md — Per-Commit Token Usage
> One table per commit. Captured at commit time — not reconstructed after the fact.
> Goal: track whether token reduction methods are working while quality holds.
> Quality signal: tests pass · no Viktor hard blocks · learning log entry written.
>
> Companion file: TOKEN_OPTIMIZATION.md — the methods behind the numbers.
> Last updated: 2026-05-10 (Commit 14)

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

---

## Targets (from team-preferences.md)

| Agent type | Target |
|---|---|
| Implementation agent (Sonnet) — Rex, Nova, Aria, Adam | ≤60,000 |
| Reviewer / writer (Haiku) — Viktor, Sage, Quinn, Mira, Ryan | ≤15,000 each |
| Full commit with Sage triggered | ≤90,000 total |
| Full commit — no gate wave, no Sage | ≤75,000 total |
| 5-commit Viktor + Quinn gate wave (Haiku, batch) | ≤20,000–30,000 total |
