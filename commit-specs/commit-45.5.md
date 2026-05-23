# Commit 45.5 Spec — `rag-prompt-quality`
> **Project:** rag-from-scratch · **Assignee:** ai-engineer · **Load only for the active commit.**
> **Note:** Added 2026-05-23 — Team Lead registered as first-time Novice and found AI responses feel cold/rigid and inconsistently formatted. Mira + Nova consultation confirmed root cause: weak persona framing and defensive "only if" formatting rules. Prompt-only fix; no code or graph changes.

---

### Commit 45.5 — `rag-prompt-quality`

**Commit message:** `feat(EranMani): strengthen novice persona and enforce markdown formatting floor`

**Body:**
Rewrite RESPONSE FORMAT block across all 4 prompts to flip from permissive ("only if")
to prescriptive ("must floor"). Add explicit persona statement to _NOVICE_SYSTEM and
harden analogy requirement from suggestion to constraint.

**Motivation:**
Nova diagnosed two root causes: (1) _NOVICE_SYSTEM describes the target audience but
does not give the LLM a behavioral persona — the model defaults to its general assistant
voice when the persona is implied rather than explicit. (2) RESPONSE FORMAT rules use
"only if/when/for" language, which the LLM treats as permission withheld, not permission
granted — so most responses render as plain prose. Both are prompt-only fixes.

**What to build:**

1. **_NOVICE_SYSTEM — persona statement** (top of system prompt, before COMPREHENSION LEVEL)
   - Add one sentence that gives the LLM an explicit persona, e.g.:
     "You are an enthusiastic and patient tutor — you never sound like a manual or a search engine."
   - This anchors tone before any instruction list runs.

2. **_NOVICE_SYSTEM — harden analogy requirement**
   - Change: "Lead with a real-world everyday analogy BEFORE introducing the technical concept."
   - To: "You MUST open every answer with a real-world analogy. Do this even for short answers."
   - Remove soft qualifier — make it a hard constraint.

3. **RESPONSE FORMAT — all 4 prompts (novice, intermediate, advanced, expert + default)**
   - Replace the current "only if/when/for" conditional rules with a minimum floor:
     - "Every response must bold the first technical term it introduces."
     - "Responses longer than 3 sentences must use at least one structural element (bold, list, or heading)."
     - "Single-sentence answers may use plain prose — no structure required."
   - Keep the same categories (bold, numbered list, table, heading, plain prose) but
     reframe them as defaults that activate on a floor condition, not exceptions.

**Files touched:**
- `src/agents/prompts/rag.py` — rewrite `_NOVICE_SYSTEM` (persona + analogy) and
  RESPONSE FORMAT block in all 5 prompt strings (`_DEFAULT_SYSTEM`, `_NOVICE_SYSTEM`,
  `_INTERMEDIATE_SYSTEM`, `_ADVANCED_SYSTEM`, `_EXPERT_SYSTEM`)

**Depends on:** 45.4.1
**Blocks:** 46
**Can run parallel with:** 45.6 (different file — `rag.py` vs `ui.py`)

**Scope hard limits:**
- Touch ONLY `src/agents/prompts/rag.py` — no graph, no nodes, no state changes
- Do NOT change INTENT CLASSIFICATION logic (Cases 1/2/3) — those work correctly
- Do NOT change the HOW TO EXPLAIN bullet list structure — only the analogy line gets hardened
- The `{context}` template variable must remain unchanged at the end of every prompt

**Testing — done when:**
- [ ] All 5 prompt strings (`_DEFAULT_SYSTEM`, `_NOVICE_SYSTEM`, `_INTERMEDIATE_SYSTEM`, `_ADVANCED_SYSTEM`, `_EXPERT_SYSTEM`) have the updated RESPONSE FORMAT floor
- [ ] `_NOVICE_SYSTEM` has a persona statement before COMPREHENSION LEVEL
- [ ] `_NOVICE_SYSTEM` HOW TO EXPLAIN analogy rule is hardened to "MUST open every answer"
- [ ] `{context}` template variable is still present and unmodified in all prompts
- [ ] Existing test suite passes (no code logic changed — tests should be unaffected)

**Gate triage:**
- Viktor: skip — no code logic change; pure string constant rewrite
- Sage: skip — no auth, secrets, or user input trust boundary
- Quinn: skip — no new code paths; existing tests cover template selection
- Mira: run — user-facing behavior change (tone and formatting of every AI response)
