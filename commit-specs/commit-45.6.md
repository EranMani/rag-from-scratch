# Commit 45.6 Spec — `welcome-message-ux`
> **Project:** rag-from-scratch · **Assignee:** frontend · **Load only for the active commit.**
> **Note:** Added 2026-05-23 — Team Lead found first-time welcome too rigid for non-technical users, and returning-user welcome lacks progress visibility. Mira rated both as blockers. Scoped to _build_welcome_message() only.

---

### Commit 45.6 — `welcome-message-ux`

**Commit message:** `feat(EranMani): rewrite welcome messages — first-time scaffold and personalized return`

**Body:**
Replace the first-time Novice welcome with a scaffolded entry showing 3–4 concrete
starter paths. Replace the returning-user welcome with a progress-first summary
(phases completed, last topic, clear resume path).

**Motivation:**
Mira (product review 2026-05-23): first-time message outsources the first decision to
the user without establishing what the app is. Non-technical users interpret this as
"the app doesn't want to guide me." Returning users see one weak spot + one question
but not where they are in their learning journey — missing progress visibility and
narrative continuity. Both are day-1 retention risks.

**What to build:**

1. **First-time Novice welcome (interaction_count == 0, mastery_level == "novice")**

   Current (replace this):
   ```
   Ready to start, **{name}**? I'll build a picture of where you are as we go.
   Best first move: **What is retrieval-augmented generation?**
   ```

   Replace with a scaffolded entry that:
   - Opens with a warm 1-sentence description of what the app is
   - Offers 3–4 concrete starter paths the user can copy-paste or click
   - Paths should span different entry points (total beginner, ML-aware, builder)
   - Example structure (implement with good judgment — not verbatim):
     ```
     Welcome, **{name}**! I'm RAG Tutor — your AI-powered guide to Retrieval-Augmented Generation.

     Not sure where to start? Try one of these:
     - "Explain RAG like I'm 14 — no jargon"
     - "I know some ML — how does RAG differ from fine-tuning?"
     - "I'm building a chatbot — what RAG pattern should I use?"
     - "Give me the 5-minute overview of why RAG matters"
     ```
   - Keep it scannable — no walls of text. The user should be able to act in under 10 seconds.

2. **Returning user welcome (interaction_count > 0)**

   Current approach: shows top gap + starter question OR top strength + next unlock.

   Replace with a progress-first structure:
   - **Progress summary:** show how many topics done per phase (e.g. "Foundations: 2/2 ✓ · Core: 1/5 · Production: 0/2")
   - **Last active area:** surface the most recently active topic if available from gaps/strengths
   - **Resume path:** one concrete next step (keep the existing gap/strength logic for picking the recommendation)
   - Example structure (implement with good judgment — not verbatim):
     ```
     Welcome back, **{name}**.

     **Your progress:** Foundations ✓ · Core Components 1/5 · Production 0/2

     Last time you worked on **Embeddings & Similarity** — ready to continue?
     Try: **What is cosine similarity and why does it matter for RAG?**
     ```
   - Keep it short — 3–5 lines total. Progress + location + one action.

3. **No-profile fallback** — keep the existing 2-line fallback for unauthenticated users (`if not profile`). Do not touch it.

**Data available in `profile` dict:**
- `interaction_count: int`
- `mastery_level: str` ("novice" / "intermediate" / "advanced" / "expert")
- `gaps: list[str]` — topic slugs where user is weak
- `strengths: list[str]` — topic slugs where user is strong
- `topic_scores: dict[str, float]` — per-slug scores

**Phase structure (already defined in ui.py as `_PHASE_TOPICS` and `_PHASE_LABELS`):**
- novice phase: `["embeddings_and_similarity", "rag_pipeline_architecture"]` (Phase 1 — Foundation)
- intermediate phase: `["chunking_strategies", "vector_databases", "retrieval_methods", "context_and_prompting", "langchain_fundamentals"]` (Phase 2 — Core)
- advanced/expert: `["evaluation_and_metrics", "production_patterns"]` (Phase 3 — Production)

For the progress summary, compute done/total per phase using `topic_scores` — a topic is "done" if its score >= 0.70.

**Files touched:**
- `src/app/ui.py` — rewrite `_build_welcome_message()` (lines 119–184) only

**Depends on:** 45.4.1
**Blocks:** 46
**Can run parallel with:** 45.5 (different file — `ui.py` vs `rag.py`)

**Scope hard limits:**
- Touch ONLY `_build_welcome_message()` — no other function in ui.py
- Do NOT add new API calls — profile data is already passed in as a dict parameter
- Do NOT change the function signature: `(display_name: str | None, profile: dict | None) -> str`
- Do NOT add NiceGUI components — the function returns a markdown string rendered by `ui.markdown()`
- The "no profile" fallback (line 122–126) stays unchanged — do not touch it

**Testing — done when:**
- [ ] First-time Novice (interaction_count == 0, mastery_level == "novice") returns scaffolded entry with 3–4 starter paths
- [ ] Returning user with gaps returns progress summary + top gap + starter question
- [ ] Returning user with strengths returns progress summary + next unlock recommendation
- [ ] Fallback (no profile) is unchanged
- [ ] Function signature unchanged: `(display_name: str | None, profile: dict | None) -> str`
- [ ] Existing test suite passes

**Gate triage:**
- Viktor: skip — no code logic beyond string building; no new functions or paths
- Sage: run — welcome message renders user profile data (display_name, topic progress); verify no XSS via f-string injection into ui.html() — function returns a plain markdown string for ui.markdown(), not ui.html(), so risk is low but confirm
- Quinn: skip — string-building function; behavior verified by reading output, not unit test
- Mira: run — explicitly requested; this commit exists because of her product finding
