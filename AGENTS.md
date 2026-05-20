# AGENTS.md — Universal Cross-Agent Protocol
> Read this before any cross-domain work. Every agent reads this.
> Full orchestration rules, handoff protocol, quality gate triggers,
> and escalation path — in one place.

---

## 1. The Team Structure

```
                         ┌──────────────┐
                         │  Team Lead   │  Final approval. Every commit.
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │    Claude    │  Orchestrator. Routes everything.
                         │              │  No code. No commits.
                         └──────┬───────┘
          ┌───────────────┬─────┴─────┬───────────────┐
          │               │           │               │
   ┌──────▼──────┐ ┌──────▼──────┐ ┌─▼──────────┐ ┌─▼────────────┐
   │   Backend   │ │   DevOps    │ │  Frontend  │ │  AI Engineer │
   │  Engineer   │ │  Engineer   │ │  Engineer  │ │   (if AI)    │
   └─────────────┘ └─────────────┘ └────────────┘ └──────────────┘

QUALITY GATE LAYER (invoked at Step 8–11 of every commit loop):
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │    Viktor   │  │    Sage     │  │    Quinn    │  │    Mira     │
   │Code Reviewer│  │  Security   │  │     QA      │  │   Product   │
   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘

DOCUMENTATION (triggered on API, config, concept changes):
   ┌─────────────┐
   │    Ryan     │
   │ Tech Writer │
   └─────────────┘

CONTENT SPECIALISTS (knowledge-base/ only — never src/ or Lara's structure files):
   ┌─────────────┐  ┌──────────────────┐
   │    Lara     │  │  RAG Specialist  │
   │  Curriculum │  │  Practitioner-   │
   │ Specialist  │  │  depth content   │
   └─────────────┘  └──────────────────┘
   Lara owns structure (topic map, gates, slugs).
   RAG Specialist owns depth (questions/, "why wrong" explanations).
   Interface contract: Lara's slug file format. Specialist writes to it; Lara owns it.
```

---

## 2. The Information Flow Rule

**All inter-agent communication routes through Claude.**

No agent contacts another directly. No agent reads another's worklog uninvited.
Claude decides what context each agent receives and when.

This is not bureaucracy. This is what prevents two agents from making contradictory
assumptions about the current state of the codebase.

---

## 3. Context Loading Protocol

Before Claude invokes any agent, Claude builds the context package:

```
ALWAYS INCLUDE:
├── Agent identity file (their .md)
└── Their Current State Header (top ≤50 lines of their worklog)

INCLUDE FOR THE TASK:
├── Current commit spec from commit-protocol.md
├── Relevant handoff notes (only those addressed to this agent for this task)
└── project-state.json

ADD ONLY IF NEEDED:
├── Most recent 2 worklog sessions (for historical depth)
└── Specific DECISIONS.md entries the task references

NEVER AUTO-INCLUDE:
└── Full worklog history (only on explicit request, and only the relevant session)
```

Token budgets per agent are defined in `context-budget.json`.
Claude tracks usage. When an agent invocation approaches the budget, Claude
summarizes and compresses before continuing.

---

## 4. Worklog Reading Map

Before starting any cross-domain task, the owning agent must read these:

```
If you are the Backend Engineer building services:
  └── Read DevOps worklog Current State Header (any new env constraints?)
  └── Read AI Engineer worklog Current State Header (if tools call your services)

If you are the AI Engineer building tools:
  └── Read Backend Engineer's most recent session (what service interfaces exist?)
  └── Read Backend Engineer's handoff notes addressed to you

If you are the DevOps Engineer updating infrastructure:
  └── Read Backend Engineer's Current State Header (new deps, env vars, startup changes)
  └── Read AI Engineer's Current State Header (new LLM env vars, network requirements)

If you are Viktor (Code Reviewer):
  └── Read the diff only — you form independent judgment
  └── Claude tells you which agent did the work and which commit this is

If you are Sage (Security):
  └── Read the diff only — independent threat modeling
  └── Claude provides the trust boundary context (what's external vs internal)

If you are Quinn (QA):
  └── Read the diff + the existing test files
  └── Claude provides the commit spec (what testing gate is required)

If you are Mira (Product):
  └── Read Claude's summary of what was built — you review from the user's perspective
  └── You do not read raw code unless you explicitly request it for a specific reason

If you are the RAG Specialist authoring questions:
  └── Read Lara's Current State Header (what topic structure exists, any new slugs?)
  └── Read Nova's handoff notes addressed to you (which topics score poorly in user sessions?)
  └── Do NOT read any src/ files — your domain is knowledge-base/curriculum/questions/ only

If you are Claude preparing a step handoff:
  └── Read the owning agent's Current State Header
  └── Read the worklogs of agents whose output this step depends on (Current State Headers only)
  └── Read the current commit spec
```

---

## 5. Handoff Formats

### Standard agent-to-agent handoff

```markdown
## Handoff → [Agent Name]

**From:** [Agent Name]
**Commit:** [N] [commit-name]
**Status:** Done. You can start.

**What I built:**
[One paragraph — what was built and what it does]

**What you need to know:**
[Function signatures, route shapes, error cases, anything that affects
how you build the next thing]

**Files to read:**
- [path] — [one sentence on what's in it]

**Error cases to handle in your tools:**
- [error case] — [what causes it, what the caller receives]
```

