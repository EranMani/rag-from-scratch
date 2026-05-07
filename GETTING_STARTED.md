# Getting Started — Universal Agentic Workflow
*Your step-by-step guide for the first time*

---

## Before You Begin

You need:
- Claude Code installed and running
- A project directory (new project or existing codebase)
- The `UNIVERSAL_WORKFLOW/` folder copied into your project root

That's it. No other setup required.

---

## Step 1 — Copy the Workflow Into Your Project

**Do not copy the `UNIVERSAL_WORKFLOW` folder itself.**
Copy the **contents inside it** directly into your project root.

The `UNIVERSAL_WORKFLOW` folder is just storage for this repo.
Your project never has a folder called `UNIVERSAL_WORKFLOW`.

What your project root should look like after copying:

```
my-project/
├── CLAUDE.md              ← must be here — Claude Code reads this automatically
├── ORCHESTRATION.md
├── AGENTS.md
├── team-preferences.md
├── project-state.json
├── commit-protocol-template.md
├── context-budget.json
├── .claude/
│   ├── settings.json
│   ├── agents/            ← all agent identity files go here
│   └── commands/          ← all slash commands go here
├── hooks/
│   ├── pre_commit_check.py
│   └── post_commit_next_step.py
├── src/                   ← your existing project code
└── README.md
```

The most important file is `CLAUDE.md` at the root.
Claude Code finds it automatically when you open the project.
If it's inside a subfolder, Claude won't find it.

**Quick copy command (Mac/Linux):**
```bash
cp -r path/to/UNIVERSAL_WORKFLOW/. my-project/
```

The trailing `/. ` copies the contents, not the folder itself.

---

## Step 2 — Open Claude Code in Your Project

```bash
cd my-project
claude
```

Claude reads `CLAUDE.md` automatically on startup. It sees no `project-state.json`
and knows this is a new project. It will tell you to run `/init`.

---

## Step 3 — Run `/init`

Type in Claude Code:

```
/init
```

Claude will interview you. Six questions, one at a time:

| Question | What to answer |
|---|---|
| What are we building? | Describe the product in 2–3 sentences. End with: "The one thing that must work is..." |
| What's the tech stack? | Language, framework, database — anything already decided. Say "not sure yet" if you haven't decided. |
| Which agents do we need? | Claude shows the full list. Confirm the core ones, activate optional ones (Frontend, AI Engineer, etc.). **Claude will also ask for a commit email per agent** — use anything consistent, e.g. `rex@myproject.com`. This activates the domain-boundary hook. |
| What's out of scope? | Things that might seem natural to include but belong to a future phase |
| Hard constraints? | Deadline, existing systems you can't change, compliance requirements |
| Greenfield or existing code? | New project from scratch, or building on top of existing code |

---

## Step 4A — If Greenfield (New Project)

After the interview, Claude consults your agents **in parallel**:

- The backend engineer validates the technical build order
- The DevOps engineer maps infrastructure dependencies  
- The product manager challenges scope
- Any optional agents you activated give their input
- Viktor reviews the proposed commit sequence for structural problems

This takes a few minutes. You don't do anything — Claude handles it.

Then Claude shows you the **proposed commit protocol**: every commit planned out,
in order, with phases, owners, and rationale. Review it.

When you're happy: say **"Approved — write the protocol."**

Claude writes all the files and says: *"Ready to start Commit 01. Shall I proceed?"*

Say **yes** and the build begins.

---

## Step 4B — If Existing Codebase

Claude runs `/archaeology` first — a read-only survey of your existing code.
**Nothing is changed. No commits are made.**

Four agents read your codebase in parallel:
- Backend engineer maps what exists, what's partial, and what conventions the code uses
- DevOps engineer maps infrastructure, env vars, CI/CD
- Sage maps the security attack surface
- Viktor does a baseline quality review

Claude then synthesizes everything and shows you:
- What already works (won't be touched)
- What's missing or broken (becomes your commit sequence)
- The existing conventions that all new code must follow
- The proposed commit protocol starting from where the code is *now*

When you're happy: say **"Approved — write the protocol."**

---

## Step 5 — The Build Loop

Every commit follows this flow. You only act twice per commit:

```
1. Claude tells you what's next and asks: "Shall I proceed?"
   → You say yes

2. Claude invokes the right agent — they build and log their work

3. Tests run automatically

4. Viktor, Sage, Quinn, and Mira review in parallel (you don't do anything)
   — If they find a blocking issue, Claude sends it back to the agent to fix
   — If they find advisory notes, Claude bundles them for you

5. Claude surfaces the approval prompt:
   "Here's what was built. Here are the findings. Approve to commit?"
   → You review and say yes (or give feedback)

6. The commit lands. Hooks update the protocol automatically.

7. Claude tells you what's next → back to step 1
```

That's the entire loop. Your job is: read the approval prompt, decide, say yes or no.

---

## Slash Commands You'll Actually Use Day-to-Day

| When you want to... | Type |
|---|---|
| See overall project progress | `/status` |
| Check what's coming next | `/next-step` |
| Start a new project | `/init` |
| Survey an existing codebase | `/archaeology` |
| Roll back a bad commit | `/rollback` |
| Change the plan mid-project | `/replan` |
| Close out a finished project | `/project-complete` |

---

## What Claude Does Automatically (You Don't Touch These)

- Reads `project-state.json` at every session start to know where things stand
- Reads `team-preferences.md` to calibrate how strict reviewers are
- Runs the quality gate wave (Viktor + Sage + Quinn + Mira) after every commit
- Updates `commit-protocol.md` and `project-state.json` after every commit via hooks
- Routes handoff notes between agents
- Manages token budgets so agents don't run out of context mid-task

---

## Tuning the System to Your Style

Edit `team-preferences.md` any time to adjust:

- **Viktor too strict on style?** Set style to `ignore` — he'll focus on logic only
- **Sage blocking too aggressively?** Set your exposure to `internal-only` — LOW findings get suppressed
- **Want shorter approval prompts?** Set `approval_prompt_length: terse`
- **Working fast with deadline pressure?** Set `deadline_pressure: high` — Claude parallelizes more aggressively

Changes take effect at the next session start.

---

## If Something Goes Wrong

| Situation | What to do |
|---|---|
| A commit broke something | `/rollback` — Claude assesses blast radius before touching anything |
| The plan needs to change | `/replan` — Claude drafts the change, you approve before anything is written |
| An agent is blocked | Claude will surface it to you automatically — you decide how to unblock |
| You want a second opinion on code | `/review-request` — invokes Viktor on any file, any time |
| You're worried about security | `/security-audit` — invokes Sage on any file, any time |

---

## First Session Checklist

```
□ UNIVERSAL_WORKFLOW/ contents copied to project root
□ Opened Claude Code in the project directory
□ Ran /init and answered all 6 questions
□ Reviewed and approved the commit protocol
□ Said yes to Commit 01
```

Once that checklist is done, the system runs itself.
Your job from here is to read, decide, and approve — one commit at a time.

---

*The full ruleset is in `ORCHESTRATION.md` if you want to understand how anything works under the hood.*
*Every agent's personality and standards are in `.claude/agents/`.*
*Every slash command's full protocol is in `.claude/commands/`.*
