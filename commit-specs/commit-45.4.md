# Commit 45.4 Spec — `question-difficulty-degradation`
> **Project:** rag-from-scratch · **Assignee:** ai-engineer · **Load only for the active commit.**
> **Note:** Added 2026-05-22 — product decision: graceful degradation when user signals a question is too hard. Three steps: original → LLM simplifies → fetch answer from docs.

---

### Commit 45.4 — `question-difficulty-degradation`

**Commit message:** `feat(EranMani): add question difficulty degradation — simplify then reveal`

**Body:**
When a user signals that a question is too hard, the system degrades gracefully:
step 1 rephrases the question at a lower difficulty via a constrained LLM prompt;
step 2 (if still stuck) retrieves and shows the answer from the knowledge base.
Simplification happens once only — the system does not loop.

**Motivation:**
Product decision (2026-05-22): the knowledge base stays thin (one question per concept,
no pre-generated variants). Simplification is dynamic, handled by the model at runtime.
The LLM must be tightly constrained to rephrase without revealing the answer. Fallback
to docs is the existing RAG retrieval path — no new infrastructure required.

**Degradation path:**
```
Step 1 — Original question delivered
         ↓ (user signals difficulty: "too hard", "I don't understand", "help", etc.)
Step 2 — LLM rephrases question at lower complexity
         Constraint: rephrase only — do NOT hint at or reveal the correct answer
         This step fires ONCE. State tracks that simplification has occurred.
         ↓ (user still cannot answer)
Step 3 — Fetch answer from docs via existing RAG retrieval
         Show the answer with explanation from the knowledge base
         Mark question as a gap in identified_gaps
```

**What to build:**

1. **State addition** — add `question_simplified: bool` to `AgentState`
   - Tracks whether step 2 has fired for the current pending question
   - Reset to `False` when a new question is delivered
   - Prevents re-simplification loop

2. **Difficulty signal detection** — add `_is_difficulty_signal(message: str) -> bool`
   - Simple keyword/phrase check: "too hard", "don't understand", "I don't know",
     "help", "can you simplify", "hint", etc.
   - Conservative — false negatives are safer than false positives

3. **Simplification prompt** — add to `src/agents/prompts/assessment.py`
   - Instruction: take the original question, rephrase at a lower difficulty level
   - Hard constraint: "Do NOT hint at the correct answer. Do NOT reveal what the
     right answer is. Change only the vocabulary and framing, not the concept tested."
   - Single-shot — no back-and-forth

4. **Degradation routing** — update `evaluate_answer` in `evaluation.py`
   - Before the existing MCQ/open branch: check for difficulty signal
   - If signal detected and `question_simplified=False` → simplify and re-ask (step 2)
   - If signal detected and `question_simplified=True` → RAG retrieval path (step 3)
   - Normal answer → existing evaluation path (unchanged)

**Files touched:**
- `src/agents/state.py` — add `question_simplified: bool` field
- `src/agents/assessment/evaluation.py` — add degradation routing before existing branch
- `src/agents/prompts/assessment.py` — add simplification prompt
- `src/agents/assessment/results.py` — pass `question_simplified` reset on new question delivery

**Depends on:** 45.3
**Blocks:** 46

**Scope hard limits:**
- Simplification fires ONCE per question — enforced by `question_simplified` state field
- The simplification LLM call must NOT reveal the answer — this constraint belongs in the prompt, not in post-processing
- RAG retrieval in step 3 uses the existing retrieval path — do NOT duplicate retrieval logic
- Do NOT change scoring for a degraded answer — the grading result is what it is; log the gap normally

**Testing — done when:**
- [ ] Difficulty signal detected for representative phrases ("too hard", "I don't understand", "help")
- [ ] Simplification fires once; second difficulty signal triggers doc fetch, not re-simplification
- [ ] `question_simplified` resets to `False` when a new question is delivered
- [ ] Simplification prompt contains explicit "do not reveal the answer" constraint
- [ ] Normal answer path (no difficulty signal) is unchanged — all existing tests pass
