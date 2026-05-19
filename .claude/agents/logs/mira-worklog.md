# Mira — Worklog
# Project: RAG from Scratch
# Role: Senior Product Manager

---

## Current State
*Last updated: Ad-hoc product assessment · 2026-05-19*

**Last completed:** Ad-hoc assessment — three feature ideas (question-gating, onboarding level-check, mixed question formats)
**Currently active:** none
**Blocked by:** none

**Open Handoffs — Outbound:**
- Commit 20 post-commit backlog: (1) badge string "Standard depth" is positional, not benefit-oriented — suggest "Balanced depth and detail"; (2) unknown-value fallback "Adapted for: {user_level}" exposes raw internal values — suggest "Adapted for you"; (3) profile panel visual cue and onboarding tooltip deferred per Team Lead acknowledgment.

**Open Handoffs — Inbound:**
- none

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Observation |
|---|--------|--------|-----------------|
| 01 | 03 `wire-conversation-history` | Done | Cache/history interaction is a real product defect, not an edge case; session ephemerality needs explicit UI communication |
| 02 | 20 `dynamic-chat-ui` (fix pass) | Done | Both original notes confirmed resolved; two low-stakes copy concerns flagged for post-commit backlog |
| 03 | 21 `production-compose` | Done | Monitoring profile opt-in in dev is a net positive; .env.prod.example needs a deployment order callout; portfolio signal is strong |
| 04 | 23 `scoring-model-product-spec` | Done | Produced full product spec draft for docs/scoring-model.md; decided trigger threshold (0.60), opt-in test framing, no score decay, user_level mapping |
| 05 | 27 `ui-header` | Done | "RAG Tutor" is product-correct; flagged naming consistency sweep as a follow-up commit before any external portfolio presentation |
| 06 | Ad-hoc | Done | Question-gating: agree with full confidence. Level-check: agree with self-report + 3-question diagnostic hybrid. Mixed formats: agree with open-first, MCQ-secondary, ~60/40 ratio |

---

## Session 01 — Commit 03: `wire-conversation-history`

**Date:** 2026-05-09

### Trigger

Team Lead requested product perspective review on Commit 03 before approval.
Three design choices were flagged for pressure-testing: retrieval-only history,
cache key omitting history, and in-process session ephemerality.

### Product Question

Does this commit deliver what a user would expect when they ask a follow-up question —
and does it expose any silent failures that could undermine the portfolio demo?

### Review Findings

**Design choice 1 — History in generation only, not retrieval:**
For the portfolio demo context, this is an acceptable tradeoff. A recruiter or
interviewer exploring the system is likely to ask follow-ups that reference prior
answers ("explain that more simply", "what did you mean by X"), not questions that
require retrieving entirely new documents based on prior context. The retrieval gap
only bites in a different scenario: "Earlier you mentioned chunking strategies —
what about overlapping chunks?" That retrieval would run against "overlapping chunks"
alone. The diff being reviewed does not surface this as a known limitation anywhere.

**Design choice 2 — Cache key excludes conversation history:**
This is a visible product defect in any multi-turn demo session. The sequence is:
user asks "What is RAG?", gets a real answer, the answer is cached under the query
key. User then has a five-turn conversation. At some point, user or interviewer asks
"What is RAG?" again — perhaps to test caching, perhaps by accident. The cache
returns the original context-free answer. The user notices the response ignores the
conversation that just happened. This is not an edge case in a demo — it is likely.
The implementation comment in chain.py (line 54-57) documents the intentional
history-after-retrieval ordering but says nothing about the cache interaction.

**Design choice 3 — In-process session ephemerality:**
The `SessionMemory` class is a plain Python object — a `defaultdict` inside a module
singleton. A server restart wipes it. This is architecturally fine for a portfolio
demo running on a single instance. The product risk is whether the UI or API communicates
this clearly to a user who expects continuity. Looking at chat.py, the session_id is
generated fresh as `str(uuid.uuid4())` when the client does not pass one. A user who
refreshes the NiceGUI page gets a new session_id and a blank memory — silently, with
no messaging. This is a hidden gotcha, not a documented limitation.

**Additional observation — unbounded memory growth:**
`SessionMemory` grows unbounded per the docstring ("grows unbounded"). `format_history`
truncates to the last 10 messages for the prompt, which is the right call for token
cost. But the underlying `_sessions` dict retains all messages forever in-process.
For a portfolio demo with one or two users this is not a runtime problem. For the demo
to not look like it's leaking, it's worth noting.

### Suggestions Generated

See output block in final response.

### Open Questions for Team Lead

