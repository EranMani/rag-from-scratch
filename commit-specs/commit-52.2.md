# Commit 52.2 Spec — `welcome-ux-quick-wins`
> **Project:** rag-from-scratch · **Assignee:** frontend (Aria) · **Load only for the active commit.**
> **Note:** Added 2026-05-24 — Team Lead registered as first-time Novice and found prompt suggestions
> are plain text (not clickable). Mira + Aria consultation confirmed this as a day-1 retention risk.
> C52.3 depends on the chip UI layer established here.

---

### Commit 52.2 — `welcome-ux-quick-wins`

**Commit message:** `feat(EranMani): add clickable suggestion chips to welcome card — mastery-level-aware`

**Body:**
Replace plain-text starter suggestions in the welcome card with clickable chip buttons.
Chips are mastery-level-aware (novice/intermediate/advanced sets). Clicking a chip
calls send_message() directly — same pattern as nav chips.

**Motivation:**
Team Lead (2026-05-24): prompt suggestions are plain text — users don't know they can
type them. First impression is passive. Day-1 retention risk: user sees a welcome message
with suggestions buried in markdown but no obvious entry point to act. C52.3 (auto-initiated
intro) builds on this chip layer — it must exist first.

---

### What to Build

**1. Add `_WELCOME_CHIPS` constant (near the other module-level constants)**

```python
_WELCOME_CHIPS: dict[str, list[str]] = {
    "novice": [
        "Explain RAG like I'm 14 — no jargon",
        "What problem does RAG solve?",
        "How is RAG different from a regular chatbot?",
        "What is an embedding and why does it matter?",
    ],
    "intermediate": [
        "Walk me through chunking strategies and their trade-offs",
        "When should I use dense vs sparse retrieval?",
        "How does LangChain simplify RAG pipelines?",
        "What's the difference between MMR and similarity search?",
    ],
    "advanced": [
        "How do I evaluate retrieval quality in production?",
        "What are the trade-offs between different vector databases at scale?",
        "How do I optimize RAG for latency without sacrificing accuracy?",
        "What production failure modes should I design for in RAG systems?",
    ],
    "expert": [
        "How do I evaluate retrieval quality in production?",
        "What are the trade-offs between different vector databases at scale?",
        "How do I optimize RAG for latency without sacrificing accuracy?",
        "What production failure modes should I design for in RAG systems?",
    ],
}
```

Aria may adjust wording with good judgment — the content above is a strong default,
not verbatim. All strings are hardcoded (no user data in chip text).

**2. Remove the "Try: **...**" suggestion lines from `_build_welcome_message()`**

The clickable chips replace the plain-text "Try:" prompts. Remove the `f"Try: **{...}**"`
suffix from every return branch in `_build_welcome_message()`. The prose (progress summary,
welcome back, gap/strength recommendation text) stays. Only the "Try:" line is removed.

Specifically: all branches in `_build_welcome_message()` that end with
`f"Try: **{_starter(slug)}**"` or similar — remove that trailing line/fragment from
the returned string. The function still returns the welcome prose; chips render separately.

**3. Render chips in the welcome card section**

In `index()`, in the welcome card section (around line 2268 — where `ui.markdown(_welcome_msg)` is rendered):

After the `ui.markdown()` call, add:

```python
_ml = (_welcome_profile or {}).get("mastery_level", "novice")
_chip_list = _WELCOME_CHIPS.get(_ml, _WELCOME_CHIPS["novice"])
with ui.row().style("flex-wrap:wrap; gap:8px; margin-top:14px"):
    for _ct in _chip_list:
        async def _chip_click(_e, _t=_ct):
            await send_message(_t)
        ui.button(_ct).props("flat dense no-caps").style(
            "background:rgba(109,40,217,0.12); border:1px solid rgba(109,40,217,0.4); "
            "color:#a78bfa; border-radius:20px; padding:4px 14px; "
            "font-size:0.82rem; letter-spacing:0"
        ).on("click", _chip_click)
```

**Important — closure pattern:** `send_message` and `question_input` are both defined
later in the page function (after the welcome card block). Python closures look up names
at call time, not definition time, so this is safe — both names will exist in scope
before any chip can be clicked. Use default-argument capture (`_t=_ct`) to fix the
loop variable late-binding issue (same pattern as admin delete buttons). Do NOT define
`_chip_click` outside the loop — it must capture `_t` per iteration.

**No-profile case:** If `_welcome_profile` is None, `_ml` defaults to `"novice"`.
Show novice chips (these are safe generic entry points for any unauthenticated user).

---

### Files Touched

| File | Change |
|---|---|
| `src/app/ui.py` | Add `_WELCOME_CHIPS` constant (module level); remove "Try:" lines from `_build_welcome_message()`; add chip row after `ui.markdown(_welcome_msg)` in welcome card |

**Depends on:** 52.1
**Blocks:** 52.3 (C52.3's auto-initiated intro carousel reuses the chip UI layer)
**Can run parallel with:** nothing (sequential with 52.3)

---

### Scope Hard Limits

- Touch ONLY `_build_welcome_message()` (remove Try: lines only) and the welcome card render section in `index()`
- Do NOT change `_build_welcome_message()` signature
- Do NOT add new API calls — `_welcome_profile` is already loaded
- Do NOT change any other UI section, chat logic, MCQ rendering, or nav chips
- Chips must NOT render user-controlled data — only hardcoded strings from `_WELCOME_CHIPS`
- Do NOT use `ui.html()` for chip content

---

### Testing — Done When

- [ ] Welcome card shows 4 clickable chips matching the user's mastery level
- [ ] Novice user sees novice chip set; intermediate user sees intermediate set
- [ ] Clicking a chip calls `send_message()` with the chip text (message appears in chat)
- [ ] No-profile fallback shows novice chips (does not error)
- [ ] "Try: **...**" plain-text suggestions no longer appear in welcome markdown
- [ ] `_build_welcome_message()` signature unchanged
- [ ] Existing test suite passes (`pytest tests/` — 45 tests)

---

### Gate Triage

- **Viktor:** run — new UI component pattern (loop + async closure + default-arg capture); review closure correctness and forward-reference safety
- **Sage:** skip — all chip content is hardcoded constants; no user data in chip text or labels; no trust boundary crossed
- **Quinn:** skip — UI behavior; no business logic or coverage gap
- **Mira:** skip — this is a tech delivery of an already-approved replan requirement; no new product decisions

**Model:** Haiku for Viktor.
