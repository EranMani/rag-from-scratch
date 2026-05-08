# Learning Log

> Written for the Team Lead. Plain language. No jargon without explanation.
> Every commit gets at minimum a one-liner. Significant commits get a full entry
> with code snippet, reasoning, and design pattern analysis.
>
> **Use this file to:** understand what was built, why it was built that way,
> which design patterns and architectural principles were applied, and how to
> explain all of it to a reviewer or recruiter.

---

## Entry Format Reference

### Full Entry
*Used for: architectural changes, non-obvious decisions, security-relevant changes,
design pattern applications (atomicity, single responsibility, dependency injection,
idempotency, separation of concerns, etc.) — anything that also touches ARCHITECTURE.md
or DECISIONS.md.*

---

**Commit [N] — [commit-name]** · [date] · [agent] · `[architectural | new feature | optimization | fix]`

> **In one sentence:** [One recruiter-ready line — what changed and why it matters.]

**What happened and why:**
[2–3 paragraphs in plain English. What the agent built, what problem it solves,
why this approach was chosen over the alternatives. Written so you can explain it
to someone who didn't read the code.]

**Design pattern / architectural principle:**
[Name the pattern(s) applied — e.g. atomicity, single responsibility, dependency injection,
idempotency, separation of concerns, guard clause, middleware chain, etc.
Then explain in one or two plain sentences what that pattern means in this specific context
and why it matters here. If no named pattern applies, write "N/A".]

**Reasoning & discovery:**
[How did the agent find this solution? What was the bug or problem as initially understood?
What guiding questions or observations pointed toward the answer? What was tried and ruled
out along the way? Synthesized from the agent's Approach note in their worklog — written
so you can follow the thought process, not just read the conclusion.]

**The key change:**
```[language]
// path/to/file.py — line N
// Before:
[old code]

// After:
[new code]
```

**Files touched:**
- `path/to/file.py` — [what changed here]
- `path/to/other.py` — [what changed here]

---

### One-liner Entry
*Used for: routine fixes, config updates, test additions, minor refactors —
anything that doesn't introduce a new pattern or decision.*

---

**Commit [N] — [commit-name]** · [date] · [agent] · `[fix | config | test | refactor | docs]`

> **In one sentence:** [One recruiter-ready line.]

---

## Entries

*No entries yet. Entries are added per commit starting from Commit 01.*