- Should the cache defect (design choice 2) be addressed now or in Commit 17 when
  the cache key is formally fixed? The Commit 17 spec already plans to fix the cache
  key for user_level — adding history to the key at that point would be natural. But
  leaving it silently wrong for 14 commits is a risk in a demo context.
- Is session continuity across page refreshes in scope for any commit? If not, should
  the UI display a session indicator so a user knows when they are starting fresh?

---

## Session 04 — Commit 23: `scoring-model-product-spec`

**Date:** 2026-05-11
**Status:** Complete

### Trigger

Co-author `docs/scoring-model.md` with Lara. This is the canonical implementation
contract for Nova (Commit 24, assessment engine rewrite) and Rex (Commit 25, profile
scoring rewrite). Mira owns Questions 1, 2, 6, and 7 of the 7-question contract.
Questions 3–5 are answered by gates.md and are cited, not redefined.

### Product Question

How does testing feel to a user — transparent or hidden? When does it happen?
Does score decay make sense for a learning tool? What user level label belongs
at each point in the curriculum?

### Decisions Made

**Q1 — When does the agent administer a test question?**
Trigger: the user's topic score (or inferred readiness) crosses 0.60 on a topic,
OR the user has had 5+ content exchanges on a topic with no assessment on record.
Decision rationale: 0.60 is above random-correct territory (50% if guessing on
a binary question) but below the 0.70 passing gate — it means the user has been
engaging meaningfully and is ready to be tested without being ambushed before
they have encountered the material.

**Q2 — Test transparency**
Tests are fully transparent. The agent announces the switch to assessment mode with
a brief framing line before the first question. The user can defer once per topic per
session. They cannot defer indefinitely — after one deferral, the next content reply
on that topic re-triggers the assessment offer and cannot be deferred again in the
same session.

**Q6 — Score decay**
No score decay. The spaced repetition formula already handles recency implicitly —
the 0.7 weight on current session means a strong recent performance outweighs a weak
historical one. Decay would punish users who pause their learning for life reasons
(holidays, deadlines), which is the wrong user signal for a self-paced tool.

**Q7 — user_level mapping**
- novice: no phase started (all topics null)
- beginner: Phase 1 in progress (at least one Phase 1 topic scored, phase_1_passed = false)
- intermediate: Phase 1 passed (phase_1_passed = true), Phase 2 not yet passed
- advanced: Phase 2 passed (phase_2_passed = true), Phase 3 not yet passed
- expert: Phase 3 passed (phase_3_passed = true)

### Open Questions for Team Lead

None. All decisions are concrete and implementable.

---

## Session 03 — Commit 21: `production-compose`

**Date:** 2026-05-10

### Trigger

Team Lead requested product perspective on infrastructure commit before approval.
Three questions posed: developer experience with monitoring profile opt-in, portfolio signal of full observability stack in prod, and operator experience with `.env.prod.example`.

### Product Question

Does this infrastructure commit serve both the developer who maintains it and the portfolio reviewer who evaluates it — and does it communicate the right things to each?

### Review Findings

See suggestions generated below.

### Suggestions Generated

See output block in final response.

### Open Questions for Team Lead

- None requiring immediate action. One carry-forward flagged: `.env.prod.example` deployment order callout (Commit 22 or 23 scope).

---

## Session 05 — Commit 27: `ui-header`

**Date:** 2026-05-17

### Trigger

Narrow product question from Claude: is the brand name change from "Educational RAG System" to "RAG Tutor" product-correct, and does it create any consistency risk in the codebase?

### Product Question

Does "RAG Tutor" clearly communicate what this product does? Is there a risk from the old name persisting elsewhere in the codebase?

### Review Findings

**"RAG Tutor" as a display name:** Product-correct. "Educational RAG System" described the implementation; "RAG Tutor" describes the user's relationship with the product. Shorter, more active, pairs well with the `</>` brand mark. The one honest gap is that "RAG" is jargon, but the subtitle compensates by naming specific topics. The pairing works.

**Consistency risk:** Real, but not urgent. "Educational RAG System" persisting in `<title>` tags, meta tags, and the README creates a two-names problem that reads as an unfinished product to any recruiter or interviewer who looks past the header. This undermines the "wow on first impression" goal the replan set.

**Other concerns:** None.

### Suggestions Generated

Follow-up commit recommendation: naming consistency sweep targeting `<title>` tags across all HTML templates, `og:title`/`og:description` meta tags, the README heading, and any in-app page headings that still reference the old name. Should be queued before any external portfolio presentation — does not block Commit 27.

### Open Questions for Team Lead

- Should the naming consistency sweep be added to the commit queue as a discrete commit, or folded into an existing upcoming UI commit?
