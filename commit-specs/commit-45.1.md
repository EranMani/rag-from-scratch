# Commit 45.1 Spec — `novice-prompt-comprehension`
> **Project:** rag-from-scratch · **Assignee:** ai-engineer · **Load only for the active commit.**
> **Note:** Added 2026-05-22 — product decision: novice prompt must target zero-technical-knowledge users, not just "beginners". Mira reviewed; design validated.

---

### Commit 45.1 — `novice-prompt-comprehension`

**Commit message:** `feat(EranMani): tighten novice system prompt to zero-knowledge comprehension level`

**Body:**
Sets an explicit comprehension target in `_NOVICE_SYSTEM`: explain as if to a curious
14-year-old with no technical background. Adds hard instructions to lead with a
real-world analogy before introducing any technical term, and to never assume
familiarity with any vocabulary.

**Motivation:**
The previous prompt used "patient tutor / complete beginner" framing but still allowed
the model to assume technical curiosity. Non-technical users (e.g. someone with no AI
exposure) would land on jargon-heavy topic names without the context to interpret them.
The new framing closes that gap.

**Files touched:**
- `src/agents/prompts/rag.py` — `_NOVICE_SYSTEM` rewritten with explicit comprehension level, analogy-first instruction, and "define every term before using it" constraint

**Depends on:** 45 (rag-specialist-content)
**Blocks:** 45.2

**Scope hard limits:**
- Only `_NOVICE_SYSTEM` is touched — no other prompt template modified
- No logic changes — prompt text only

**Testing — done when:**
- [ ] `_NOVICE_SYSTEM` contains explicit comprehension level instruction
- [ ] `_NOVICE_SYSTEM` instructs model to lead with analogy before technical term
- [ ] `_NOVICE_SYSTEM` instructs model to define every term before using it
- [ ] No other prompt template changed
- [ ] Existing tests pass (no logic touched)
