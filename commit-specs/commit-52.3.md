# Commit 52.3 Spec — `auto-initiated-intro`
> **Project:** rag-from-scratch · **Assignee:** ai-engineer (Nova) then frontend (Aria) · **Load only for the active commit.**
> **Note:** Added 2026-05-24 replan. Closes the last day-1 retention gap: "AI waits passively on session start."
> Depends on C52.2 chip layer. Sequential — Aria's trigger depends on Nova's endpoint contract.

---

### Commit 52.3 — `auto-initiated-intro`

**Commit message:** `feat(EranMani): auto-initiate AI intro on session start — personalized for first-time and returning users`

**Body:**
On every authenticated page load, the AI automatically sends the first message — no
user input required. First-time users receive a compelling RAG introduction (intriguing,
not dry) followed by 3 static context cards. Returning users receive a personalized
progress recap with a concrete next-focus recommendation. Routes through the real
LangGraph graph in both cases.

**Motivation:**
Team Lead (2026-05-24): "AI waits passively on session start" identified as a critical
day-1 retention risk. First impression is everything — the app must engage immediately,
not wait for the user to figure out what to type. Returning users must feel the app
knows them and is tracking their progress.

---

### What to Build — Nova (AI Engineer)

**New endpoint: `POST /api/chat/seed`**

File: `src/app/api/routes/chat.py` — add alongside the existing POST `/api/chat`.

**Logic:**

1. Require JWT authentication (same decorator/dependency as existing chat route). Anonymous users get 401 — chat is authenticated-only.

2. Read user profile from DB:
   - `mastery_level: str` (default `"novice"` if not set)
   - `topic_scores: dict[str, float]` (default `{}` if not set)

3. Determine user type:
   - **First-time:** `topic_scores` is empty (`{}`) or every value is `0.0`
   - **Returning:** has at least one topic score `> 0.0`

4. Build a seed prompt string (see below). This becomes `state.question` in the graph.

5. Invoke `app.state.rag_graph.astream_events()` with the seed prompt and the user's thread config — same invocation pattern as the existing `/api/chat` endpoint.

6. Return `StreamingResponse(media_type="text/event-stream")` — same SSE format:
   - `{"type": "token", "content": "..."}` — one per token
   - `{"type": "done", "user_level": "...", "assessed_topics": {}}` — final event

**Seed prompt guidance — First-time users:**

The prompt must produce a response that:
- Leads with WHY RAG matters — a real, impressive use case (not a textbook definition)
- Explains what RAG is in plain language appropriate to `mastery_level`
- Tells the user what they'll build competence in
- Ends with a warm invitation to ask their first question or click a suggestion

Target length of the AI response: 100–150 words. Enthusiastic but not cheesy.
Do NOT have the AI say "I am an AI" — write the prompt so the tutor voice is natural.

Example seed prompt for first-time novice (Nova adapts as needed):
```
You are a RAG learning coach. A brand-new student (level: novice) has just opened
this app for the first time. Give them a short, exciting introduction that:
1. Opens with a surprising, real-world use case where RAG solves something impressively
   (e.g., a company's internal knowledge base that actually answers correctly)
2. Explains in plain terms what RAG is — no jargon, analogy preferred
3. Lists 2–3 things they'll understand by the end of this course
4. Ends with an inviting question or "pick a topic below to get started"
Keep it under 150 words. Sound like a coach who genuinely cares, not a textbook.
```

Adapt tone/vocabulary for `mastery_level` (novice = analogy-first; intermediate+ = can use technical terms).

**Seed prompt guidance — Returning users:**

Build a `topic_summary` string from `topic_scores`:
- Scored topics `>= 0.7`: list as strengths
- Scored topics `< 0.7` and `> 0.0`: list as gaps / in-progress
- Unscored topics: list as "not yet covered"

Example seed prompt for returning user (Nova writes the actual prompt):
```
You are a RAG learning coach welcoming back a student. Their level: {mastery_level}.
Here is their topic progress:
  Strengths (score ≥ 0.7): {strengths_list}
  In progress (score < 0.7): {gaps_list}
  Not yet covered: {uncovered_list}

Write a warm, specific welcome-back message (2–3 sentences max) that:
1. Acknowledges one specific strength by name
2. Identifies the single highest-priority next focus area (their biggest gap, or first
   uncovered topic in curriculum order if no gaps)
3. Ends with an invitation to continue

Be specific — name actual topics. Do not be generic. Sound like a coach who has been
tracking their journey.
```

**Curriculum order** for "next topic" recommendation (use this order for priority):
`chunking_strategies → embeddings_and_similarity → retrieval_methods → vector_databases →
context_and_prompting → evaluation_and_metrics → rag_pipeline_architecture → document_ingestion →
langchain_fundamentals → langgraph_fundamentals → production_patterns`

---

### What to Build — Aria (Frontend)

**File: `src/app/ui.py`**

**Part 1 — Static intro cards (first-time users only)**

In `index()`, in the welcome card section (where `_welcome_msg` and chips are rendered):

