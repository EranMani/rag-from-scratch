# Learning Log

> Written for the Team Lead. Plain language. No jargon without explanation.
> Every commit gets at minimum a one-liner. Significant commits get a full entry
> with code snippet, reasoning, and design pattern analysis.
>
> **Use this file to:** understand what was built, why it was built that way,
> which design patterns and architectural principles were applied, and how to
> explain all of it to a reviewer or recruiter.

> Technical terms (WAL mode, TOCTOU, CWE-209, etc.) are defined in [GLOSSARY.md](GLOSSARY.md).

---

## Agents in This Project

The following specialized AI agents contributed to this codebase. Each log entry
identifies the owning agent by name.

| Agent | Role | Responsible for |
|---|---|---|
| Rex | Backend Engineer | API routes, auth, profile service, SQLite, tests |
| Nova | AI/ML Engineer | LangGraph graph, RAG pipeline nodes, prompt engineering |
| Aria | Frontend Engineer | NiceGUI UI (`src/app/ui.py`) |
| Adam | DevOps Engineer | Docker, nginx, EC2 deployment scripts |
| Viktor | Code Reviewer | Reviews every commit — blocks on hard findings |
| Sage | Security Engineer | Reviews auth, secrets, and external API commits |
| Quinn | QA Engineer | Test coverage review |
| Mira | Product Manager | User-facing behavior review |
| Ryan | Tech Writer | This log, README, API reference |
| Claude | Orchestrator | Sequences commits, routes agents, maintains architecture docs |

---

## Entry Format Reference

### When to use which format

| Commit type | Format |
|---|---|
| Architectural change, new pattern, ARCHITECTURE.md or DECISIONS.md updated | Full entry |
| Non-obvious decision, security-relevant, cross-domain wiring | Full entry |
| Routine fix, config update, test addition, minor refactor | One-liner |

For full entries: include only the sections that add value for *this specific commit*.
"Why it wasn't obvious" and "Design pattern" are optional — use them when they genuinely
apply, omit them when they don't. Depth scales with complexity.

---

### Full Entry

---

**Commit [N] — [commit-name]** · [date] · [agent] · `[architectural | new feature | fix | security]`

> **In one sentence:** [One recruiter-ready line — what changed and why it matters.]

**Interview talking point:**
> **Q:** [The question this commit best answers in a technical interview]
>
> **A:** [1–2 sentences. The why, not the what. Written so the Team Lead can say it verbatim.]

**What happened and why:** *(1-2 sentences per bullet — no paragraphs)*
- [What was built or changed]
- [What problem it solves]
- [Why this approach over the alternative — only if a real choice was made]
- [Any non-obvious constraint or consequence — only if one exists]

**Reasoning & discovery:** *(1-2 sentences per step — no paragraphs)*
1. [How the problem was first understood]
2. [What was ruled out and why]
3. [What clinched the solution]

**The key change:** *(omit if prose explains it better than code)*
```python
# path/to/file.py
# Before / After — show only the load-bearing lines
```

**Design pattern:** *(omit if no genuine pattern was applied — do not invent one)*
| Pattern | What it means here | Why it was chosen |
|---|---|---|

**Files touched:**
- `path/to/file` — what changed

---

### One-liner Entry

---

**Commit [N] — [commit-name]** · [date] · [agent] · `[fix | config | test | refactor | docs]`

> **In one sentence:** [One recruiter-ready line.]

---
## Entries

> **Era 1 (C01–C20) archived:** [learning-log-archive-era1.md](learning-log-archive-era1.md) — Foundations: auth, profile service, LangGraph assembly, topic scoring, adaptive prompts, first UI panels (2026-05-08 to 2026-05-10).

---

**Commit 21 — `production-compose`** · 2026-05-10 · Adam · `architectural | config`

> **In one sentence:** A standalone production Docker Compose file was created with hardened defaults — no bind mounts, internal-only ports, log rotation, and memory caps — separating the deployment artifact from the developer-convenience dev compose.

**Interview talking point:**
> **Q:** How do you prevent developer shortcuts from leaking into production deployments when both use Docker Compose?
>
> **A:** By maintaining two separate Compose files: `docker-compose.yml` for dev (bind mounts, exposed ports, monitoring always on) and `docker-compose.prod.yml` for prod (baked image only, `expose:` not `ports:`, `restart: always`, log rotation). Sharing a file with overrides risks a dev default slipping through — separate files make the production surface explicit and reviewable.

**What happened and why:**
- A new `docker-compose.prod.yml` defines all 10 services with production-safe defaults rather than overriding the dev file
- The `./src:/app/src` bind mount is absent from prod: the container runs the baked image, so a source file edited on the host cannot silently change production behavior
- All services except `app` (port 8000) and `grafana` (port 3000) use `expose:` instead of `ports:` — this means they are reachable container-to-container but not from the host, shrinking the network attack surface
- An `x-logging` YAML anchor applies `json-file` log rotation (`max-size: 10m`, `max-file: 5`) to every service in one declaration, preventing unbounded disk fill under sustained load
- Ollama is capped at 5 GB memory; Elasticsearch JVM heap is bounded to 512 MB max — both prevent an overloaded service from starving other containers on the same host
- Dev monitoring (ELK + Prometheus + Grafana) was moved behind `profiles: [monitoring]` in `docker-compose.yml`, so `docker compose up` no longer starts those services for contributors who don't need them

**Why it wasn't obvious:**
- The `CHROMA_PORT` variable exists in two contexts that mean different things: `8001` is the dev *host* port (the port the developer's laptop uses to reach Chroma through Docker's port mapping), but inside the container network every service talks to Chroma on its *container* port `8000`. Pointing `CHROMA_PORT=8001` in prod would cause the app service to attempt connections to `chroma:8001` — a port nothing is listening on. The fix is to set `CHROMA_PORT=8000` explicitly in the prod app service's `environment:` block and document why 8000 and 8001 are both mentioned in different places.
- The original Chroma healthcheck used `bash -c 'echo > /dev/tcp/127.0.0.1/8000'` — a TCP probe written as a Bash built-in. The Chroma image uses BusyBox, which ships `sh`, not `bash`. The healthcheck silently failed on every startup. Replacing it with `curl -sf http://localhost:8000/api/v1/heartbeat || exit 1` uses a binary available in the image and checks the actual API path.
- The `ALLOW_ANNONYMOUS_CHAT` typo in `.env.prod.example` matched neither the Pydantic field name (`ALLOW_ANONYMOUS_CHAT`) nor any settings lookup — so the feature flag was silently ignored in any deployment that relied on the example file. Corrected spelling propagates to every future deployment that copies the example.

**What to watch for in future commits:**
- Any commit that adds a new service to `docker-compose.yml` must also add it to `docker-compose.prod.yml` with `restart: always`, the `x-logging` anchor, and `expose:` instead of `ports:` (unless it is intentionally host-accessible).
- New environment variables added to `.env.prod.example` must use the exact spelling of the corresponding Pydantic field — mismatch causes silent no-ops, not startup errors.
- If Ollama's memory cap of `5g` is hit under load, the OOM killer will terminate the container and `restart: always` will bring it back — but in-flight requests will be lost. Future commits that add streaming or long inference should document this failure mode.

**Code reference:**
- `docker-compose.prod.yml` — the `x-logging` YAML anchor at the top of the file and its `<<: *logging` references on each service show the DRY pattern for log rotation; the `chroma` service's `healthcheck` shows the corrected curl probe; the `app` service's `environment:` block shows the explicit `CHROMA_PORT=8000` override
- `.env.prod.example` — compare `CHROMA_PORT` comment ("container port — not the host mapping") against the dev compose `ports:` declaration (`8001:8000`) to see why the two values differ

---

**Commit 22 — `rag-curriculum-design`** · 2026-05-11 · Lara · `architectural`

> **In one sentence:** Rebuilt the entire RAG learning curriculum from a content-focused model to a mastery-based model, providing the canonical topic taxonomy and assessment rubrics that all downstream scoring logic depends on.

**Interview talking point:**
> **Q:** How do you know if a student actually understands retrieval-augmented generation?
>
> **A:** Not by asking them about it — by testing them on it. This commit separates "asking about a topic" (what the old model did) from "demonstrating mastery of a topic" (what learners need). The curriculum now defines what mastery looks like for each of 8 topics, with exact rubrics for correct/partial/incorrect answers. That distinction is why the entire scoring system needed to be rebuilt.

**What happened and why:**
- Lara created the complete RAG curriculum as a system of record: 8 topics with zero-to-hero learning objectives, prerequisites, common misconceptions, and 8 questions per topic with full rubrics.
- The prior scoring model inferred knowledge from question *content* (what students asked) rather than test *performance* (how well they answered). Learning science requires the latter — you can ask sophisticated questions about machine learning without understanding it.
- Moved from implicit, inference-based scoring to explicit, rubric-anchored scoring. Rubrics define correct/partial/incorrect with clear criteria; the LLM evaluator must match one of these three verdicts exactly, or the answer is treated as incorrect.
- Phase 2 (the foundational mid-tier) requires a *dual gate*: minimum 0.70 per topic AND mean 0.75 across all four Phase 2 topics. Phase 1 and 3 are per-topic only. This is deliberate — Phase 2 topics are tightly coupled (chunking → vectors → retrieval → prompting), so imbalanced mastery breaks later learning.

**Reasoning & discovery:**
1. The original model's "topic inferred from question content" was a proxy that fell apart immediately when students asked off-topic or metacognitive questions. No rubric for assessment = no way to know if someone actually understood their own answer.
2. Ruled out "keep the inference approach and tune it harder" — more tweaking doesn't fix the fundamental problem that asking ≠ understanding. Also ruled out "copy a generic ML curriculum" — RAG is specific enough that stock assessment patterns don't fit its semantics.
3. The clinching insight: all downstream commits (23 for product spec, 24 for assessment engine, 25 for scoring service) depend on having a canonical, machine-readable curriculum first. Nothing that follows can be correct if this is wrong or ambiguous. Built it bulletproof from the start.

**Design pattern:**
| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Curriculum-First | All assessment logic is derived from curriculum definitions, not the other way around. | Prevents scoring logic from creeping into assessment rubrics. Curriculum is ground truth; scoring is an application of it. |
| Explicit Verdict Vocabulary | Only `correct`, `partial`, `incorrect` are valid evaluator outputs; anything else is treated as `incorrect` and flagged. | Removes ambiguity about what the LLM evaluator is doing. No silent failures where an unexpected output breaks the gate. |
| Spaced Repetition Weighting | `0.7 × current_session + 0.3 × best_prior_session`. Primarily reflects now, rewards improvement. | Avoids anchoring permanent scores to early poor attempts while still reflecting recent performance. |

**Files touched:**
- `knowledge-base/curriculum/topic-slugs.json` — new, 8-slug canonical list
- `knowledge-base/curriculum/curriculum-map.md` — new, topic tree with learning objectives and prerequisites
- `knowledge-base/curriculum/gates.md` — new, phase gates, scoring formula, null-handling rules, verdict vocabulary
- `knowledge-base/curriculum/questions/embeddings_and_similarity.md` — new, 8-question bank with full rubrics
- `knowledge-base/curriculum/questions/rag_pipeline_architecture.md` — new, 8-question bank with full rubrics
- `knowledge-base/curriculum/questions/chunking_strategies.md` — new, 8-question bank with full rubrics
- `knowledge-base/curriculum/questions/vector_databases.md` — new, 8-question bank with full rubrics
- `knowledge-base/curriculum/questions/retrieval_methods.md` — new, 8-question bank with full rubrics
- `knowledge-base/curriculum/questions/context_and_prompting.md` — new, 8-question bank with full rubrics
- `knowledge-base/curriculum/questions/evaluation_and_metrics.md` — new, 8-question bank with full rubrics
- `knowledge-base/curriculum/questions/production_patterns.md` — new, 8-question bank with full rubrics
- `ARCHITECTURE.md` — updated, added Curriculum as top-level system component
- `DECISIONS.md` — updated, recorded Phase 2 dual-gate decision and spaced repetition weighting rationale
- `GLOSSARY.md` — updated, added 6 new terms: `topic`, `verdict`, `gate`, `phase`, `mastery score`, `topic slug`

**What was clear from the start:**
This is architectural. The entire assessment and scoring pipeline depends on these artifacts existing and being correct before anything downstream can be built. Lara was the right agent to build it because curriculum design is her domain; this commit is pure domain expertise, not code.

**What to watch for in future commits:**
- Commits 23–25 all consume from this curriculum directly. Any change to curriculum must cascade: gate thresholds to Commit 24, question banks to Commit 25, topic slugs to Commit 24–25.
- The dual gate for Phase 2 is strict by design. Monitor session data in Commit 25 to see if the 0.75 mean threshold is realistic or needs to be relaxed.
- `null` vs. `0.0` distinction in topic scores is load-bearing in gates.md — the gate logic explicitly checks `if score is null then fail()`. Do not collapse these in the schema later.
- The verdict vocabulary (`correct`, `partial`, `incorrect`) is canonical in gates.md. If the LLM evaluator in Commit 24 produces any other value, it gets flagged as incorrect *and* logged as an error for debugging.

---

**Commit 23 — `scoring-model-product-spec`** · 2026-05-11 · Mira + Lara · `architectural`

> **In one sentence:** Created `docs/scoring-model.md` — the canonical implementation contract for Nova (Commit 24) and Rex (Commit 25), defining when assessment triggers, how scores are computed, and how gate progression works.

**Interview talking point:**
> **Q:** How do you ensure a product spec actually constrains the implementation instead of becoming a wiki?
>
> **A:** Answer seven concrete questions that the downstream engineers must solve anyway: when does assessment trigger (0.60 score OR 5+ null turns), what does the user see (transparent 3–5 question format), how is score computed (0.7×current + 0.3×best), what are the gate thresholds (0.70 per topic for Phase 1–2, 0.75 for Phase 3), and crucially—what signal drives user_level in the adaptive prompt system (gate position, not score average). Every rule is implementable; every rule is testable.

