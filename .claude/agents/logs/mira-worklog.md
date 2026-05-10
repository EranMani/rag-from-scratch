# Mira — Worklog
# Project: RAG from Scratch
# Role: Senior Product Manager

---

## Current State
*Last updated: Commit 20 `dynamic-chat-ui` final gate review · 2026-05-10*

**Last completed:** Commit 20 `dynamic-chat-ui` — final product gate (fix pass confirmation)
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