If `_welcome_profile` has no topic scores (first-time), render 3 hardcoded info cards
ABOVE the `ui.markdown(_welcome_msg)` block:

```python
_is_first_time = not any(
    (v or 0.0) > 0.0 for v in (_welcome_profile or {}).get("topic_scores", {}).values()
)

if _is_first_time:
    with ui.row().style("gap:12px; flex-wrap:wrap; margin-bottom:20px"):
        _intro_cards = [
            ("What is RAG?",
             "Retrieval-Augmented Generation (RAG) combines a knowledge base with an AI "
             "language model — giving it accurate, grounded answers instead of hallucinations."),
            ("How this app works",
             "We ask adaptive questions, track what you understand, and adjust difficulty "
             "as you improve. The more you engage, the more personal your path becomes."),
            ("What you'll cover",
             "Core RAG concepts · Chunking & Embeddings · Retrieval Methods · "
             "LangChain · LangGraph · Production Patterns"),
        ]
        for _title, _body in _intro_cards:
            with ui.card().style(
                "background:rgba(109,40,217,0.08); border:1px solid rgba(109,40,217,0.3); "
                "border-radius:12px; padding:16px 20px; min-width:180px; flex:1"
            ):
                ui.label(_title).style(
                    "font-weight:700; color:#a78bfa; font-size:0.9rem; margin-bottom:6px"
                )
                ui.label(_body).style(
                    "color:#c4b5fd; font-size:0.8rem; line-height:1.5"
                )
```

All strings are hardcoded. No user data in card content. Do NOT use `ui.html()` for card text.
Aria may adjust card wording with good judgment — this copy is a strong default.

**Part 2 — Auto-seed trigger on page load**

After all UI elements in `index()` are defined, add:

```python
asyncio.ensure_future(_seed_session())
```

Define `_seed_session()` as an inner async function within `index()` (same pattern as
other inner async functions in `index()`):

```python
async def _seed_session():
    try:
        response = await http.post(
            "/api/chat/seed",
            headers=auth_headers(),
        )
        # parse the SSE stream and display as AI message
        # same SSE parsing pattern used elsewhere for streaming
    except Exception:
        pass  # seed failure is silent — chat still works normally
```

**The seed response appears as an AI message WITHOUT a preceding user bubble.**
Aria must implement a `_display_ai_seed(stream)` function (or inline logic) that:
- Creates an AI message bubble in the chat area
- Appends tokens as they arrive (same streaming pattern as regular chat)
- Does NOT add a user message bubble above it

If `httpx` async streaming is not already in use in the frontend, Aria adapts the
SSE parsing to whatever pattern already exists in `index()` for streaming chat responses.

**When NOT to seed:** If the user is not authenticated (redirected before reaching `index()`),
the seed is never triggered. No anonymous handling needed.

---

### Files Touched

| File | Change | Agent |
|---|---|---|
| `src/app/api/routes/chat.py` | Add `POST /api/chat/seed` endpoint | Nova |
| `src/app/ui.py` | Add 3 static intro cards (first-time); add `_seed_session()` + trigger | Aria |

**Depends on:** 52.2 (chip UI layer in `index()`)
**Blocks:** 53 (nginx-config — all UX work must be done first)
**Sequence:** Nova commits first; Aria receives Nova's endpoint contract as a handoff

---

### Scope Hard Limits

**Nova:**
- Touch only `src/app/api/routes/chat.py`
- No new state fields in `AgentState`
- Reuse the existing graph invocation pattern exactly — do not invent a new execution path
- No hardcoded AI response text — the seed prompt goes through the real graph

**Aria:**
- Touch only `src/app/ui.py`
- Static card strings are hardcoded only — no user data in card text
- Do NOT use `ui.html()` for any card or message content
- `_seed_session()` failure must be silent — do not surface errors to the user
- Do NOT modify `send_message()` — implement the seed display separately

---

### Testing — Done When

- [ ] First-time user (no topic scores): sees 3 static intro cards + AI intro streams in automatically without typing
- [ ] Returning user (has topic scores): no static cards; personalized welcome-back + next-focus recommendation streams in
- [ ] Seed response appears as AI message bubble — no user bubble above it
- [ ] Intro message is compelling and mastery-level-appropriate (manual review — not a test)
- [ ] Returning-user message names a specific topic (not generic "keep going")
- [ ] Seed failure (network error) is silent — chat input and chips still work normally
- [ ] Clicking a welcome chip still works after auto-seed completes
- [ ] `pytest tests/` — 45/45 pass (no regressions)

---

### Gate Triage

- **Viktor:** run — new endpoint + SSE response pattern + conditional profile logic; review invocation correctness and error handling
- **Sage:** run — user's `topic_scores` data flows from DB into an LLM prompt (trust boundary crossing); verify no raw user-controlled strings reach the prompt without sanitization
- **Quinn:** skip — no new business logic branch with measurable coverage gap; seed is a page-load side effect, not a testable unit
- **Mira:** skip — tech delivery of an approved replan requirement; no new product decisions

**Models:** Haiku for both Viktor and Sage.