**What happened and why:**
- Created `docs/scoring-model.md` with 7 concrete rules that answer the questions downstream commits must solve
- This is the contract: Nova's assessment engine must conform to the trigger conditions and user-visible behavior specified in the doc; Rex's profile scoring must conform to the formula and gate definitions
- User-level mapping decision was critical: discovered that current `get_mastery_level()` incorrectly uses score average instead of gate state; a user at Phase 1 with 0.70 score would be labeled "advanced" when they should be "beginner" — this doc forces C24/C25 to fix it
- The spec also surfaced three immediate codebase discrepancies that C24/C25 must resolve: deprecated slugs still in VALID_MODULE_SLUGS, `compute_topic_scores` using wrong delta formula, and `get_mastery_level` using wrong signal

**Reasoning & discovery:**
1. The problem: Nova and Rex were scheduled back-to-back with no shared understanding of the scoring/assessment contract. Each could implement differently. The gate thresholds alone weren't enough—we needed to define trigger conditions, user-visible behavior, and which signal drives adaptive prompt routing
2. What was ruled out: a shared Slack doc or a verbal agreement—both disappear. This needed to be canonical, version-controlled, and specific enough that a code reviewer could spot a violation
3. What clinched the solution: Mira ran through the system end-to-end and asked "what if a user scores 0.60, defers assessment, then returns 2 weeks later"—that forced us to clarify: no score decay (0.7/0.3 formula handles it), assessment deferral allowed once per topic per session, and the gate state (not score average) drives adaptive prompting. Those answers are now in the doc; C24 and C25 can't miss them

**Design pattern:**
| Contract-Driven Implementation | What it means here | Why it was chosen |
|---|---|---|
| Product spec as executable constraint | Each scoring rule is a testable assertion; implementation violations are code review catches, not post-ship bugs | Two engineers (Nova, Rex) building interdependent systems need a shared grammar. The spec is that grammar |
| Specification by concrete example | Every rule includes a worked example (e.g., "score delta: 0.7×0.75 + 0.3×0.65 = 0.72") | Formulas are ambiguous; examples are not. A reviewer can check implementation against the worked examples |

**Files touched:**
- `docs/scoring-model.md` — new: 7-question canonical spec for C24/C25
- `DECISIONS.md` — updated: 5 new entries for C23 (user-level mapping, no decay rationale, trigger conditions, gate semantics, deferral behavior)
- `DECISIONS_INDEX.md` — updated: added entries 60–64
- `GLOSSARY.md` — updated: added Assessment Session, Readiness Score Threshold, Assessment Deferral

**Handoff to Commit 24 (Nova):**
Commit 24's assessment engine must conform to three rules from the spec: (1) trigger when `topic_score >= 0.60 OR count_null_scores >= 5`, (2) deliver assessment transparently (user sees start announcement, 3–5 questions, summary), (3) one deferral allowed per topic per session. The verdict vocabulary in gates.md is canonical: `correct`, `partial`, `incorrect`. Any other value from the LLM evaluator is an error. `get_mastery_level()` must be rewritten to map user_level from gate state (Phase 1/2/3/4/5 → novice/beginner/intermediate/advanced/expert), not from score average.

---

**Commit 25 — `profile-scoring-rewrite`** · 2026-05-12 · Rex · `architectural`

> **In one sentence:** Rewrote profile scoring engine to implement the spaced-repetition formula (0.7×current + 0.3×best) and gate-driven mastery levels; added session history tracking to the profile row and idempotent DB migration for the new 8-slug topic set.

**Interview talking point:**
> **Q:** How do you ensure a scoring formula stays correct under uncertainty (unknown best session score, newly added topics)?
>
> **A:** Three invariants: (1) use `None` for unassessed topics, not 0.0—gate checks explicitly exclude None, so an unassessed topic cannot pass a gate by accident; (2) store session history in the profile row itself (flat list per topic), not a separate table—keeps scoring O(1) and crash-safe; (3) cumulative phase gates (expert requires p1 AND p2 AND p3)—checking only p3 would allow a corrupt DB state where Phase 3 passes without Phase 1 ever attempted. Pre-computed gate bools checked in chain is the correctness invariant.

**What happened and why:**
- Rewrote `src/app/profile/scoring.py`: implemented spaced-repetition formula `0.7×current_session_score + 0.3×best_prior_session_score`; first session uses just current score. Session score is the mean of per-question scores from a completed assessment (min 3 questions)
- Rewrote `get_mastery_level()` to read user_level from phase gate state (novice/beginner/intermediate/advanced/expert), not score average. This fixes the semantic bug discovered in C23: a user at Phase 1 with 0.70 score is "beginner" (passed p1 gate), not "advanced"
- Added `session_history TEXT` column to `user_profiles` table; `_deserialize_row` now reconstructs it as `dict[str, list[float]]`. Session scores are absolute (0.0–1.0), not deltas
- Wrote `migrate_topic_slugs()`: idempotent startup migration from old 6-slug set to new 8-slug set. Sentinel check: if `rag_pipeline_architecture` key exists in a row's `topic_scores`, that row was already migrated. Old `rag_fundamentals` renamed to `rag_pipeline_architecture`; `langchain` discarded; 4 new slugs initialized to `None` (not 0.0). Crash-safe: rows migrated before crash are skipped on resume
- Updated `compute_topic_scores` signature: removed `interaction_count`, now 2 args. Returns `TopicScoreUpdate` TypedDict with 5 fields: `topic_scores`, `session_history`, `strengths`, `gaps`, `mastery_level`
- Fixed caller in `src/agents/nodes/update_profile.py`: updated call signature and added `session_history` to the profile update
- Fixed two pre-existing test bugs found during Commit 25 test run: (1) `test_agent_state.py` had stale slug fixtures (`rag_fundamentals` and `langchain`); corrected to new slugs and fixed Pydantic model assertions from attribute access to dict `in`/`==`; (2) `test_chat_route.py` missing `metadata: {"langgraph_node": "generate"}` in `_make_chunk_event`, a regression from C18

**Reasoning & discovery:**
1. The formula problem: averaging all session deltas over time produces score inflation and no recovery path (a 0.4 session drags the average down permanently). The spaced-repetition formula `0.7×current + 0.3×best` gives recent sessions weight while ensuring best performance is never forgotten. The 70/30 split is standard in SRS systems; it prioritizes current understanding while protecting against flukes
2. What was ruled out: storing session events in a separate DB table (requires join-and-aggregate on every scoring call, O(n) instead of O(1)); using 0.0 for unassessed topics (0.0 === falsy, breaks gate checks; None is explicit and unambiguous)
3. What clinched the migration strategy: the application may be restarted during migration (crash during lifespan). A row-by-row sentinel key (`rag_pipeline_architecture` presence) proves which rows were migrated. No migration flag table, no ALTER TABLE—just a conditional rename per row. If the app restarts after row 50 is done, rows 1–50 are skipped, rows 51+ are processed on resume. This is crash-safe without a transaction log

**Design pattern:**
| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Spaced Repetition Formula (SRS) | Topic score = 0.7 × current_session + 0.3 × best_prior. First session: score = current_session | Standard in learning systems; weights recent understanding while protecting best performance. The 70/30 split gives primacy to current knowledge without forgetting prior mastery |
| Cumulative State Machine (gates) | expert = p1_passed AND p2_passed AND p3_passed (not independent). Checking only p3 allows state corruption | Mastery layers build on each other. Checking only the final phase permits a DB state where Phase 3 passed without Phase 1 ever attempted—a nonsensical outcome. Chaining all three bools prevents this |
| Row-Level Sentinel (migration) | `rag_pipeline_architecture` presence in topic_scores dict proves the row was migrated | Crash-safe without a migration flag table or ALTER TABLE. If the app restarts mid-migration, rows migrated so far are skipped; new rows resume. Rows can be safely re-processed (idempotent rename) |

**The key change:**
```python
# src/app/profile/scoring.py — spaced-repetition formula
# Before:
topic_score = mean([all_session_scores_ever])

# After:
if not session_history[topic_slug]:
    topic_score = current_session_score
else:
    topic_score = 0.7 * current_session_score + 0.3 * max(session_history[topic_slug])
```

```python
# src/app/profile/db.py — migration sentinel
# Before: no session_history, fixed 6-slug set
# After:
migrated = 'rag_pipeline_architecture' in row['topic_scores']
if not migrated:
    # rename rag_fundamentals → rag_pipeline_architecture
    # add 4 new slugs at None
    # save idempotently
```

**Files touched:**
- `src/app/profile/scoring.py` — full rewrite: spaced-repetition formula, gate-driven mastery levels, TopicScoreUpdate contract
- `src/app/profile/db.py` — session_history column added, migration function `migrate_topic_slugs()`, deserializer updated
- `src/app/main.py` — lifespan wired to call `migrate_topic_slugs()` after profile DB init
- `src/agents/nodes/update_profile.py` — `compute_topic_scores` call signature fixed (2 args), session_history passed to profile update
- `tests/test_scoring.py` — full rewrite (52 tests: schema, formulas, null/zero distinction, mastery levels, purity, clamping, strengths/gaps, history tracking)
- `tests/test_agent_state.py` — slug fixtures updated, Pydantic model assertions corrected
- `tests/test_chat_route.py` — metadata field added to `_make_chunk_event`

**Test coverage:** 264/264 PASS

---

**Commit 26 — `ui-foundation`** · 2026-05-17 · Aria · `architectural | new feature`

> **In one sentence:** Established the visual foundation for all three UI pages — CSS palette tokens, Inter font, glass-morphism auth cards, and gradient CTA button — surfacing two non-obvious constraints: NiceGUI's per-page HTML isolation and Quasar's post-render style override.

**Interview talking point:**
> **Q:** What surprised you most about styling a NiceGUI application, and how did you work around it?
>
> **A:** Two things. First, NiceGUI renders each `@ui.page` route as a completely independent HTML document — any `add_head_html()` call in one page function is invisible to every other route. That means global font or CSS injection has to be repeated in each page function, not done once at module level. Second, Quasar (the component library NiceGUI uses) re-applies its own `background` style to buttons after the initial render, wiping any inline style you set. The immediate fix is `!important`; the cleaner fix is a Quasar CSS variable override, which we deferred to the C27–C29 component pass.

**What happened and why:**
- Added the Inter font (`<link>` from Google Fonts CDN) inside `add_head_html()` in all three page functions — `login_page`, `register_page`, and `index` — because each route is a fresh HTML document with its own `<head>`
- Defined CSS palette tokens (sky, indigo, slate, emerald, amber, red) as `:root` CSS custom properties inside a `<style>` block in `index()` only; auth pages still use hardcoded hex values because no C26 component consumes tokens there
- Redesigned auth pages with a radial gradient body background and a glass-morphism card (`backdrop-filter:blur(8px)` + semi-transparent `rgba(30,41,59,0.8)` surface), establishing the visual register the rest of the UI must match
- Added an inline SVG logo mark via `ui.html()` and styled the CTA button with a sky→indigo gradient; `!important` was required to prevent Quasar from overwriting the gradient on render
- Body style in `index()` updated to include `font-family:'Inter',system-ui` as the application-wide type stack

**Design pattern:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Per-page head injection | `add_head_html()` called independently in each `@ui.page` function | NiceGUI serves each route as a separate HTML document; there is no shared `<head>` across routes. A single top-level injection call does nothing for other routes |
| Style/link separation | Font `<link>` tags in one `add_head_html()` call; CSS in a second `<style>` block | Mixing `<link>` elements inside a `<style>` block is invalid HTML and silently fails in most browsers |
| `!important` override (debt marker) | CTA button gradient marked `!important` to survive Quasar's post-render style pass | Quasar's button component re-applies its own background after the DOM is ready. `!important` wins the cascade; a Quasar CSS variable override is the clean alternative and is deferred to C27–C29 |

**Reasoning & discovery:**
1. The font was injected once in `index()` and tested — login and register pages rendered without Inter. The cause: NiceGUI's page router returns a complete HTML document per route, not a shared SPA shell. Each page function is the entire document for that URL.
2. The `<link>` tag was initially placed inside the same `<style>` block as the CSS palette. The font loaded inconsistently. Separating link and style into two `add_head_html()` calls resolved it — `<link>` inside `<style>` is not valid HTML.
3. The CTA button gradient disappeared after the initial paint. Chrome DevTools showed Quasar's component JS writing `background: var(--q-primary)` to the element after render, clobbering the inline gradient. `!important` on the gradient declaration wins the specificity battle; it is logged as a known debt item for the component-styling pass.

**The key change:**
```python
# src/app/ui.py — per-page font injection pattern
# Wrong: injecting only in index() leaves auth pages without the font
@ui.page('/login')
async def login_page():
    # font link NOT here → login renders in system-ui, not Inter
    ...

# Correct: each page function injects its own <link> tags
@ui.page('/login')
async def login_page():
    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
    )
    ...
```

**Google Fonts CDN trade-off:**
The font is loaded from Google's CDN (`fonts.googleapis.com`). This leaks each visitor's IP address to Google on first load (CWE-829: inclusion of functionality from untrusted control sphere). Sage flagged this as LOW severity — accepted for portfolio context. The hardened alternative is self-hosting the Inter font files in `src/app/static/` and serving them locally, which eliminates the third-party request entirely.

**Files touched:**
- `src/app/ui.py` — Inter font injection (all 3 pages), CSS palette tokens in `index()`, glass-morphism auth card styles, inline SVG logo, gradient CTA button with `!important` override, body font-family set in `index()`

---

**Commit 27 — `ui-header`** · 2026-05-17 · Aria · `new feature`

> **In one sentence:** SVG brand mark with CSS gradient text and pill-style email badge; corrected SVG gradient rendering technique and fixed CWE-79 XSS in user-supplied badge label.

**Interview talking point:**
> **Q:** What's the difference between SVG text gradients and CSS gradient text, and when does each work?
>
> **A:** SVG `<text>` elements cannot reliably fill with gradients via `fill="url(#gradient-id)"` — support is inconsistent across browsers. The robust technique is CSS gradient text via `background-clip: text; -webkit-text-fill-color: transparent`, but it requires a `color` fallback for non-supporting browsers. SVG `<path>` strokes with `stroke="url(#id)"` are the reliable alternative if you need pure SVG. This came from a retry pass where the initial approach failed silently — the text rendered but the gradient did not.