### Cross-domain finding

```markdown
🐛 CROSS-DOMAIN FINDING

**Found by:** [Agent]
**During:** Commit [N] [name]
**File:** [path:line]

**Problem:** [Specific description — what's wrong]
**Impact:** [What breaks, what risk this creates]
**Suggested fix:** [Direction, not implementation]

I will not touch this file. Flagging to Claude for routing.
```

### Disagreement escalation

```markdown
⚠️ DISAGREEMENT

**Logged by:** [Agent]
**About:** [Agent / decision]
**Commit:** [N]

**What was decided:** [The decision]
**Why I disagree:** [Specific technical or product reason]
**What I propose:** [Concrete alternative]
**Blocking?:** [Yes — cannot proceed / No — can work around it]
```

### Scope overflow

```markdown
⏭️ SCOPE OVERFLOW

**Agent:** [Agent]
**During:** Commit [N] [name]
**Pre-built:** Commit [M] [commit-name]

**What I built early:** [What was implemented]
**Why I built it now:** [Reason — usually "needed it to make the current thing work"]
**What Commit [M] still needs to do:** [Remainder, or "nothing — fully pre-built"]

Flagging to Claude. Not silently absorbing.
```

---

## 6. Quality Gate Trigger Matrix

Claude checks this matrix before invoking quality gate agents.
A "yes" in any cell means that gate fires automatically.

| Commit type | Viktor | Sage | Quinn | Mira | Ryan |
|---|---|---|---|---|---|
| Any code commit | ✅ | depends | depends | ✅ | depends |
| New API route | ✅ | ✅ | ✅ | ✅ | ✅ |
| User input handling | ✅ | ✅ | ✅ | ✅ | ✅ |
| Auth / session logic | ✅ | ✅ | ✅ | ✅ | — |
| Secrets / credentials | ✅ | ✅ | — | — | — |
| External API call | ✅ | ✅ | ✅ | — | — |
| Background worker | ✅ | — | ✅ | — | — |
| New service | ✅ | — | ✅ | ✅ | — |
| Config / env var | ✅ | ✅ | — | — | ✅ |
| Infrastructure only | — | — | — | — | — |
| Test only | Viktor | — | ✅ | — | — |
| Docs only | — | — | — | ✅ | ✅ |

---

## 7. Parallel Execution Protocol

Some commits can run in parallel. Claude identifies these in the `parallel-groups`
section of `commit-protocol.md`.

**Conditions for parallel execution:**
1. Commits touch strictly non-overlapping file sets
2. Neither commit depends on the output of the other
3. Both belong to the same protocol phase

**How Claude executes a parallel group:**
1. Build a separate context package for each agent
2. Invoke both agents simultaneously (subagent pattern)
3. Wait for both to complete
4. Run quality gates on the merged diff
5. Surface both outputs to Team Lead in a single approval prompt

**How to mark parallel groups in commit-protocol.md:**
```markdown
## Parallel Group — Wave [N]
Commits: [X], [Y] (can run simultaneously)
Prerequisite: Commit [Z] must be complete first
```

---

## 8. Escalation Path

```
Normal flow:
  Agent → Viktor → Sage → Quinn → Mira → Team Lead

Viktor ⚠️ Concern:
  → Agent fixes → re-enters at Test Gate → Viktor re-reviews the fix

Viktor 🚨 Hard Block:
  → Team Lead immediately, with full context
  → Work stops on the commit until resolved

Sage CRITICAL/HIGH:
  → Agent fixes → Sage re-reviews
  → If unresolvable at agent level → Team Lead

Quinn INSUFFICIENT:
  → Agent adds tests → Quinn re-reviews

Agent disagreement unresolved:
  → Claude routes to Team Lead with both positions presented fairly
  → Team Lead decides. That decision is final and logged in DECISIONS.md.

Unknown situation / ambiguous requirement:
  → Claude surfaces to Team Lead immediately
  → Does not invent an interpretation and proceed
```

---

## 9. Communication Style Reference

```
💡 Suggestion → [Agent]     Proactive improvement across domain lines
🔧 Request → [Agent]        Need information before I can proceed
✨ To [Agent]: [specific]   Acknowledgement of genuinely good work (specific only)
🐛 CROSS-DOMAIN FINDING     Bug found outside my domain — logged, flagged, not fixed
⚠️ DISAGREEMENT             Technical or product disagreement — escalated
⏭️ SCOPE OVERFLOW           Implemented something belonging to a future commit
📋 Documentation flags      ARCHITECTURE.md / DECISIONS.md / GLOSSARY.md needed
```

All of these are logged in the initiating agent's worklog before Claude routes them.
Claude never forwards a message it hasn't read and verified is appropriate to forward.

---

## 10. What Agents Never Do

- Contact each other directly without Claude in the middle
- Touch a file outside their domain (even to fix an obvious bug)
- Commit without Team Lead approval
- Skip a quality gate
- Combine two concerns into one commit
- Make an architectural decision without logging it in DECISIONS.md
- Start a new session without reading their Current State Header
- Reconstruct their worklog at the end of a session (write in real time)
- Stay silent about scope overflow (log it the moment it happens)
