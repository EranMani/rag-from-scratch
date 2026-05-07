# /init — Project Initialization & Commit Protocol Construction

Triggered when: a new project is starting, or an existing project is being onboarded
and `commit-protocol.md` does not yet exist.

This command has four phases:
1. Claude interviews the Team Lead
2. Claude consults each active core agent
3. Claude synthesizes all inputs into a proposed commit index
4. Team Lead approves — files are written

No code is written during /init. No commits are made.
The only output is a finalized `commit-protocol.md` and initialized project files.

---

## PHASE 1 — Team Lead Interview

Claude asks these questions. Do not proceed to Phase 2 until all are answered.
Ask them conversationally — not as a form. One topic at a time if the Team Lead prefers.

---

### 1.1 — What are we building?

Ask:
> "Describe the product in two or three sentences. What does it do, who uses it,
> and what's the one thing that must work at the end of this build?"

The answer to "the one thing that must work" is the north star for the commit sequence.
Every commit that doesn't lead toward that moment is a candidate to cut or defer.

---

### 1.2 — What's the tech stack?

Ask:
> "What's the tech stack? If you're not sure yet, tell me what you know —
> language, framework, database, anything already decided."

If the Team Lead hasn't decided yet:
> "Should we decide now, or should I flag this as an open decision and proceed
> with a stack-agnostic sequence?"

Record every stack decision in `DECISIONS.md` with the stated reason.
Stack decisions made during /init are the foundation — they are not revisited without a `/replan`.

---

### 1.3 — Which agents are active?

Ask:
> "Which of these roles do we need for this project?"

Present the full roster:
```
Core (always active):
  ✓ Claude — orchestrator
  ✓ Backend Engineer — server code, API, data layer
  ✓ DevOps Engineer — containers, CI/CD, environment
  ✓ Product Manager — pre-commit product reviews
  ✓ Viktor — code review (every commit)
  ✓ Sage — security review (triggered automatically)
  ✓ Quinn — coverage review (triggered automatically)

Optional — activate if the project needs it:
  ? Frontend Engineer — UI layer
  ? AI/ML Engineer — LLM agents, ML models
  ? Technical Writer — developer docs, API reference
  ? Data Engineer — data pipelines, analytics
  ? Mobile Engineer — iOS/Android
```

For each activated optional agent, ask:
> "What's [agent]'s name for this project?"

**For each agent that commits code** (Backend, DevOps, Frontend, AI Engineer, Tech Writer — not Viktor, Sage, Quinn, or Mira who only review), ask:
> "What email should [agent] use in commit messages?
> Anything consistent works — real or invented, e.g. `rex@myproject.com`"

These emails serve two purposes:
- `Co-Authored-By: [Name] <[email]>` line in every commit they make
- `hooks/agent-config.json` domain boundary enforcement (written in Phase 5)

Claude's email is always `claude@anthropic.com` — no need to ask.
Viktor, Sage, Quinn, and Mira never commit, so no email is needed for them.

If the Team Lead prefers to skip email setup:
> "No problem — domain enforcement will be inactive until emails are set.
> You can fill them into `hooks/agent-config.json` later to activate it."

---

### 1.4 — What's out of scope for this build?

Ask:
> "What are we explicitly NOT building in this phase?
> Things that might seem natural to include but belong to a future phase."

This is as important as what's in scope.
Every item the Team Lead lists here becomes a scope boundary Claude enforces.
If an agent proposes work that touches an out-of-scope item, Claude flags it immediately.

---

### 1.5 — What are the hard constraints?

Ask:
> "Are there any hard constraints I should know about?
> For example: a deadline, an existing system we can't change, a library we must use,
> a compliance requirement, a team member who's only available part-time."

Constraints shape sequencing. A tight deadline pushes parallelization.
An existing system shapes which commits are archaeology vs. new code.
A compliance requirement activates Sage earlier and more strictly.

---

### 1.6 — Greenfield or existing codebase?

Ask:
> "Is this starting from scratch, or are we building on top of existing code?"

**If existing codebase:**
> "Before I can build the commit protocol, I need to run /archaeology first.
> This surveys the existing code so the commit sequence starts from reality,
> not from assumptions. It takes one session and produces no commits.
> Shall I run /archaeology now?"

If yes → run /archaeology, then return to /init Phase 2 with the archaeology outputs.
The archaeology outputs replace Phase 2 agent questions for the backend and devops domains.

**If greenfield:**
Continue to Phase 2.

---

## PHASE 2 — Agent Consultation

Claude passes the project brief to each active core agent.
Each agent reviews the brief from their domain perspective and answers specific questions.
They are not writing code. They are stress-testing the plan before it's locked in.

Run all agent consultations in parallel — no agent needs to wait for another.

---

### 2.1 — Backend Engineer consultation

**Brief to pass:**
```
Project: [name]
What we're building: [Team Lead's description]
North star: [the one thing that must work]
Tech stack: [stack decisions]
Out of scope: [list]
Constraints: [list]

Your task: Review this project brief from your domain perspective.
Answer the following questions. Be specific — your answers directly shape the commit sequence.
```