**What happened and why:**
- Built the page header with a brand mark (SVG `<path>` stroke with namespaced gradient) and an email badge
- Pass 1 attempted SVG `<text>` element with `fill="url(#rag-brand-icon-grad)"` (fill from gradient). This failed silently — the gradient did not render in Chrome or Firefox. SVG text gradient fills are browser-dependent and unreliable
- Pass 2 rebuilt with two rendering techniques in parallel: CSS gradient text for the brand name (`-webkit-background-clip: text; -webkit-text-fill-color: transparent`) and SVG `<path>` strokes with `stroke="url(#id)"` for the icon mark (both reliable across modern browsers)
- The email badge displays the user's registered email or a fallback badge with the last 8 characters of their user ID. Initial code used `ui.html(f'<span style="...">{label}</span>')` where `label` is user-supplied (email from registration). This is CWE-79 — stored XSS, self-XSS scope (NiceGUI sessions are per-user; one user's email does not render in another's session), but a security issue nonetheless. `EmailStr` validation at registration partially defends but only validates format, not HTML encoding
- Fixed by replacing `ui.html()` with `ui.label(label).style(...)` — NiceGUI's `label` widget HTML-escapes content before DOM insertion, preventing injection

**Reasoning & discovery:**
1. The SVG `<text>` gradient was researched and expected to work. Testing showed it silent-failed — no console errors, just no color. Debugging revealed the W3C SVG spec allows gradient fills on text but browser compliance is inconsistent (IE/Edge support it, Chrome/Firefox do not). The robust solution is CSS gradient text, which has universal modern support with explicit fallback color
2. The email badge vulnerability: `ui.html()` exists for cases where HTML markup is intentional (e.g., structured content). When the content is user-supplied, this is a code smell. The fix checks the NiceGUI API for a safer widget — `label` is designed for exactly this use case: text content that needs styling but not HTML markup
3. What clinched the CSS gradient approach: the header must use the same brand colors and gradient direction as the CTA button (C26). CSS gradient text is less flexible than SVG gradients (no radial gradients on text) but it aligns with the design system and survives a browser restart without re-rendering SVG paths

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| CSS Gradient Text with Fallback | `color: #e2e8f0; background: linear-gradient(...); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;` | The `color` property serves as a fallback for non-supporting browsers. Without it, text is invisible in browsers that don't support `background-clip: text`. The `-webkit-` prefix is required for Chrome/Safari; `background-clip: text` (no prefix) is the standard and future-proof |
| SVG Path Strokes over Text Fills | `<path stroke="url(#gradient)"` instead of `<text fill="url(#gradient)"` | SVG text gradient fills are W3C-specified but browser support varies. Path strokes with gradients are universally supported and are the reliable choice for gradient rendering in SVG |
| Content-Aware Widget Selection | `ui.label()` instead of `ui.html()` for user-supplied content | NiceGUI's `label` widget HTML-escapes content; `html()` does not. When content is user-supplied, the escaping widget is mandatory. This prevents CWE-79 injection and is the correct abstraction |

**The key change:**

```python
# src/app/ui.py — SVG `<text>` gradient (Pass 1, rejected)
# Before: failed silently in Chrome/Firefox
ui.html(f'<svg><text fill="url(#rag-brand-icon-grad)">RAG</text></svg>')

# After: CSS gradient text with fallback color + SVG path stroke
ui.html(f'''
<style>
  .rag-brand-name {{
    color: #e2e8f0;          /* fallback for non-supporting browsers */
    background: linear-gradient(135deg, #0ea5e9 0%, #4f46e5 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
</style>
<span class="rag-brand-name">RAG</span>
''')
```

```python
# src/app/ui.py — Email badge (XSS vulnerability fix)
# Before: CWE-79 via ui.html() with user-supplied email
label = app.storage.user.get("email") or f"id …{uid[-8:]}"
ui.html(f'<span style="...">{label}</span>')  # NOT SAFE

# After: ui.label() HTML-escapes before DOM insertion
label = app.storage.user.get("email") or f"id …{uid[-8:]}"
ui.label(label).style('...color: #cbd5e1; background: ...')
```

**Security consequence:**
CWE-79 severity is reduced from **potential stored XSS** to **eliminated** by using the escaping widget. The email field is registered with `EmailStr` validation, which blocks most injection attempts at registration time, but validation is not sufficient—the rendering layer must also escape. By moving to `ui.label()`, we defense-in-depth: validation at registration + escaping at render.

**Files touched:**
- `src/app/ui.py` — brand mark SVG with path stroke + CSS gradient text fallback, email badge using `ui.label()` with escaping, inline `<style>` block for gradient text fallback color, namespaced gradient id `#rag-brand-icon-grad`

---

**Commit 28 — `ui-chat`** · 2026-05-17 · Aria · `refactor`

> **In one sentence:** Chat area style redesign: gradient user bubbles, blue left-border accent on AI cards, indigo glow on Knowledge Check cards, indigo thinking indicator — visual continuity with the auth page aesthetic.

---

**Commit 29 — `ui-sidebar-admin`** · 2026-05-17 · Aria · `refactor`

> **In one sentence:** Profile sidebar and admin dashboard visual polish: color-coded mastery chips, topic score pills with progress bars, red-tinted gap badges, stat card gradients, health status chips — CSS-only redesign via `<style>` block overrides and semantic `ui.label()` classes.

---

**Commit 30 — `ui-landing-page`** · 2026-05-19 · Aria · `new feature`

> **In one sentence:** Static marketing landing page with full-viewport particle canvas animation and brand identity — unauthenticated users now see `/landing` instead of redirecting directly to `/login`.

**Interview talking point:**

> **Q:** How do you handle layout overrides in NiceGUI when you need full-viewport control?
>
> **A:** NiceGUI's `.nicegui-content` wrapper sets `display: flex; align-items: center;` by default, which forces child elements into a flex context. When you need full-width layout (like a landing page), you have to override the wrapper styles with both CSS and DOM queries to prevent load-order edge cases. The fix applies to both the head styles and the runtime element, overriding `display: flex` to `display: block`, removing padding and margins, and unsetting alignment properties.

**What happened and why:**

- Built an 8-section marketing landing page (`/landing`) as a static NiceGUI page using `ui.html()` for the full-viewport layout and particle canvas animation
- Changed unauthenticated redirect logic from `/login` to `/landing` in the `index()` route — users now see the marketing page first
- Discovered that NiceGUI's default `.nicegui-content` wrapper uses flex layout with `align-items: center`, which was centering the entire landing page and preventing full-width CSS from working
- Fixed by applying two operations: injected a CSS override block into the page head, and used `ui.query()` to modify the wrapper's inline styles at runtime. Both operations are required — CSS alone doesn't guarantee load ordering, and inline styles can be overridden by later CSS imports
- Applied CSS namespace prefix `rag-landing-` to all landing page styles to prevent collision with NiceGUI's Quasar `.q-*` classes and other pages' styles
- Landing page uses synchronous `def`, not `async def` — no authentication, no API calls, no database access, so there is no reason for an async context

**Design pattern / architectural principle:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| NiceGUI Full-Bleed Layout Override | CSS `display: block !important` + `ui.query()` inline style modification on `.nicegui-content` | NiceGUI defaults to flex centering. Without overriding both the CSS rules and the element's inline styles, full-viewport layout fails. `!important` is used because it reliably wins the cascade and prevents later stylesheets from re-flexing the layout |
| CSS Namespace Isolation | All landing page styles use `rag-landing-` prefix (`.rag-landing-section`, `.rag-landing-canvas`, etc.) | NiceGUI does not isolate CSS between pages — styles persist across navigation. Prefixing prevents accidental collision with Quasar `.q-*` utility classes or styles from other pages in the same browser session |
| Static Page as Synchronous Function | `def landing_page():` not `async def landing_page():` | No I/O operations means no `await` is needed. Using `async` here is cargo-cult — it adds overhead for zero benefit. The page is purely presentational |

**Reasoning & discovery:**

1. The landing page needed full viewport width with a particle canvas animation background. The canvas requires `<canvas>` positioned absolutely over content. But when the page loaded, the entire layout was centered in the viewport instead of spanning it. Debugging revealed NiceGUI's `.nicegui-content` container was a flex container with `align-items: center` applied
2. The fix required both CSS and DOM manipulation. CSS alone wasn't sufficient because later stylesheets can override the rule. The `ui.query(".nicegui-content").style(...)` call applies inline styles that reliably persist. Both together handle edge cases where CSS loads after the query runs, or the element is recreated during navigation
3. What clinched the namespace prefix: NiceGUI's architecture re-uses the same DOM containers across pages. A CSS rule like `.section { padding: 1rem }` injected on the landing page will affect `.section` elements on other pages if they exist. The `rag-landing-` namespace is an explicit contract: "these styles apply only to landing page content." When another page is built later, it can use `rag-dashboard-`, `rag-profile-`, etc., and there is zero collision risk

**Viktor's deferred block:**

Viktor flagged a missing DOM guard in the particle canvas animation loop: the `requestAnimationFrame(draw)` call does not check whether the canvas element still exists in the DOM before scheduling the next frame. This creates a memory leak if the page is navigated away during animation. Per the no-gate-fix-passes rule, the fix was deferred to Commit 30.5 (one-line guard: `if (!document.contains(canvas)) return;` at the start of the `draw` function). This is functionally low-risk in practice because all landing page navigation uses standard `<a>` anchor tags which trigger a full page reload (destroying the JS context), but it is a real best-practice gap that should not ship without the guard.

**The key change:**

```python
# src/app/ui.py — NiceGUI layout override for landing page
# Before: .nicegui-content defaults to flex with center alignment

# After: CSS override + DOM query
ui.add_head_html('''<style>
.nicegui-content { display: block !important; padding: 0 !important; max-width: 100% !important; width: 100% !important; margin: 0 !important; align-items: unset !important; justify-content: unset !important; }
.q-page { padding: 0 !important; }
.q-page-container { padding: 0 !important; width: 100% !important; max-width: 100% !important; }
</style>''')
ui.query(".nicegui-content").style("display: block !important; padding: 0 !important; max-width: 100% !important; width: 100% !important; margin: 0 !important; align-items: unset !important; justify-content: unset !important")
```

```python
# src/app/ui.py — Unauthenticated redirect changed to landing page
# Before: redirect to login immediately
@ui.page("/")
async def index():
    if not app.storage.user.get("authenticated"):
        ui.navigate("/login")
    # ...

# After: redirect to landing page for first-time visitors
@ui.page("/")
async def index():
    if not app.storage.user.get("authenticated"):
        ui.navigate("/landing")
    # ...
```

**Files touched:**
- `src/app/ui.py` — new `@ui.page("/landing")` 8-section static marketing page with namespaced CSS (`rag-landing-*`), particle canvas animation with JS, full-viewport layout override, changed unauthenticated redirect from `/login` to `/landing`

---

**Commit 30.5 — `ui-landing-raf-guard`** · 2026-05-19 · Claude · `bug fix`

> **In one sentence:** Added `if (!document.contains(canvas)) { return; }` before `requestAnimationFrame(draw)` in the particle canvas animation to stop the rAF loop from firing on a detached DOM element after NiceGUI full-page navigation.

**Files touched:**
- `src/app/ui.py` — one-line rAF guard added inside `draw()` in `landing_page()` particle canvas JS block

---

**Commit 31 — `ui-auth-pages`** · 2026-05-19 · Aria · `new feature`

> **In one sentence:** Redesigned login and register page layouts to match Auth.jsx UI kit — vertical brand column with SVG logo, visible input labels, corrected focus ring color, and reordered register form fields.

---

**Commit 32 — `ui-chat-shell`** · 2026-05-19 · Aria · `update`

> **In one sentence:** Unified chat page styling and labels across all UI kit components (ChatShell, KnowledgeProfile, Composer, Bubbles); refactored composer layout from row to column wrapper.

---

**Commit 33 — `question-bank-mcq`** · 2026-05-19 · Lara · `new feature`

> **In one sentence:** Created MCQ (multiple-choice question) banks for all 8 RAG curriculum topics — 40 questions total (5 per topic) with deterministic binary scoring for phase-gate advancement.

**Interview talking point:**
> **Q:** How do you gate learner progression through a multi-topic curriculum without introducing evaluator variance or requiring an LLM grader?
>
> **A:** MCQ answer-key comparison is deterministic — no rubric ambiguity, no evaluator variance, no LLM cost. Open-ended questions stay as in-session learning; MCQs provide the binary signal for gating. Same `session_score` formula applies to both, so curriculum flow treats them identically.

**What happened and why:**
- Created MCQ question banks in `knowledge-base/curriculum/questions/mcq/[slug].md` for all 8 topics: 2 beginner, 2 intermediate, 1 advanced per topic. This satisfies `min_questions_per_session=3` from phase gates while keeping assessments concise.
- Created `knowledge-base/curriculum/mcq-format.md` schema document defining field constraints, answer-key format, and scoring rules. This makes the distinction from open-ended questions explicit and prevents format drift.
- Appended binary scoring addendum to `knowledge-base/curriculum/gates.md`. MCQ scores (0.0 or 1.0) feed the same `session_score = mean(question_scores)` formula as open-ended rubric scores, so progression logic doesn't need to distinguish between question types.
- Separated MCQ file tree from open-ended questions. Nova's Commit 35 (mcq-assessment-engine) will read only from `questions/mcq/` to avoid format confusion and ensure engine input is always well-formed.

**Reasoning & discovery:**
1. Phase gate advancement requires a deterministic signal — no ambiguity, no variance between assessments, no evaluator drift. Open-ended rubrics need LLM evaluation; MCQ answer keys don't.
2. Parallel file trees (open-ended vs. MCQ) make the format distinction structural rather than documenting a convention. Prevents accidental mixing and gives Nova a clear read path for Commit 35.
3. 5 questions per topic (2+2+1) balances gate rigor — must demonstrate beginner and intermediate knowledge before synthesis — with session time constraints. The question bank can be rotated in future iterations without changing gate logic.

**Files touched:**
- `knowledge-base/curriculum/questions/mcq/rag-fundamentals.md` — 5 MCQ bank for Topic 1
- `knowledge-base/curriculum/questions/mcq/retrieval-systems.md` — 5 MCQ bank for Topic 2
- `knowledge-base/curriculum/questions/mcq/embeddings.md` — 5 MCQ bank for Topic 3
- `knowledge-base/curriculum/questions/mcq/vector-search.md` — 5 MCQ bank for Topic 4
- `knowledge-base/curriculum/questions/mcq/reranking.md` — 5 MCQ bank for Topic 5
- `knowledge-base/curriculum/questions/mcq/llm-integration.md` — 5 MCQ bank for Topic 6
- `knowledge-base/curriculum/questions/mcq/evaluation.md` — 5 MCQ bank for Topic 7
- `knowledge-base/curriculum/questions/mcq/production-rag.md` — 5 MCQ bank for Topic 8
- `knowledge-base/curriculum/mcq-format.md` — new; defines MCQ schema, field constraints, and scoring rules
- `knowledge-base/curriculum/gates.md` — appended binary scoring rules for MCQ advancement gating

