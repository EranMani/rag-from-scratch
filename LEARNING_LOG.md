# Learning Log

> Written for the Team Lead. Plain language. No jargon without explanation.
> Every commit gets at minimum a one-liner. Significant commits get a full entry
> with code snippet and reasoning.
>
> **Use this file to:** understand what was built, why it was built that way,
> and explain it to a reviewer or recruiter.

---

## Entry Format Reference

### Full Entry
*Used for: architectural changes, non-obvious decisions, security-relevant changes,
new patterns — anything that also touches ARCHITECTURE.md or DECISIONS.md.*

---

**Commit [N] — [commit-name]** · [date] · [agent] · `[architectural | new feature | optimization | fix]`

> **In one sentence:** [One recruiter-ready line — what changed and why it matters.]

**What happened and why:**
[2–3 paragraphs in plain English. What the agent built, what problem it solves,
why this approach was chosen over the alternatives. Written so you can explain it
to someone who didn't read the code.]

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