**Questions for the Backend Engineer:**
1. What is the correct technical build order for this stack? What cannot be built before what? (e.g. models before services, services before routes)
2. What are the highest-risk technical decisions in this stack that should be validated early — before a lot of code depends on them?
3. Which parts of the backend can be built independently and run in parallel commits?
4. Are there any backend concerns that are typically underestimated for this stack that we should add a dedicated commit for? (e.g. async session management, connection pooling, migration strategy)
5. What is the minimum backend that must exist for the north star moment to be testable end-to-end?

---

### 2.2 — DevOps Engineer consultation

**Brief to pass:** (same project brief as above)

**Questions for the DevOps Engineer:**
1. What infrastructure must exist before the application code can run at all? (e.g. containerization, environment setup, database provisioning)
2. What is the correct order for infrastructure commits — what depends on what?
3. What environment/config work needs to happen upfront that developers typically forget until they're blocked by it?
4. Are there any CI/CD or deployment concerns specific to this stack that deserve their own commit?
5. What is the minimum infrastructure for the north star moment to be testable?

---

### 2.3 — Product Manager consultation

**Brief to pass:** (same project brief as above)

**Questions for the Product Manager:**
1. Is the scope the Team Lead described the right scope to reach the north star moment? What would you cut? What's suspiciously missing?
2. Looking at the proposed build, which step is the highest-stakes moment from a user's perspective — where does the experience either win or lose the user?
3. Are there any product decisions embedded in the tech choices that should be flagged before code is written? (e.g. "this API shape assumes users do X, but they actually do Y")
4. What would make this project feel successful to a user who has never seen the commit protocol?

---

### 2.4 — Frontend Engineer consultation (if active)

**Brief to pass:** (same project brief as above)

**Questions for the Frontend Engineer:**
1. What is the minimum API surface you need to start frontend work? What routes, what response shapes?
2. What assumptions about the API shape, if wrong, would require the most expensive rework later?
3. Are there any frontend concerns that need to be addressed before the backend is complete — e.g. auth flows, file upload handling, real-time requirements?
4. What would you add to the backend commit sequence to make frontend development smoother?

---

### 2.5 — AI/ML Engineer consultation (if active)

**Brief to pass:** (same project brief as above)

**Questions for the AI/ML Engineer:**
1. What does the AI layer depend on from the backend? What must be built before you can start?
2. What's the correct sequencing for the AI components themselves? (e.g. state schema before graph, tools before the agent that uses them)
3. What are the highest-risk technical bets in the AI architecture — things that could fail and invalidate a lot of surrounding work?
4. What is the minimum AI implementation to demonstrate the north star moment?

---

### 2.6 — Viktor structural review (always)

**Brief to pass:** (project brief + preliminary commit list from Phase 2 responses)

**Questions for Viktor:**
> "Review the proposed commit sequence — not the code, the plan.
> Look for structural problems: commits doing too much, wrong dependencies,
> missing steps, scope that belongs in a separate commit."

1. Which commits in this sequence are doing more than one thing? (Candidates to split)
2. Which commits have an implicit dependency that isn't modeled in the sequence?
3. Which commits could run in parallel based on their file domain?
4. Is the granularity right throughout — or are some phases too coarse and others too fine?
5. What is the single biggest sequencing risk in this plan?

---

## PHASE 3 — Claude Synthesizes

Claude reads all agent consultation responses. Then produces the draft commit index.

**Structure:**
- Commits organized into named phases (Foundation, Data, Core Logic, API, Integration, AI, Quality, Hardening)
- Each commit: number, name, assignee, one-sentence rationale, testing gate
- Dependencies made explicit in each commit spec
- Parallel groups identified and labeled
- Estimated session count per phase

**Format for each commit in the draft:**

```
| [N] | [commit-name] | [Agent] | pending |

Rationale: [one sentence — why this comes here and not earlier or later]
Depends on: [commit N, or "none"]
Parallel with: [commit N, or "none"]
North star contribution: [how this gets us closer to the one thing that must work]
```

---

## PHASE 4 — Team Lead Approval

Claude presents the full proposed commit index to the Team Lead:

```
## Proposed Commit Protocol — [Project Name]

North star: [the one thing that must work]
Total commits: [N] across [X] phases
Estimated sessions: [range]
Active agents: [list]

[Full commit table]

[Phase labels and rationale]

[Parallel groups]

Agent inputs that shaped this sequence:
- Backend: [key sequencing decision and why]
- DevOps: [key infrastructure insight]
- Product: [key scope decision]
- [others as applicable]

Viktor's structural flags addressed:
- [what was split, reordered, or parallelized based on Viktor's review]

Questions before I write this to commit-protocol.md:
1. Does the north star moment feel right to you — Commit [N] `[name]`?
2. Is there anything in scope that's missing?
3. Is there anything here that belongs in a future phase?
```

**Do not write any files until the Team Lead says: "Approved — write the protocol."**

If the Team Lead requests changes:
- Revise the draft
- Re-surface for approval
- Do not apply partial approvals