---

**Commit 34 — phase-gate-enforcement** · 2026-05-20 · Nova · `new feature | architectural`

> **In one sentence:** Assessment question selection is now gated to the user's current curriculum phase — novice and beginner users receive only Phase 1 questions, intermediate only Phase 2, advanced only Phase 3, and experts cycle through all phases in canonical order.

**Interview talking point:**
> **Q:** How does the adaptive RAG tutor prevent a beginner from being assessed on advanced topics before mastering the fundamentals?
>
> **A:** `_select_test_slug()` now resolves an `eligible` frozenset from a `_LEVEL_TO_PHASE` dict keyed on `user_level` before checking gaps or canonical ordering. A Phase 3 gap for a beginner is skipped entirely — the function only considers slugs that fall inside the user's current phase. The phase topic sets were already defined in `scoring.py`; this commit made them public so the assess node could import and apply them.

**What happened and why:**
- `_PHASE_1_TOPICS`, `_PHASE_2_TOPICS`, `_PHASE_3_TOPICS` in `scoring.py` were private (underscore-prefixed) — accessible only within the scoring module. Made them public so `assess.py` could import them without duplicating the curriculum definition.
- Added `_LEVEL_TO_PHASE: dict[str, frozenset[str]]` at module level in `assess.py` mapping all 5 `user_level` values to their eligible topic set. Default fallback is `PHASE_1_TOPICS` — unknown levels are treated as the most restrictive gate.
- Rewrote `_select_test_slug()` to resolve `eligible` from `_LEVEL_TO_PHASE` before either gap or canonical checks. Both checks now filter by `eligible` first, then `VALID_MODULE_SLUGS`.
- `_ORDERED_SLUGS` promoted from a local variable (recreated per call) to a module-level constant — correct home for an immutable list used as a fallback ordering.
- One stale test (`test_test_mode_uses_identified_gap_slug`) used a Phase 2 gap slug (`vector_databases`) for a novice user. Phase gate correctly skips this — test updated to use a Phase 1 gap.

**Reasoning & discovery:**
1. The phase topic constants already existed in `scoring.py` — the scoring engine had always known which topics belong to which phase. The private naming was an artificial barrier. Making them public was the minimal change that gave `assess.py` what it needed without duplicating the curriculum definition.
2. Dict lookup over if/elif: a dict makes coverage explicit (all 5 keys visible at a glance), is O(1), and the `.get(user_level, PHASE_1_TOPICS)` fallback is conservative — unknown levels default to the most restrictive gate rather than silently passing through.
3. Expert users get `_ALL_TOPICS` (all 8 slugs), but `_ORDERED_SLUGS` still determines which slug comes first — Phase 1 leads. This means experts cycle through the same structured progression rather than getting random access.

**The key change:**

```python
# src/agents/nodes/assess.py — before
def _select_test_slug(state: AgentState) -> str | None:
    gaps: list[str] = state.get("identified_gaps") or []
    for slug in gaps:
        if slug in VALID_MODULE_SLUGS:          # no phase check
            return slug
    _ORDERED_SLUGS = [...]                      # local variable, recreated per call
    for slug in _ORDERED_SLUGS:
        if slug in VALID_MODULE_SLUGS:          # no phase check
            return slug
    return None

# src/agents/nodes/assess.py — after
_LEVEL_TO_PHASE: dict[str, frozenset[str]] = {
    "novice":       PHASE_1_TOPICS,
    "beginner":     PHASE_1_TOPICS,
    "intermediate": PHASE_2_TOPICS,
    "advanced":     PHASE_3_TOPICS,
    "expert":       _ALL_TOPICS,
}

def _select_test_slug(state: AgentState) -> str | None:
    user_level: str = state.get("user_level") or "novice"
    eligible: frozenset[str] = _LEVEL_TO_PHASE.get(user_level, PHASE_1_TOPICS)
    gaps: list[str] = state.get("identified_gaps") or []
    for slug in gaps:
        if slug in eligible and slug in VALID_MODULE_SLUGS:   # phase-gated
            return slug
    for slug in _ORDERED_SLUGS:
        if slug in eligible and slug in VALID_MODULE_SLUGS:   # phase-gated
            return slug
    return None
```

**Design pattern:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Dict dispatch with conservative fallback | `_LEVEL_TO_PHASE.get(user_level, PHASE_1_TOPICS)` | All 5 levels explicit; unknown levels default to most restrictive gate; no if/elif branching needed |
| Public module API for cross-domain constants | `_PHASE_X_TOPICS` → `PHASE_X_TOPICS` | Scoring module is the canonical source; assess node consumes without duplication |

**Files touched:**
- `src/app/profile/scoring.py` — made `PHASE_1/2/3_TOPICS` public; updated 4 internal references
- `src/agents/nodes/assess.py` — added `_LEVEL_TO_PHASE`, `_ALL_TOPICS`, `_ORDERED_SLUGS` at module scope; rewrote `_select_test_slug`
- `tests/test_assess_node.py` — added `TestPhaseGateSlugSelection` (8 tests); updated 1 stale test

---

### Commit 35 — `mcq-assessment-engine` · 2026-05-20

**What changed:** Replaced LLM scoring for multiple-choice questions with deterministic regex-based evaluation that extracts A–D answers from freeform user input.

**Why it matters:** MCQs are closed-form problems with known correct answers — LLM scoring adds latency and variance for zero benefit. This is the foundation for the assessment UI (Commit 37) that needs to know at render time whether to show multiple-choice buttons or a text input.

**Key design decision:** Word-boundary regex `\b([A-Da-d])\b` extracts the first standalone letter from user input (handles "B", "b", "Option B is correct", "I think B"). This respects natural language without being hostile to it — no need to force users into a strict format.

**Code reference:**
```python
# from src/agents/nodes/assess.py

def _evaluate_mcq_answer(user_message: str, correct_answer: str) -> float:
    """Deterministic binary MCQ evaluator — no LLM call."""
    match = re.search(r"\b([A-Da-d])\b", user_message.strip())
    if match and match.group(1).upper() == correct_answer.upper():
        return 1.0
    return 0.0

# In _evaluate_answer, branching on is_mcq flag:
if state.get("is_mcq"):
    correct = state.get("pending_mcq_correct_answer")
    if correct is None:
        logger.error("assess_node: is_mcq=True but pending_mcq_correct_answer is None; ...")
        return _build_eval_result(..., assessment_error=True)
    user_msg = (state.get("messages") or [])[-1].content or ""
    score = _evaluate_mcq_answer(user_msg, correct)
```

**Gotcha:** 7 existing tests that globally patched `pathlib.Path.read_text` broke when `_select_test_question` started calling `_load_mcq_question` — which expects MCQ-formatted content from disk. Fix: patch `_load_mcq_question` directly in tests that only care about state transitions, not actual question content. Tests verifying the full evaluate path (with real question files) should not mock `_load_mcq_question`.

**Handoff:** Aria (Commit 37) consumes `is_mcq` from `ChatResponse` to decide whether to render A–D buttons or plain text input. The flag flows: `AgentState.is_mcq` → `build_chat_response()` → `ChatResponse.is_mcq` → SSE `done` event payload. Aria reads `done_data["is_mcq"]` to set the render branch.

---

### Commit 36 — `onboarding-level-check` · 2026-05-20

**What changed:** Added three REST endpoints at `/api/onboarding/` (status check, MCQ diagnostic, placement completion) that determine a new user's starting curriculum phase before their first chat. Extracted the MCQ file loader into a shared `mcq_utils.py` module to prevent a circular import between the route layer and the agent layer.

**Why it matters:** Without onboarding placement every new user starts at novice regardless of prior knowledge. The diagnostic asks 3 questions from a topic appropriate to the self-reported level; scoring (2/3+ confirms, 1/3 drops one level, 0/3 drops two levels) gives a calibrated starting point rather than an arbitrary default.

**Key design decisions:**
1. **MCQ loader extracted to `mcq_utils.py`** — `onboarding.py` needs MCQ file access. Importing from `agents/nodes/assess.py` would create a route→agent circular import. The extracted module is pure file I/O with zero agent dependencies.
2. **Correct answers re-verified from source files on every `/complete` call** — no server-side session is stored between `/diagnostic` and `/complete`. Re-reading the files at scoring time prevents a client that modifies its request from receiving credit for answers it never fetched.
3. **`_drop_level()` floor via `max(0, idx - n)`** — scoring can never produce a level below novice regardless of how many levels a user drops.
4. **`asyncio.to_thread()` for all profile DB calls** — the profile DB uses synchronous SQLite; all calls inside async FastAPI handlers are wrapped to prevent event loop blocking.

**Code reference:**
```python
# src/app/api/routes/onboarding.py — placement scoring
correct_count = sum(
    1 for i, ans in enumerate(body.answers[:3])
    if ans.strip().upper() == load_mcq_question(slug, i)[1]
)
if correct_count >= 2:
    confirmed_level = body.level           # confirmed self-report
elif correct_count == 1:
    confirmed_level = _drop_level(body.level, 1)
else:
    confirmed_level = _drop_level(body.level, 2)
```

**Gotcha:** The test bootstrap `users` table was missing `is_admin INTEGER NOT NULL DEFAULT 0`. The real schema selects this column explicitly in `get_user_by_id`. The mismatch caused 500 errors (not 401) on all authenticated routes because the failure occurred inside the auth dependency after JWT decode — not before it.

**Files touched:**
- `src/agents/mcq_utils.py` — new: shared MCQ file loader extracted from `assess.py`
- `src/agents/nodes/assess.py` — removed inline loader; added import alias to `mcq_utils`
- `src/app/api/routes/onboarding.py` — new: three onboarding endpoints with JWT auth
- `src/app/main.py` — registered onboarding router
- `tests/test_onboarding.py` — new: 16 tests (status, diagnostic, complete)
- `tests/test_assess_node.py` — updated patch target to `agents.mcq_utils._MCQ_DIR`

**Handoff:** Aria (Commit 38) consumes the full API contract: `GET /api/onboarding/status → {needed: bool}`, `POST /api/onboarding/diagnostic → {questions: [{index, text}], slug}`, `POST /api/onboarding/complete → {confirmed_level, correct_count, message}`.

---

**Commit 37 — `mcq-chat-ui`** · 2026-05-20 · Aria (frontend) · `new feature`

> **In one sentence:** The chat UI now renders MCQ assessment questions as interactive A/B/C/D option buttons, replacing the text input when the backend signals an active knowledge check via SSE.

**Interview talking point:**
> **Q:** How did you implement a dynamic input toggle in NiceGUI when the server signals a different UI mode via SSE?
>
> **A:** The SSE `done` event includes an `is_mcq` boolean. When `is_mcq: true` arrives, `composer_row.set_visibility(False)` hides the text input and `mcq_panel.set_visibility(True)` shows the option buttons — both elements stay in the DOM the whole time. Clicking an option submits the letter and reverses the toggle. The non-obvious part: NiceGUI's `with` block nesting makes `nonlocal` fragile, so mutable single-element lists (`_mcq_active = [False]`) are used for closure-safe state mutation instead.

**What happened and why:**
- Added `mcq_panel` — 4 `ui.row()` elements with gradient letter badges and `ui.label()` option texts; sits alongside `composer_row` in the DOM and toggles visibility on MCQ signal.
- Refactored `send()` into `send_message(question: str)` + thin `send()` wrapper, so both text-input and MCQ button paths share one send function.
- Click handlers use default-arg capture (`lambda _e, _l=_captured`) to prevent the Python late-binding closure bug when wiring 4 buttons in a for-loop.
- All option texts use `ui.label()` and `set_text()` — never `ui.html(f-string)` — confirmed safe by Sage (PASS, no XSS vector).

**Reasoning & discovery:**
1. Option texts arrive in `test_question` as `A. text\nB. text...` lines; parsing requires extracting `^[A-D]\. ` prefix lines and stripping the 3-char prefix.
2. `nonlocal` was ruled out because NiceGUI `with` context manager nesting makes the enclosing scope boundary ambiguous at declaration time — the mutable list pattern is explicit and closure-safe.
3. Pre-built labels updated via `set_text()` (vs. clearing and re-adding elements) avoids NiceGUI DOM flicker when each MCQ question arrives.

**The key change:**
```python
# src/app/ui.py — MCQ state toggle on SSE done event
_mcq_active = [False]  # mutable list — closure-safe without nonlocal
if is_mcq and test_q:
    _opt_lines = [l for l in test_q.splitlines() if len(l) >= 3 and l[0] in "ABCD" and l[1] == "."]
    for _i, (_row_el, _lbl_el) in enumerate(mcq_btns):
        _lbl_el.set_text(_opt_lines[_i][3:].strip() if _i < len(_opt_lines) else "")
    _mcq_active[0] = True
    composer_row.set_visibility(False)
    mcq_panel.set_visibility(True)
```

**Design pattern:**
| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Signal-driven visibility toggle | `is_mcq` from SSE controls `composer_row` vs `mcq_panel` | Keeps rendering decision in the backend signal, not client-side text parsing |
| Mutable list closure | `_mcq_active = [False]` for shared state across callbacks | `nonlocal` is fragile inside NiceGUI's deeply nested `with` context blocks |
| Default-arg capture | `lambda _e, _l=_captured` in click handler loop | Prevents late-binding bug — each button captures its own letter at loop time |

**Files touched:**
- `src/app/ui.py` — MCQ state variables, panel construction, visibility toggle, `send_message()` refactor, click wiring

---

**Commit 38 — `progression-ui`** · 2026-05-20 · Aria (frontend) · `new feature | architectural`

**What changed:**
Two NiceGUI UI additions to `src/app/ui.py`:

1. **Onboarding wizard** — a 3-step `ui.dialog()` shown on first login (`GET /api/onboarding/status` returns `needed: true` when user has no topic scores). Step 1: self-report level (Beginner / Intermediate / Expert). Step 2: 3 diagnostic MCQs fetched from `/api/onboarding/diagnostic`, rendered using the same `.rag-mcq-row` button style from C37. Step 3: placement result with confirmed level, correct count, backend message, and phase topic list. Skippable at any step — skip calls `POST /api/onboarding/complete` with `skipped: true`, placing user at novice and closing the modal without showing Step 3.

2. **Phase progress panel** — replaces the module-by-module progress bar list in `profile_panel()` with a phase-aware display. Shows current phase label (e.g. "Phase 2 · Core RAG"), per-topic scores color-coded at three thresholds (≥0.70 → `#22c55e` green, 0.40–0.69 → `#f59e0b` amber, <0.40 → `#ef4444` red, unscored → "—" `#64748b` gray), and a dynamic advancement message per phase from `_ADVANCE_MSG`. Refreshes after every chat turn via the SSE done event (already wired in C37).

**Non-obvious patterns:**

```python
# ob_step_content is @ui.refreshable def (sync), not async.
# Async work is separated into _ob_select_level, _ob_select_answer, _ob_skip.
# Each handler mutates mutable-list state then calls ob_step_content.refresh().
# Same pattern as profile_panel (C19/C20): separate async fetching from sync rendering.

# _ob_finish references profile_panel, which is defined later in index().
# Safe because _ob_finish is only called at runtime (user click),
# not at definition time — profile_panel is in the same enclosing scope.

# _PHASE_LABELS, _PHASE_TOPICS, _ADVANCE_MSG at module level (not inside profile_panel)
# so sidebar refresh after each chat turn doesn't rebuild these dicts on every call.
```

**Files touched:**
- `src/app/ui.py` — module-level phase dicts, onboarding wizard, phase progress panel

---

### Commit 38.5 — knowledge-profile-ui

**What changed:** Replaced the flat topic-score list in `profile_panel()` with a two-tab sidebar (Current / Overview) matching `UI_Design/app/KnowledgeProfile.jsx`. Current tab shows active module, topic checklist with gradient checkmarks, and module progress bar. Overview tab shows all three modules with per-module progress bars and locked-state dimming.

**Key discoveries:**

**1. `ui.element("div")` required for precise CSS flex/grid control**

`ui.row()` and `ui.column()` render as Quasar `q-row`/`q-col` which inject gap and padding classes. These override inner `flex:1` and `width:100%` — progress bars and labels cannot stretch to full container width. Solution: replace all layout-critical wrappers with `ui.element("div")` and explicit inline `display:flex` styles.

```python
# Correct — plain div, no Quasar interference
with ui.element("div").style("display:flex; flex-direction:row; align-items:center; width:100%; gap:8px"):
    ui.label(topic_name).style("flex:1; ...")
    ui.element("div").style("flex:1; height:4px; ...")  # progress bar

# Wrong — q-row injects gap/padding that breaks flex:1
with ui.row().style("width:100%"):
    ui.label(topic_name).style("flex:1; ...")  # flex:1 doesn't stretch
```

**2. CSS `::after` pseudo-elements require injected stylesheet**

NiceGUI's `.style()` method sets inline CSS. Inline styles cannot define pseudo-elements. The gradient underline on the active tab (`.sb-tab.active::after`) must be in a CSS class rule injected via `ui.add_head_html()` in `index()`:

```python
ui.add_head_html("""<style>
.sb-tab { cursor:pointer; padding:6px 0; font-size:13px; color:#8b92a8; position:relative; }
.sb-tab.active { color:#fff; font-weight:600; }
.sb-tab.active::after { content:""; position:absolute; bottom:-2px; left:0; width:100%;
  height:2px; background:linear-gradient(90deg,#f97316,#ec4899,#8b5cf6); border-radius:1px; }
</style>""")
```

**3. SVG gradient defs injected once per page load**

`profile_panel()` is `@ui.refreshable` and fires after every chat turn. Defining `<linearGradient>` inline in each checkmark SVG would duplicate the `<defs>` block on every render. Define once in `index()` head; all icons reference by `id`:

```python
# In index() — once per page load
ui.add_head_html("""<svg style="display:none"><defs>
  <linearGradient id="tg" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="#f97316"/>
    <stop offset="50%" stop-color="#ec4899"/>
    <stop offset="100%" stop-color="#8b5cf6"/>
  </linearGradient>
</defs></svg>""")

# In profile_panel() — referenced cheaply
ui.html('<svg width="14" height="14"><path d="M2 7l4 4 6-6" stroke="url(#tg)" .../></svg>')
```

**4. Mastery whitelist before CSS class injection**

`mastery_level` comes from the API response. It is used in a CSS class name (`mc-{mastery}`) and in `ui.html()`. Whitelisted before use to prevent CSS class injection:

```python
mastery_raw = profile.get("mastery_level") or "novice"
mastery = mastery_raw if mastery_raw in {"novice", "beginner", "intermediate", "advanced", "expert"} else "novice"
ui.html(f'<span class="mastery-chip mc-{mastery}"><span class="dot"></span>{mastery.capitalize()}</span>')
```

**5. Mutable list for tab state in `@ui.refreshable`**

Same pattern as C37/C38: single-element mutable list allows the click handler to mutate tab state across the closure boundary:

```python
_tab_state = ["Current"]

@ui.refreshable
def profile_panel() -> None:
    active_tab = _tab_state[0]
    def _switch_tab(name: str) -> None:
        _tab_state[0] = name
        profile_panel.refresh()
```

**Files touched:**
- `src/app/ui.py` — two-tab profile_panel(), SVG defs + tab CSS injected in index()

---

**Commit 39 — scoring-correctness** · 2026-05-20 · Claude · `fix`

> **In one sentence:** Fixed three live scoring bugs—question modulo arithmetic, passive decay erasing earned scores, and missing session-count guardrails—discovered in learning flow audit.

**Interview talking point:**
> **Q:** Tell us about a time when you had to fix a scoring system where the bugs only showed up in production-like workflows, not unit tests.
>
> **A:** We had three bugs hidden in spaced-repetition scoring: a modulo-5 arithmetic error that caused question index collisions; a passive decay formula that was erasing high MCQ scores via low conversational signals; and no guardrail on minimum session questions. The learning flow audit caught all three at the same time. The interesting part was fixing the passive decay without breaking backward compatibility—we added an `is_passive: bool` flag that changes the formula from multiplicative (erases scores) to additive with a 0.3 ceiling (preserves earned work). The session guard used a `None` sentinel instead of a default value to avoid triggering early returns in code that didn't know about it yet.

**What happened and why:**
- Three bugs in `assess.py` and `scoring.py` surfaced in a Mira/Nova learning flow audit—each silent failure that broke scoring without raising an exception.
- Bug 1 (`assess.py`): MCQ files have exactly 5 questions, but the code cycled `len(messages) % 8`, causing indices 5, 6, 7 to raise `IndexError`, triggering `assessment_error=True` and suppressing questions after turn 4.
- Bug 2 (`scoring.py` passive decay): The spaced-rep formula (`0.7 × prior + 0.3 × signal`) treats passive signals (low confidence conversational responses) the same as active (high-confidence MCQ answers). A 1.0 MCQ score would decay to 0.51 via a single weak passive signal, erasing earned points.
- Bug 3 (`scoring.py` session guard): No minimum session question count. One correct MCQ → session_score=1.0 → topic_score=1.0 → phase gate passed, even though one question is not enough evidence.
- Fixed all three using the lightest-weight approach: exact arithmetic for the modulo; a flag-based formula switch for passive scoring; a `None` sentinel for the session guard to preserve backward compatibility until Commit 41 wires the real counter.

**Reasoning & discovery:**
1. The learning flow audit (Mira/Nova) spotted silent failures where questions disappeared or scores collapsed unexpectedly—a clear sign the bugs were present but not caught by isolated unit tests.
2. We ruled out band-aid fixes (e.g., clamping the session score to ≥0.3) because they would hide the root cause and create inconsistent behavior across different question counts and signal combinations.
3. The clincher was realizing that passive signals and active signals should have different formulas—passive should never erase what was earned, only add credibility incrementally. That led to the `is_passive` flag, which also cleanly separates the two concerns in code.

**The key changes:**

```python
# assess.py — line 34
# Before:
if len(messages) % 8 == 0:

# After:
if len(messages) % 5 == 0:
```

```python
# scoring.py — compute_topic_scores signature
# Before:
def compute_topic_scores(
    topic: str,
    best_prior: float,
    signal: float,
    decay_factor: float = 0.7,
) -> float:

# After:
def compute_topic_scores(
    topic: str,
    best_prior: float,
    signal: float,
    decay_factor: float = 0.7,
    is_passive: bool = False,
    session_question_count: int | None = None,
) -> float:
```

```python
# scoring.py — compute_topic_scores logic
# Before (all signals use multiplicative formula):
return decay_factor * best_prior + (1 - decay_factor) * signal

# After (passive uses additive with cap):
if is_passive:
    return max(best_prior, min(best_prior + signal * 0.1, 0.3))
if session_question_count is not None and session_question_count < 3:
    warnings.warn(f"Session has {session_question_count} questions; returning unchanged")
    return best_prior
return decay_factor * best_prior + (1 - decay_factor) * signal
```

**Design pattern:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Sentinel value (`None`) | Session guard uses `None` to mean "not specified yet" rather than defaulting to `1`, so existing callers that omit the parameter don't accidentally trigger the guard | Preserves backward compatibility until Commit 41 wires the real session counter from AgentState; default `1` would break all existing code |
| Dual formula by intent | Passive signals use additive-with-cap; active signals use multiplicative decay | Active (MCQ) answers are earned and shouldn't be erased; passive (conversational) signals add supporting evidence but can't override high-confidence learned knowledge |

**Files touched:**
- `src/app/assess.py` — line 34: fixed MCQ modulo from 8 to 5
- `src/app/scoring.py` — added `is_passive: bool = False` and `session_question_count: int | None = None` parameters; split formula logic by signal type; added session guard with warning
- `tests/test_scoring.py` — 16 new tests across `TestPassiveScoringLogic`, `TestSessionMinimumGuard`, `TestQuestionIndexCycling` (317 pass total)

---

## Commit 40 — `langchain-curriculum` · Lara · 2026-05-20

`langchain_fundamentals` re-added as the fifth Phase 2 bridging topic; `topic-slugs.json`, `curriculum-map.md` (arc diagram + full spec), and `gates.md` (4→5 required topics, mean 0.75 unchanged) updated; 5 MCQs + 8 open-ended questions with full rubrics written; Nova wires slug to `VALID_MODULE_SLUGS`, `PHASE_2_TOPICS`, and `_ORDERED_SLUGS` in Commit 41.

---

## Commit 41 — `gate-remediation` · 2026-05-20 · Nova (Claude direct edits) · `architectural | new feature`

> **In one sentence:** Four correctness fixes wired together: `langchain_fundamentals` registered as the 9th curriculum slug, intermediate users with Phase 1 gaps routed to remediation questions, the session question counter connected to the minimum-3-questions guard, and a proximity hint injected into the LLM context when a user's score is within 0.10 of passing a phase gate.

**Interview talking point:**
> **Q:** How does the system handle a learner who has technically "passed" Phase 1 but still shows conceptual gaps in their answers?
>
> **A:** When the LLM evaluator identifies a gap in a Phase 1 topic (e.g., embeddings) and the user is at `intermediate` level (meaning they passed Phase 1 by gate state), the question selection function checks the Phase 1 gap list before the normal phase-eligible selection. If a Phase 1 gap exists, the user gets a targeted Phase 1 remediation question instead of jumping them entirely into Phase 2. The remediation is intentionally scoped to `intermediate` only — `advanced` and `expert` users with apparent Phase 1 gaps are more likely to be LLM false positives than genuine knowledge regression.

**What happened and why:**
- Added `langchain_fundamentals` to `PHASE_2_TOPICS` (scoring.py), `VALID_MODULE_SLUGS` and `TopicScoresDelta` (state.py), `_ORDERED_SLUGS` and passive assessment prompt (assess.py). Canonical slug count is now 9.
- Implemented Phase 1 remediation in `_select_test_slug()`: for `user_level == "intermediate"`, checks `PHASE_1_TOPICS ∩ identified_gaps` first; if any Phase 1 slug is in the gaps and valid, return it immediately. All other mastery levels follow the unmodified path.
- Wired `session_question_counts: dict[str, int]` as a new `AgentState` field; `assess_node` emits it in both MCQ and LLM evaluation paths; `MemorySaver` checkpointer accumulates it across turns; `update_profile_node` reads it and passes the per-topic count to `compute_topic_scores()` — activating the minimum-3-questions guard introduced in Commit 39.
- Added proximity hint in `generate_node`: `await asyncio.to_thread(get_profile_by_user_id, user_id)` reads the stored profile, finds any Phase 1/2 topic with score in [0.60, 0.70), and appends `"Note: user is close to passing {slug} (score: {score:.2f}, threshold: 0.70). Reinforce this topic where natural."` to the context string. Silently skipped if `user_id` is None or profile lookup fails.

**Reasoning & discovery:**
1. The minimum-3-questions guard (Commit 39) was a latent safety feature — the parameter existed but was always `None` until this commit passed the real counter from `session_question_counts`. Making it live required emitting the counter in `assess_node` (which sees each evaluation), accumulating via `MemorySaver`, and reading in `update_profile_node`.
2. The Phase 1 remediation gap was identified by testing: an intermediate user whose LLM evaluator found `identified_gaps: ["embeddings_and_similarity"]` would receive a `chunking_strategies` question next (their eligible Phase 2 topic) — when they actually needed to revisit embeddings. The fix required a level-specific check before the normal loop.
3. `generate_node` reading the DB directly was a deliberate choice over adding `topic_scores` to `AgentState`. The proximity hint needs *absolute* stored scores (e.g., "current is 0.65"), not the per-turn delta in `topic_scores_delta`. Carrying absolute scores through `AgentState` would duplicate DB state and add a DB-read node to the graph. A targeted `asyncio.to_thread` read inside the node is the minimal-coupling approach, consistent with the existing `asyncio.to_thread` pattern throughout the project.