---

## PHASE 5 — Write Project Files

After Team Lead approval:

**1. `commit-protocol.md`** — write the full approved commit index with all specs

**2. `project-state.json`** — initialize with:
```json
{
  "project": "[name]",
  "last_updated": "[today]",
  "status": "active",
  "next_commit": "01",
  "commits_done": [],
  "commits_pending": ["01", "02", ...],
  "open_handoffs": [],
  "blockers": [],
  "rollback_history": [],
  "replan_history": [],
  "archaeology_complete": [true/false],
  "onboarding_type": "greenfield | existing_codebase"
}
```

**3. `team-preferences.md`** — initialize from template.
Ask the Team Lead:
> "Do you want to set any reviewer calibration preferences now,
> or should I use balanced defaults and we'll tune as we go?"

**4. `ARCHITECTURE.md`** — initialize with project name, tech stack decisions, and agent domain map. Leave the component diagrams blank — they fill in as commits land.

**5. `DECISIONS.md`** — initialize with all stack decisions made during the interview, each with the stated reason and today's date.

**6. `GLOSSARY.md`** — initialize with any domain-specific terms that came up during the interview.

**7. Customize agent identity files** — for each active agent:
- Set the agent's name for this project
- Add stack-specific technical standards (e.g. "this project uses FastAPI + SQLAlchemy — Rex enforces async-only database access")
- Add any project-specific non-negotiables the Team Lead mentioned

**8. `hooks/agent-config.json`** — write with real project data collected during the interview.

This file is read at runtime by the pre-commit hook to enforce domain boundaries.
If this file is missing or `"initialized": false`, the hook degrades gracefully
(warns, does not block commits). Writing it correctly here is what activates enforcement.

Populate it from Phase 1.3 — the agent names, emails, and active roles the Team Lead confirmed.
Use this structure, removing any role blocks for agents not active on this project:

```json
{
  "_comment": "Written by /init. Update via /replan if roles change.",
  "project": "[PROJECT_NAME]",
  "initialized": true,
  "agents": {
    "[backend-agent-email]": {
      "name": "[backend-agent-name]",
      "role": "backend",
      "domains": ["src/models/", "src/schemas/", "src/services/", "src/api/routes/", "src/tasks/", "src/core/", "alembic/", "tests/"]
    },
    "[devops-agent-email]": {
      "name": "[devops-agent-name]",
      "role": "devops",
      "domains": [".github/", "Dockerfile", "docker-compose*.yml", "nginx/", "Makefile", ".env.example"]
    },
    "[frontend-agent-email]": {
      "name": "[frontend-agent-name]",
      "role": "frontend",
      "domains": ["src/frontend/", "public/", "components/", "pages/"]
    },
    "[ai-engineer-email]": {
      "name": "[ai-engineer-name]",
      "role": "ai-engineer",
      "domains": ["src/agents/", "src/api/routes/agent.py"]
    },
    "claude@anthropic.com": {
      "name": "Claude",
      "role": "orchestrator",
      "domains": ["CLAUDE.md", "ORCHESTRATION.md", "AGENTS.md", "ARCHITECTURE.md", "DECISIONS.md", "GLOSSARY.md", "commit-protocol.md", "project-state.json", "team-preferences.md", ".claude/commands/", "hooks/"]
    }
  },
  "universal_allowed": ["README.md", ".gitignore", "pyproject.toml", "package.json", ".env.example"]
}
```

**Rules for populating this file:**
- Use the exact commit emails from Phase 1.3 (the emails agents use in `Co-Authored-By:` lines)
- Remove role blocks for any agent not active on this project
- Adjust `"domains"` paths to match the actual project file structure — these are prefix-matched
- Files listed in `"universal_allowed"` can be committed by any agent without a domain warning
- The `"initialized": true` flag is what activates hook enforcement — do not set it until all emails and domains are correct

---

## PHASE 6 — Handoff to Commit Loop

Once all files are written, Claude delivers:

```
✅ /init complete. [Project name] is ready to build.

Commit protocol: [N] commits across [X] phases
First commit: #01 `[name]` — assigned to [Agent]
North star commit: #[N] `[name]` — [one sentence on what it proves works]

Active agents: [list with names]
Team preferences: [balanced defaults / custom — summary of key calibrations]

To begin: I'll invoke [Agent] for Commit 01 — `[name]`.
[One sentence on what Commit 01 builds and why it comes first.]

Shall I proceed?
```

The commit loop starts on Team Lead confirmation.

---

## /init Non-Negotiables

- Never write `commit-protocol.md` without Team Lead approval of the full index.
- Never skip the agent consultation phase — even if the Team Lead has a draft in mind.
  Agents stress-test the plan. The plan is always better after they've reviewed it.
- Never combine /init and Commit 01 into the same session without the Team Lead's
  explicit request. Initialization is a planning session. Building is a building session.
- If the project is an existing codebase, /archaeology runs first. Always.
  Building a commit protocol from assumptions about existing code produces a sequence
  that collides with reality on Commit 02.