**Design pattern:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Level-specific remediation gate | `if user_level == "intermediate"` guard before Phase 1 gap check | Remediation scoped narrowly — `beginner`/`novice` already get Phase 1; `advanced`/`expert` Phase 1 gaps likely LLM false positives |
| MemorySaver accumulation for counters | `session_question_counts` emitted per-turn, accumulated by checkpointer | Decouples who counts (assess_node) from who consumes the count (update_profile_node); resets naturally on new `thread_id` |
| Async DB read inside generator node | `asyncio.to_thread` with graceful-skip on None | Minimal coupling; no new AgentState fields; consistent with project-wide blocking I/O bridge pattern |

**Files touched:**
- `src/app/profile/scoring.py` — `langchain_fundamentals` added to `PHASE_2_TOPICS`
- `src/agents/state.py` — `langchain_fundamentals` in `VALID_MODULE_SLUGS` + `TopicScoresDelta`; new `session_question_counts: dict[str, int]` field in `AgentState`
- `src/agents/nodes/assess.py` — `langchain_fundamentals` in `_ORDERED_SLUGS` and passive prompt; Phase 1 remediation block in `_select_test_slug()`; `session_question_counts` emitted in MCQ + LLM eval paths
- `src/agents/nodes/update_profile.py` — reads `session_question_counts` from state; passes per-topic count to `compute_topic_scores()` as `session_question_count`
- `src/agents/nodes/generate.py` — `asyncio.to_thread` DB read; proximity hint appended to context

---

## Commit 42 — `rag-specialist-persona` · 2026-05-20 · Claude

**What was built:** Created `.claude/agents/rag-specialist.md` — the identity file for the RAG Specialist agent, a practitioner-depth content author whose domain is `knowledge-base/curriculum/questions/` only. Updated `AGENTS.md` to add a "CONTENT SPECIALISTS" section alongside the existing team structure diagram, and a worklog reading map entry covering the Specialist's collaboration protocols with Lara and Nova.

**Why this matters for learning:** Curriculum depth has two separable concerns: _structure_ (what topics exist, what phases they belong to, what format questions use — owned by Lara) and _depth_ (what failure modes practitioners actually encounter in production — owned by the Specialist). Conflating both into one agent produces either surface-level questions or format inconsistency. The interface contract — Lara owns the slug schema and format definition; the Specialist writes within it — is the minimal-coupling design that prevents format drift when two agents author to the same question bank.

**The practitioner depth criterion ("the litmus test"):** Would a senior engineer who has never touched LangChain answer this correctly from solid RAG fundamentals? If yes → the question is too abstract. Would someone who read the LangChain docs this morning answer it correctly? If yes → it tests recall, not understanding. The RAG Specialist targets the gap between those two: questions that require operational knowledge of failure modes, not framework recall.

**Design pattern:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Writer role with single-owner format | Specialist writes question content; Lara owns slug schema + format definition | Prevents format drift when two agents author to the same question bank |
| Nova → Specialist signal path | Nova surfaces low-scoring topics from `session_history`; Specialist adds harder questions or better distractors there | Makes content quality feedback loop data-driven, not intuition-driven |
| Explicit domain boundary in identity file | Specialist file lists every Lara-owned file it may never touch | Removes ambiguity — curriculum structure gaps are Lara handoffs, not Specialist self-assignments |

**Files touched:**
- `.claude/agents/rag-specialist.md` — new: agent identity, domain boundaries, expertise framing, Lara + Nova collaboration contracts
- `AGENTS.md` — update: CONTENT SPECIALISTS section in team diagram; worklog reading map entry for RAG Specialist

---

## Commit 43 — `phase-unlock-agent` · 2026-05-21 · Nova · `architectural | new feature`

> **In one sentence:** Phase gate crossings now signal learners with a motivational announcement by adding `gate_just_passed` to the agent state and rendering announcements in the generate node — making curriculum progression visible to users instead of silent.

**Interview talking point:**
> **Q:** How do you add a motivational event signal to an agent system without creating coupling between the detection node and the render node?
>
> **A:** Introduce a transient state field (`gate_just_passed`) that is written by the detection node (update_profile) and cleared by the consuming node (generate) in the same turn. The signal is "fire once" by design — the update node reads the previous gate status, detects a crossing, and emits the field. The generate node consumes it, renders an announcement, and always writes `None` to clear it for the next turn. This keeps the two nodes decoupled (neither imports from the other) while ensuring the signal fires exactly once per gate crossing.

**What happened and why:**
- Phase gate crossings were invisible — a user who unlocked Phase 2 received no signal, so the motivational arc of the curriculum was broken. The learner couldn't tell they had progressed.
- Added `gate_just_passed: str | None` field to `AgentState`. This carries the signal name (e.g., `"phase_1"` or `"phase_2"`) from one node to the next within a single turn, then is cleared.
- Rewrote `_LEVEL_ORDER` and `_GATE_THRESHOLDS` constants in `update_profile_node`: define phase thresholds as integer rank values (novice=0, beginner=1, intermediate=2, advanced=3, expert=4). On every profile update, compare old rank to new rank — if the new rank crosses a threshold, emit the gate name. No LLM involved; it's pure arithmetic.
- Added `_PHASE_ANNOUNCEMENTS` dict mapping gate names to user-visible text (e.g., `"Congratulations! You've unlocked Phase 2: Core Retrieval & Search."`). The generate node prepends this to the LLM response when `gate_just_passed` is set.
- The generate node always returns `{"gate_just_passed": None}` to ensure the field is cleared for the next turn, preventing the announcement from firing twice.

**Reasoning & discovery:**
1. The problem: gate crossings happen deterministically (user_level changes from "beginner" to "intermediate") but produce no signal. Open-ended rubrics would require a second LLM call to ask "did the user just pass a gate?" — adding latency and cost for a question that can be answered with integer comparison.
2. What was ruled out: storing the announcement in `AgentState` across multiple turns (couples the two nodes and risks duplicate announcements). Correct approach: fire-once event signal — transient field written and cleared in the same turn.
3. What clinched the solution: LangGraph's checkpointer (MemorySaver) preserves state between node calls *within the same turn*, so a field written in update_profile and read/cleared in generate happens atomically. The turn boundary is the natural clearing point.

**Design pattern:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Fire-once event signal | `gate_just_passed` written by detector, read-and-cleared by consumer in same turn | Decouples detection from rendering; signal fires exactly once per crossing; automatically clears at turn boundary |
| Deterministic gate detection via rank comparison | `old_rank < threshold ≤ new_rank` using integer constants | No LLM overhead; O(n) gate checks per profile update where n ≤ 5 phases; portable and testable |
| Transient state field | `gate_just_passed: str | None` — always cleared to `None` at turn end | Prevents stale signals from leaking to later turns; simple invariant: field is always `None` at turn start |

**The key change:**
```python
# src/app/profile/scoring.py
_LEVEL_ORDER = {"novice": 0, "beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
_GATE_THRESHOLDS = {"phase_1": 2, "phase_2": 3, "phase_3": 4}

# In update_profile_node:
old_rank = _LEVEL_ORDER.get(previous_level or "novice", 0)
new_rank = _LEVEL_ORDER.get(score_update["mastery_level"], 0)

gate_just_passed = None
for gate_name, threshold in _GATE_THRESHOLDS.items():
    if old_rank < threshold <= new_rank:
        gate_just_passed = gate_name
        break

return {
    "messages": [updated_msg],
    "topic_scores_delta": score_update["topic_scores"],
    "gate_just_passed": gate_just_passed,
}
```

```python
# src/agents/nodes/generate.py
_PHASE_ANNOUNCEMENTS = {
    "phase_1": "Congratulations! You've mastered RAG fundamentals. Unlocking Phase 2: Core Retrieval Systems.",
    "phase_2": "Excellent work! You've completed Phase 2. Unlocking Phase 3: Advanced Production Patterns.",
    "phase_3": "Outstanding! You've reached expert level in RAG systems. You're now ready for cutting-edge topics.",
}

# In generate_node:
gate_just_passed = state.get("gate_just_passed")
if gate_just_passed and gate_just_passed in _PHASE_ANNOUNCEMENTS:
    announcement = _PHASE_ANNOUNCEMENTS[gate_just_passed]
    response = AIMessage(content=announcement + "\n\n" + str(response.content))

return {
    "messages": [response],
    "answer": response.content,
    "gate_just_passed": None,  # clear for next turn
}
```

**Files touched:**
- `src/agents/state.py` — added `gate_just_passed: str | None` to `AgentState`
- `src/agents/nodes/update_profile.py` — `_LEVEL_ORDER` and `_GATE_THRESHOLDS` constants; gate crossing detection loop; emit `gate_just_passed` in return dict
- `src/agents/nodes/generate.py` — `_PHASE_ANNOUNCEMENTS` dict; announcement prepending and field clearing; always return `{"gate_just_passed": None}`
- `tests/test_update_profile_node.py` — 8 new `TestGateDetection` tests covering all rank transitions and gate boundaries
- `tests/test_generate_node.py` — 5 new gate-announcement tests (announcement rendering, field clearing, missing gate names)

---

**Commit 44 — `phase-unlock-ui`** · 2026-05-21 · Aria (frontend) · `new feature`

> **In one sentence:** Phase unlock events now animate visually in the profile panel, with locked phases shown as gated and unlocked phases displaying full progress.

**Interview talking point:**

> **Q:** How do you detect a state change that has already been consumed by another part of the system?
>
> **A:** Aria preserved the unlock event for frontend display by tracking the mastery level in a mutable-list closure (`_prev_mastery = [None]`). Since `gate_just_passed` is cleared by `generate_node` before the SSE done event arrives at the browser, she detects the unlock by comparing current mastery to the previous value across consecutive `profile_panel.refresh()` calls. The `_prev_mastery[0] is not None` guard prevents a false-positive animation on first load when state is cold.

**What happened and why:**

- **Problem:** Commit 43 added phase-unlock detection to the backend (emit `gate_just_passed` announcement), but the frontend had no way to know when a user advanced between phases. The `gate_just_passed` field is consumed by `generate_node` before the SSE done event triggers the browser to refresh the profile panel.
- **Solution:** Aria added phase-grouped display to the Overview tab with locked/unlocked state visibility — locked phases show padlock icons and "Pass Phase X to unlock" hints, while unlocked phases show full progress bars and per-topic scores. The Current tab shows phase progression context ("Phase X of 3 — N topics complete"). A 2.5-second CSS `@keyframes rag-phase-unlock` green glow animates newly unlocked phase blocks.
- **Detection pattern:** The closure variable `_prev_mastery = [None]` stores the previous mastery level. When `profile_panel.refresh()` fires, Aria compares current mastery to `_prev_mastery[0]`. If they differ and `_prev_mastery[0] is not None` (ruling out cold start), the unlock animation applies. This is the same mutable-list pattern used in `_tab_state` and `_ob_step` elsewhere in the panel.
- **Security boundary:** All user-derived values (topic names, scores, mastery level) flow through `ui.label()` for escaping. The padlock icon is the only `ui.html()` call and is a static SVG string with no interpolation.

**Reasoning & discovery:**

1. **Initial constraint:** The backend unlock signal (`gate_just_passed`) is ephemeral — it's prepended to the LLM response in `generate_node` and then explicitly cleared before the node returns. The profile panel receives the announcement text but not the field itself, so there's no direct event signal to the frontend.
2. **Ruled out:** A new backend field to persist unlock state would require API changes and compromise the "fire-once" event pattern. Parsing the announcement text in the frontend would couple UI logic to prompt wording. Adding a separate unlock endpoint would increase latency and complexity.
3. **Clinched solution:** Aria observed that the mastery level itself changes when a gate is passed — it's the authoritative side effect. Comparing current mastery to previous mastery across refreshes gives us a durable, deterministic unlock signal that survives the consumption of `gate_just_passed` by the backend. The mutable-list closure mirrors the precedent already set in the profile panel code.

**Design pattern:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Mutable-list closure (`[None]`) | State persists across function invocations without a class or instance variable; fits NiceGUI's functional composition model | Matches the idiom already used for `_tab_state` and `_ob_step` in `profile_panel()`; keeps refresh logic self-contained without introducing state containers |
| Guard clause on cold start | `_prev_mastery[0] is not None` prevents animation on first panel load when state transitions from undefined to defined, not from level to level | Distinguishes an initial state load (no animation) from a true upgrade (trigger animation) |
| CSS keyframe application via Quasar class | `ui.add_head_html()` injects `@keyframes rag-phase-unlock` once; Aria applies class conditionally per phase block | Separates animation definition from trigger logic; reusable across multiple phase blocks if needed in future |

**Files touched:**

- `src/app/ui.py` — `profile_panel()` function: `_prev_mastery = [None]` closure variable, `_gate_crossed` boolean detection, phase-grouped Overview tab layout (locked phases with padlock SVG + hints vs. unlocked phases with progress bars), phase progression context line in Current tab ("Phase X of 3 — N topics complete, M to go"), unlock animation CSS (`@keyframes rag-phase-unlock`, 2.5s green glow) injected via `ui.add_head_html()`

---

## Commit 45 — `rag-specialist-content` · 2026-05-21 · RAG Specialist

**One-liner:** First RAG Specialist content pass — expanded all 9 MCQ question banks from 5 questions to 10–12 each, added expert-tier questions and practitioner-depth "why wrong" distractor explanations for every incorrect option, and appended 3 open-ended questions per topic (27 total). Zero gate wave (knowledge-base content only, no code paths). Curriculum gap flagged: LangSmith tracing may warrant a standalone Phase 3 topic (handoff to Lara).

---

## Design Principle — Constants Should Be Narrow and Honest · 2026-05-22

> Recorded from the assess node decomposition session. Not tied to a single commit — applies across the entire codebase.

**The principle:** A constant should do exactly one thing and its comment should say exactly that. When logic changes around a constant, update the comment to match the new reality. A comment that describes old behavior is a lie waiting to mislead someone.

**Where it came from:**

During the assess node refactor, `_PASSIVE_LEVEL_SCORE` was being used to reward the *complexity of the user's question*, not the *user's actual mastery level*. A novice who happened to ask an advanced question would receive a +0.3 score bump — the same reward as an expert. This was semantically wrong: the system was measuring question vocabulary, not demonstrated understanding.

The fix was to anchor the score delta to `user_level` from `AgentState` instead of `inferred_level` from the LLM. This also changed what the constant *means*:

- **Before:** "How much does a question of this complexity level contribute to mastery?"
- **After:** "How much does a user at this mastery level gain from engaging with their topic?"

That is a fundamentally different thing. The constant's comment had to narrow with it.

Similarly, `_PASSIVE_CONFIDENCE_THRESHOLD` originally guarded both slug inference and level inference. After the level moved to `AgentState`, it only guards slug inference. The comment was updated to say so.

**The rule:**

> After any refactor that changes what a constant governs, ask: does the comment still describe what this constant actually does? If the constant now does less — say so explicitly.

**The related behavior change:**

When the inferred question level is more than one step above the user's current level, the system now redirects rather than inflating the profile score. A novice asking an expert-level question doesn't receive +0.3 — they receive a message: "I can see you're eager to get ahead. Let's make sure the foundations are solid first." A question appropriate to their level follows.

This keeps the profile honest: scores reflect what the user has demonstrated, not what they've asked about.

---

## Design Principles — Assessment Module Refactor · 2026-05-22

> Recorded from the evaluate_answer refactor session. Three patterns discovered that apply broadly.

### 1. `_` prefix means private to the file — not the package

Python's `_` prefix convention signals "do not import this from outside." If a function is imported by another module, it is not private regardless of its name. During this refactor, `_build_eval_result`, `_build_test_result`, and `_evaluate_answer` all had leading underscores despite being imported and called by sibling modules. The fix: remove the prefix from anything that crosses a file boundary. Keep it only for functions that are genuinely internal to a single file.

**The rule:** Before naming a function with `_`, check whether it will be imported anywhere. If yes, it belongs to the module's public surface.

### 2. Modulo index must match the collection it indexes

The open question evaluation path was using `_select_mcq_question_index()` — a function that calls `get_mcq_count(slug)` — to pick which open question to load. MCQ count and open question count per slug are independent numbers. The result was a double modulo: `(len(messages) % mcq_count) % open_question_count`. With mismatched bases (e.g. 5 MCQ, 3 open questions), some open questions would be selected more often than others — a silent, biased distribution.

The fix: pass `len(messages)` directly to `_load_open_question_criteria`, which already applies `% len(question_sections)` internally. One modulo, correct base.

**The rule:** When using modulo to index into a collection, the divisor must be the length of *that specific collection*, not a count from a related but distinct collection.

### 3. Audit state fields for dead reads before keeping them

`test_answer_score` was written in three places — two `build_eval_result` call sites and two `build_test_result` call sites — but never read by any downstream node, API route, or UI component. It existed as documentation of the score, but `topic_scores_delta` already carried the same information in a more useful form (keyed by topic slug). The field was removed entirely.

**The rule:** Before keeping a state field, grep for all read sites (`state.get("field_name")`). If results are only write sites — assignments and dict literals in builder functions — the field is dead state and should be removed.

### 4. Guard clause return: distinguish intentional signal from error

When a function returns early with an empty/neutral value, ask first: is this case an *expected, valid outcome* or an *unexpected failure*?

In `_validated_passive_delta`, `relevant_slug is None` returns `{}, False` rather than raising. That's correct — the system prompt explicitly documents `None` as a valid LLM response meaning "question is not RAG-related." The caller handles it: `is_rag_related = result.relevant_slug is not None` routes the flow accordingly. Raising `ValueError` here would be wrong: it would be caught by the outer `except Exception`, flip `is_rag_related` to `True`, and treat a non-RAG question as RAG-related.

Contrast with a truly unexpected case — e.g. a slug that is non-null but not in `VALID_MODULE_SLUGS`. That's an LLM hallucination, not a designed signal. It still doesn't raise (the caller can't act on it usefully) but it logs a warning, making the anomaly visible without crashing the flow.

**The rule:** Before writing a guard clause, ask: "Is this value intentional — designed and handled by the caller — or is it a failure?" Intentional: return a neutral value, let the caller route. Unexpected but recoverable: log a warning, return neutral. Unexpected and unrecoverable: raise. Never raise on values the LLM prompt deliberately allows as output.

### 5. On uncertainty, fail open — not closed

When an LLM call fails and you don't know whether the input was relevant, returning a "not relevant" signal silently suppresses downstream behavior. In `run_passive_assessment`, an exception returns `({}, True, False)` — `is_rag_related=True` — rather than `False`. Returning `False` would cause the caller to skip test selection entirely, as if the question were confirmed off-topic. That's worse than doing nothing: it actively suppresses a knowledge check based on a failure, not evidence.

The empty `delta` (`{}`) ensures no score update happens, so the profile stays honest. But the flow continues — the user still gets a question.

**The rule:** When a component fails and you can't determine the correct signal, default to the value that keeps the system running, not the value that shuts it down. Fail open on uncertainty; fail closed only when you have positive evidence that shutting down is correct.

---

## Commit 45.2 — `open-question-delivery` · Nova · 2026-05-22

Added delivery functions for open-ended questions (`select_open_question`, `get_open_question_count`, `load_open_question`, `deliver_open_question`) mirroring MCQ pattern; ratio logic wired in Commit 45.3.

---

## Commit 45.3 — `question-type-balance` · Nova · 2026-05-22 · `new feature`

> **In one sentence:** Added `select_question_type()` to route novice/beginner learners exclusively to MCQs and probabilistically balance MCQ vs. open questions for advanced users, activating the open-question delivery pipeline from C45.2.

**Interview talking point:**
> **Q:** How did you decide between inlining the type-selection logic and extracting it to its own function?
>
> **A:** Inlining would have required mocking the full passive assessment pipeline just to test the ratio distribution — 1000 draws against live LLM calls. The standalone function lets us validate the probability contract in isolation: novice always returns MCQ, expert hits ~70% open over 1000 draws. The caller reads `if question_type == "open"`, which is literal spec language; the decision point is immediately readable without unpacking a conditional expression.

**What happened and why:**
- `select_question_type(user_level: str) -> str` added to `question_selection.py` — weighted random draw against `_OPEN_PROB` dict; novice/beginner take a deterministic fast-path (explicit `if prob == 0.0` guard, no `random` call)
- `select_test_question` now calls `select_question_type` immediately after the non-RAG early return; `"open"` delegates to `deliver_open_question` (wired in C45.2); MCQ path unchanged
- 12 new tests cover all spec gates: determinism (50 draws, set must be `{"mcq"}`), probabilistic coverage (200 draws, both types must appear), ratio approximation (±15% over 1000 draws), and routing delegation via mock

---

## Commit 45.4 — `question-difficulty-degradation` · Nova · 2026-05-23 · `new feature | architectural`

> **In one sentence:** Added two-step graceful degradation for open questions the user can't answer: step 2 rephrases the question at a lower difficulty via LLM (once only), step 3 records the slug as a knowledge gap and falls back to the RAG teaching path on second difficulty signal.

**Interview talking point:**
> **Q:** How do you handle the case where a learner genuinely can't answer the assessment question, without just moving on or giving them the answer outright?
>
> **A:** The system uses a two-step scaffold. On the first difficulty signal ("too hard", "I don't understand", etc.), the question is rephrased at the user's level — the hard constraint in the prompt is "Do NOT reveal what the right answer is." If the user still can't answer after the simplification, the topic is recorded as a knowledge gap and `generate_node` falls back to its normal RAG path, which teaches the concept through context. The key design choice: a `question_simplified: bool` flag in `AgentState` prevents re-simplification loops — `MemorySaver` holds the flag across turns, and `build_selection_result` resets it to `False` when a new question is delivered. Difficulty signal detection is keyword-based (13 phrases, case-insensitive) — no LLM call, deliberate cost-and-latency decision.

**What happened and why:**

- Added `_DIFFICULTY_PHRASES` tuple and `_is_difficulty_signal(message: str) -> bool` to `evaluation.py`. Keyword match via `any(phrase in answer.lower() for phrase in _DIFFICULTY_PHRASES)`. No LLM call for detection — deliberate (see design table).
- Added `_simplify_question(original_question: str, user_level: str) -> str` — calls `simplification_prompt | llm` as a LangChain `ainvoke` chain. Prompt has hard constraints against revealing the answer.
- Added `simplification_prompt: ChatPromptTemplate` to `prompts/assessment.py` with `{user_level}` (system) and `{question}` / `{user_level}` (human) placeholders. Hard constraint text: "Do NOT hint at the correct answer. Do NOT reveal what the right answer is."
- Degradation routing block added at top of `evaluate_answer` before the MCQ/open branch. No difficulty signal → normal path unchanged. Difficulty signal + `question_simplified=False` → step 2 (simplify, set flag). Difficulty signal + `question_simplified=True` → step 3 (clear pending, add slug to gaps, RAG path).
- `question_simplified: bool` added to `AgentState`. Reset to `False` in `build_selection_result` (new question delivery) and `build_eval_result` (evaluation complete).
- 34 new tests in `tests/test_question_difficulty_degradation.py`: 7 gates covering signal detection, false-positive prevention, step 2/step 3 routing, reset behavior, and prompt constraints.
- **Pre-existing debt fixed:** `tests/test_assess_node.py` had stale imports from `agents.nodes.assess` (functions moved to `agents.assessment.*` in prior refactoring). Fixed imports and updated expected key sets for `build_eval_result` output.

**Viktor Hard Block — deferred to Commit 45.4.1:** Step 2 partial return dict is missing `"is_mcq": False`. LangGraph partial merge keeps the prior `is_mcq` value; if the original question was MCQ, the user's next-turn answer to the simplified open question routes to the MCQ evaluator. Fix is one line — scheduled as its own commit per the no-gate-fix-passes rule.

**The key change:**

```python
# src/agents/assessment/evaluation.py — difficulty degradation routing
if _is_difficulty_signal(answer):
    already_simplified = state.get("question_simplified", False)
    slug = state.get("pending_test_slug") or ""
    if not already_simplified:
        simplified = await _simplify_question(original_question, user_level)
        return {
            "pending_test_question": simplified,
            "question_simplified": True,
            "messages": [AIMessage(content="Let me rephrase that question at a simpler level:\n\n" + simplified)],
        }
    else:
        existing_gaps = list(state.get("identified_gaps") or [])
        if slug and slug not in existing_gaps:
            existing_gaps.append(slug)
        return build_eval_result(
            topic_scores_delta={},
            identified_gaps=existing_gaps,
            assessment_error=False,
        )
```

**Design pattern:**

| Pattern | What it means here | Why it was chosen |
|---|---|---|
| Keyword detection over LLM | 13 phrases matched case-insensitively; no LLM call on difficulty signal | LLM call per turn doubles latency and cost for a signal that maps directly to simple phrases |
| Single-flag simplification gate | `question_simplified: bool` in AgentState + MemorySaver persistence | Prevents infinite rephrase loops without a counter; reset semantics are clear (False = new question) |
| Step 3 reuses RAG path via `pending_test_question=None` | Clearing the field is the existing signal for `generate_node` to use RAG | No new mechanism needed; field absence already means "teach, don't test" |
| Hard constraint in simplification prompt | "Do NOT reveal what the right answer is" explicit text | LLM will naturally try to be helpful by hinting; constraint anchors it to pedagogical rephrasing only |

**Files touched:**

- `src/agents/state.py` — `question_simplified: bool` field added to `AgentState`
- `src/agents/assessment/evaluation.py` — `_DIFFICULTY_PHRASES`, `_is_difficulty_signal`, `_simplify_question`, degradation routing block in `evaluate_answer`; `simplification_prompt` import
- `src/agents/prompts/assessment.py` — `simplification_prompt` added
- `src/agents/assessment/results.py` — `question_simplified: False` added to `build_selection_result` and `build_eval_result`
- `tests/test_question_difficulty_degradation.py` — new: 34 tests, 7 gates
- `tests/test_assess_node.py` — stale import fix + expected key set update (pre-existing debt)

---

## Commit 45.5 — `rag-prompt-quality` · Nova · 2026-05-23 · `prompt engineering`

> **In one sentence:** Rewrote the RESPONSE FORMAT block in all 5 RAG prompt templates from permissive conditional rules to a mandatory floor, and replaced `_NOVICE_SYSTEM`'s audience description with an explicit persona declaration and hardened analogy rule.

**Interview talking point:**
> **Q:** How do you improve LLM response consistency without changing the underlying model or adding a post-processing layer?
>
> **A:** The key insight is that LLMs treat "only if appropriate" as a permission decision — and the default answer to an open permission is no. "Bold key terms only if it helps" means the model decides most answers don't need bolding, and they get plain prose. Replace the permission with a minimum floor ("Every response must bold the first technical term it introduces") and the decision is made for the model. The escape hatch matters too: "single-sentence answers may use plain prose" keeps the rule from forcing structure onto trivially short answers. The same principle applies to persona: describing the target audience tells the model who it's talking to; declaring a voice with negative constraints ("never sounds like a manual or a search engine") tells it how to behave.

**What happened and why:**
- Two root causes identified by Nova and confirmed in Mira product review: (1) `_NOVICE_SYSTEM` described the audience but didn't declare a behavioral voice — LLM defaulted to general assistant tone; (2) RESPONSE FORMAT used "only if/when/for" language in all 5 prompts, giving the LLM permission to skip structure on every response.
- Fix 1 (persona): "You are a patient tutor explaining RAG to someone with no technical background" → "You are an enthusiastic and patient tutor — you never sound like a manual or a search engine." The negative constraints are the operative part.
- Fix 2 (analogy): "Lead with a real-world everyday analogy BEFORE introducing the technical concept" → "You MUST open every answer with a real-world analogy. Do this even for short answers." Soft directive removed; MUST + explicit short-answer scope added.
- Fix 3 (RESPONSE FORMAT — all 5 prompts): "only if/only when" conditional blocks → two mandatory floor rules + one single-sentence escape hatch.

**The key change:**

```python
# src/agents/prompts/rag.py — RESPONSE FORMAT (before, in all 5 prompts)
# - Bold (**term**) key technical terms on first use.
# - Table: only when comparing two or more things across the same attributes.
# - Numbered list: for sequential steps or processes only.
# - Heading (## Title): only if the response is long enough to need section navigation.
# - Plain prose: for short or conversational replies.

# After — all 5 prompts
# - Every response must bold the first technical term it introduces.
# - Responses longer than 3 sentences must use at least one structural element (bold, list, or heading).
# - Single-sentence answers may use plain prose — no structure required.
# - Table: when comparing two or more things across the same attributes.
# - Numbered list: for sequential steps or processes.
# - Heading (## Title): when the response is long enough to need section navigation.
```

**Design principle:**
> Permissive constraints give the LLM a permission question. Mandatory floors give it a default. When the goal is consistency, remove the permission question — don't make it louder.

**Files touched:**
- `src/agents/prompts/rag.py` — all 5 prompt strings updated; no functional code changed

---

## Commit 45.6 — `welcome-message-ux` · Aria · 2026-05-23 · `UX improvement`

> **In one sentence:** Rewrote `_build_welcome_message()` to give first-time Novice users 4 concrete starter paths and give returning users a progress-first summary with phases done/total, last active topic, and one resume action.

**Interview talking point:**
> **Q:** How do you improve first-time user retention when you can't add new analytics or A/B tests?
>
> **A:** The old first-time message said "Ready to start? Best first move: What is RAG?" — it assumed the user knew what to do with that. A non-technical user sees a blank chat and one cryptic prompt and interprets it as "the app doesn't guide me." The fix was structural: establish what the app is in one sentence, then offer 4 concrete starter paths that span different entry points (total beginner, ML-aware, builder, overview-seeker). The user can act in under 10 seconds without any prior knowledge of RAG. For returning users, the old message said "Here's your weak spot, try this question" — useful but missing location context. The new format leads with progress (`Foundations ✓ · Core 1/5 · Production 0/2`), surfaces the last active topic for continuity, then gives the one recommended action. The user knows where they are before they decide what to do next.

**What happened and why:**
- Mira product review (2026-05-23) flagged two day-1 retention risks: first-time message outsources the first decision to the user without establishing the app's purpose; returning-user message lacks progress context and narrative continuity.
- First-time path (new): warm 1-sentence app description + 4 copy-paste starter paths spanning novice/ML-aware/builder/overview entry points. Condition: `interaction_count == 0 AND mastery_level == "novice"` — non-novice first-timers get the returning-user format with 0/N counts.
- Returning user path (new): all branches now open with `**Your progress:** Foundations X/2 · Core X/5 · Production X/2` computed from `topic_scores` (score ≥ 0.70 = done). Existing gap/strength recommendation logic preserved for the resume action.
- Progress computation: `_PROGRESS_PHASES` defined inline (not reusing `_PHASE_TOPICS`) — the two constants serve different purposes: adaptive question selection vs. cumulative progress display.

**Files touched:**
- `src/app/ui.py` — `_build_welcome_message()` rewritten; function signature and no-profile fallback unchanged

---

---

## Hotfix — `markdown-heading-rendering` · Aria + Team Lead · 2026-05-23 · `Prompt Engineering / CSS`

> **In one sentence:** AI responses were missing visible headers because Quasar's CSS cascade overwrote the gradient-clip trick, and the prompt heading rule gave the model discretion it used to skip headers on follow-up questions.

**Interview talking point:**
> **Q:** You have a conditional formatting rule in your prompt ("use headings when the response is long enough"). Users report headings appear sometimes but not consistently. What's wrong and how do you fix it?
>
> **A:** Two separate bugs. First: the CSS. The gradient text trick (`background-clip: text` + `color: transparent`) breaks silently when any higher-specificity rule sets `color` on the element — Quasar's body color was cascading into headings and making the gradient invisible. Fix: `!important` on all five gradient declarations. Second: the prompt. "Required when 2+ concepts" is a permission question the LLM answers per turn. For follow-up questions — which are shorter and more focused — the model consistently answered "this is one concept, skip the heading." The rule looked mandatory but behaved optional. Fix: make it truly unconditional ("every response longer than one sentence MUST open with a `##` heading"). The escape hatch for single-sentence answers prevents over-formatting without reopening the discretion gap.

**What happened and why:**
- User reported: first AI response had gradient headers; second (a follow-up) had none. Repeated consistently.
- CSS investigation: `.nicegui-markdown h1/h2/h3` gradient declarations existed but lacked `!important` — Quasar's cascade was winning. Adding `!important` to all five properties fixed header visibility when headers were present.
- Prompt investigation: the heading rule was "required whenever the response has 2+ distinct concepts or paragraphs." Follow-up questions get focused single-concept answers — the model read the rule, evaluated the response as "one concept," and skipped the heading. Correct behavior per the rule; wrong behavior per the user expectation.
- Pattern identified: the model treats conditional formatting rules as permission questions. When in doubt it omits structure rather than adds it. The only reliable fix is to remove the condition.
- MCQ responses were a separate case: clicking an option sends "A. option text" — a 5-word message — which generates a short feedback reply that also skipped headings. Fixed by adding an explicit MCQ detection rule: letter-prefixed messages always get `## Result / ## Why / ## Key Takeaway`.

**Key changes:**

```python
# src/agents/prompts/rag.py — heading rule (all 5 templates, before)
- Heading (## Title): required whenever the response has 2+ distinct concepts or paragraphs.

# After
- Heading (## Title): every response longer than one sentence MUST open with a ##
  heading that names the concept being explained. No exceptions. Use additional ##
  headings for each new concept, and ### for sub-points within a section.
- MCQ answer: when the user's message is a single letter (A/B/C/D) or a letter
  followed by option text, always respond with ## Result · ## Why · ## Key Takeaway.
```

```css
/* src/app/ui.py — .nicegui-markdown heading CSS (before) */
.nicegui-markdown h1,.nicegui-markdown h2,.nicegui-markdown h3{
  background:linear-gradient(135deg,#f97316,#ec4899);
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent; ... }

/* After */
.nicegui-markdown h1,.nicegui-markdown h2,.nicegui-markdown h3{
  background:linear-gradient(135deg,#f97316,#ec4899) !important;
  -webkit-background-clip:text !important;
  -webkit-text-fill-color:transparent !important;
  background-clip:text !important;
  color:transparent !important; ... }
```

**Design principles:**
> Conditional formatting rules in prompts are permission questions. LLMs default to "no." Remove the condition, not the rule.
> The gradient-clip CSS trick is fragile under cascade — always `!important` it or put it inline.

**Files touched:**
- `src/agents/prompts/rag.py` — heading rule rewritten in all 5 prompt strings; MCQ rule added
- `src/app/ui.py` — `!important` added to 5 gradient-clip declarations; `color: transparent !important` added

---

## C46 — mastery-matched-routing

**What was built:** The question-delivery pipeline now filters MCQ questions by the learner's `user_level` before sampling. A novice gets novice-difficulty questions; an advanced learner gets advanced-difficulty questions. When no questions exist at the target tier for a given topic, the system falls back to the nearest available tier (lower before higher) rather than returning an error.

**Where the code lives:**
- `src/agents/mcq_utils.py` — `_DIFFICULTY_FALLBACK` dict + `get_mcq_blocks_for_difficulty()`, `get_mcq_count_for_difficulty()`, `load_mcq_question_for_difficulty()`
- `src/agents/assessment/question_selection.py` — `select_mcq_question_for_level()`
- `src/agents/assessment/test_delivery.py` — routes MCQ delivery through the mastery-aware path

**The design pattern — difficulty filtering with graceful fallback:**

```python
_DIFFICULTY_FALLBACK: dict[str, list[str]] = {
    "novice":       ["novice", "intermediate", "advanced", "expert"],
    "intermediate": ["intermediate", "novice", "advanced", "expert"],
    "advanced":     ["advanced", "intermediate", "novice", "expert"],
    "expert":       ["expert", "advanced", "intermediate", "novice"],
}

def get_mcq_blocks_for_difficulty(slug: str, difficulty: str | None) -> list[str]:
    all_blocks = get_mcq_question_blocks(slug)
    if not difficulty or difficulty not in _DIFFICULTY_FALLBACK:
        return all_blocks  # unrestricted — preserves prior behavior for None/unknown
    for tier in _DIFFICULTY_FALLBACK[difficulty]:
        filtered = [b for b in all_blocks if re.search(rf"^\*\*Difficulty:\*\*\s*{tier}", b, re.MULTILINE)]
        if filtered:
            return filtered
    return all_blocks  # final safety net
```

**Why the fallback order is lower-before-higher:** When an advanced user asks about a topic with no advanced questions in the bank, serving an intermediate question (consolidation) is pedagogically better than serving an expert question (stretch). A user already at their skill ceiling getting a harder question than expected creates frustration; getting a slightly easier one creates confidence and still tests valid knowledge. The opposite fallback would undermine the adaptive engine's purpose.

**Why `None` mastery level returns all blocks:** The pre-Commit-46 behavior was unrestricted sampling. `mastery_level=None` means the system doesn't know the user's level — falling back to unrestricted is the safest default. Narrowing to any specific tier without evidence of the user's level would introduce incorrect filtering.

**What the old functions still do:** `select_mcq_question` and `load_mcq_question` were not removed — they still serve `test_assess_node.py` test helpers and `onboarding.py` respectively. The mastery-aware versions are the new production path; the old functions remain for callers that don't need tier filtering.

**Files touched:** `src/agents/mcq_utils.py`, `src/agents/assessment/question_selection.py`, `src/agents/assessment/test_delivery.py`, `tests/test_mastery_routing.py` (new — 17 tests, 5 classes)

---

## Commit 47.1 — `slug-swap-document-ingestion` · Claude (direct Edit) · 2026-05-23 · `refactor`

> **In one sentence:** Replaced every `langchain_fundamentals` reference in src/ with `document_ingestion` across five files and matching test updates, completing the curriculum rename from C47 and restoring Phase 2 advancement.

---

## Commit 47 — `curriculum-restructure` · Lara · 2026-05-23 · `curriculum design | product decision`

> **In one sentence:** Replaced `langchain_fundamentals` with `document_ingestion` as the fifth Phase 2 Core topic, archived the LangChain question files, and updated `topic-slugs.json`, `curriculum-map.md`, and `gates.md` — keeping the "RAG from scratch" curriculum true to its concept-first identity.

**Interview talking point:**
> **Q:** Why did you remove LangChain from the curriculum for an app that uses LangChain under the hood?
>
> **A:** The app is named "RAG from scratch" — it's about understanding how RAG works at the concept level, not about using a particular framework. LangChain is a convenience layer; teaching it as a required Phase 2 Core topic implied the curriculum was about a framework rather than the underlying ideas. What was missing was document ingestion — the actual first step in building any RAG pipeline from raw source files. A learner who doesn't know how documents get loaded, parsed, and pre-processed before chunking has a real gap, regardless of which framework they use. The LangChain content isn't deleted — it's archived. If a "frameworks" track is ever added, it's recoverable.

**What happened and why:**
- `curriculum-map.md` Phase 2 entry replaced: `langchain_fundamentals` (LangChain chains/LCEL/agents) → `document_ingestion` (format parsing, metadata extraction, encoding handling, structural impact on downstream chunking)
- `gates.md` Phase 2 gate updated: all three locations (human-readable, pseudocode block, machine-readable JSON) now require `document_ingestion` as one of the five passing topics
- `topic-slugs.json` updated: `"langchain_fundamentals"` replaced with `"document_ingestion"` at position 7
- Two archive files created: `knowledge-base/curriculum/questions/archive/langchain_fundamentals.md` and `.../archive/mcq/langchain_fundamentals.md` — full copies of both question banks with ARCHIVED headers noting the date and reason
- C47.1 (Nova, separate micro-commit) follows: updates five src/ files to match — `VALID_MODULE_SLUGS`, `PHASE_2_TOPICS`, `_ORDERED_SLUGS`, Core topics list in `ui.py`, and the assessment prompt

**The design principle — concept-first beats framework-first:**

The curriculum identity of "RAG from scratch" carries a constraint: every Phase 2 topic must be a transferable concept, not a framework tutorial. Document ingestion satisfies this — the principles apply whether you use LangChain, LlamaIndex, raw Python, or a custom pipeline. LangChain API details do not — they're tool-specific and version-limited.

**Why archive, not delete:**
Question banks represent significant authoring effort and real pedagogical value. Archiving preserves them for a potential future "Frameworks" or "Tooling" phase without cluttering the active curriculum. The archive path (`knowledge-base/curriculum/questions/archive/`) is a known, documented location.

**Files touched (knowledge-base/ only — no src/ in this commit):**
- `knowledge-base/curriculum/curriculum-map.md` — replaced full `langchain_fundamentals` topic block with `document_ingestion` spec
- `knowledge-base/curriculum/gates.md` — replaced slug in 3 locations (text, pseudocode, JSON)
- `knowledge-base/curriculum/topic-slugs.json` — slug replaced at position 7
- `knowledge-base/curriculum/questions/archive/langchain_fundamentals.md` (new)
- `knowledge-base/curriculum/questions/archive/mcq/langchain_fundamentals.md` (new)

---

## Commit 48 — `document-ingestion-questions` · RAG Specialist · 2026-05-23 · `content`

> **In one sentence:** Added the full question bank for the `document_ingestion` Phase 2 topic — 20 MCQs across novice/intermediate/advanced/expert tiers and 22 open-ended questions with rubrics, covering document loaders, parsing failure modes, encoding handling (mojibake, BOM markers), metadata extraction, and format-specific gotchas (multi-column PDFs, JavaScript-rendered HTML, DOCX embedded objects).

---

## Commit 49 — `langgraph-curriculum` · Claude (direct Edit) · 2026-05-23 · `curriculum design`

Added `langgraph_fundamentals` as a Phase 3 topic in `curriculum-map.md` and `gates.md`; topic is concepts-only (directed graphs, state flow, conditional routing, graph compilation, checkpointing) — the conceptual architecture behind the adaptive system itself. Phase 3 gate now requires 3 topics at ≥0.75. `topic-slugs.json` updated from 8 to 9 slugs. C49.1 follows to register the slug in src/.

---

## Commit 49.1 — `slug-add-langgraph` · Claude (direct Edit) · 2026-05-23 · `schema`

Registered `langgraph_fundamentals` in the five src/ slug registries that govern the assessment engine: `VALID_MODULE_SLUGS`, `TopicScoresDelta`, `PHASE_3_TOPICS`, `_ORDERED_SLUGS` (question selection), and `_PROGRESS_PHASES` (UI progress display); assessment prompt updated to include the slug in the valid-topics list. Phase 3 gate now evaluates all three topics (`evaluation_and_metrics`, `production_patterns`, `langgraph_fundamentals`). Test suite updated from 9-slug to 10-slug counts.
