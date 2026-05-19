# Commit 34 — `phase-gate-enforcement`
# Assignee: Nova (ai-engineer)
# Phase: Progression System · Wave D (parallel with Commit 33 — now complete)
# Status: pending

---

## Goal

Make `_select_test_slug()` in `assess.py` phase-aware. Currently it serves questions
from any topic (gap-first, then canonical ordering), ignoring the user's curriculum phase.
After this commit, question selection is gated to the user's current phase — Phase 1 topics
until Phase 1 is passed, Phase 2 until Phase 2 is passed, Phase 3 until Phase 3 is passed.

Experts (all phases passed) cycle through all topics in canonical Phase 1 → Phase 2 → Phase 3
ordering — same structured progression, not random access.

Soft gate: the user's chat answers are never restricted. Only assessment questions are
redirected to the correct phase.

---

## Context

Phase gate math already exists in `src/app/profile/scoring.py`:
- `_PHASE_1_TOPICS`, `_PHASE_2_TOPICS`, `_PHASE_3_TOPICS` — frozensets of topic slugs per phase

`user_level` in AgentState encodes the user's current phase (defined in scoring.py Session 04):
- novice: no phase started (all topics null)
- beginner: Phase 1 in progress (at least one Phase 1 topic scored, not passed)
- intermediate: Phase 1 passed, Phase 2 not yet passed
- advanced: Phase 2 passed, Phase 3 not yet passed
- expert: all phases passed

No new state fields needed. Phase gate uses `user_level` already in AgentState.

---

## Files to Modify

| File | Action | What |
|---|---|---|
| `src/app/profile/scoring.py` | **update** | Rename `_PHASE_1_TOPICS`, `_PHASE_2_TOPICS`, `_PHASE_3_TOPICS` to public names (remove underscore); update all internal references in the same file |
| `src/agents/nodes/assess.py` | **update** | Import public phase topic sets; rewrite `_select_test_slug()` to filter eligible slugs by `user_level` before selecting |

No new files. No schema changes.

---

## Implementation Detail

### scoring.py — make phase topic sets public

```python
# Before:
_PHASE_1_TOPICS: frozenset[str] = frozenset({"embeddings_and_similarity", "rag_pipeline_architecture"})
_PHASE_2_TOPICS: frozenset[str] = frozenset({"chunking_strategies", "vector_databases", "retrieval_methods", "context_and_prompting"})
_PHASE_3_TOPICS: frozenset[str] = frozenset({"evaluation_and_metrics", "production_patterns"})

# After (same values, public names):
PHASE_1_TOPICS: frozenset[str] = frozenset({"embeddings_and_similarity", "rag_pipeline_architecture"})
PHASE_2_TOPICS: frozenset[str] = frozenset({"chunking_strategies", "vector_databases", "retrieval_methods", "context_and_prompting"})
PHASE_3_TOPICS: frozenset[str] = frozenset({"evaluation_and_metrics", "production_patterns"})
```

All internal references in scoring.py (`_phase_1_passed`, `_phase_2_passed`, `_phase_3_passed`)
must also be updated to use the new public names.

### assess.py — rewrite `_select_test_slug`

```python
from app.profile.scoring import PHASE_1_TOPICS, PHASE_2_TOPICS, PHASE_3_TOPICS

_ALL_TOPICS: frozenset[str] = PHASE_1_TOPICS | PHASE_2_TOPICS | PHASE_3_TOPICS

_LEVEL_TO_PHASE: dict[str, frozenset[str]] = {
    "novice":       PHASE_1_TOPICS,
    "beginner":     PHASE_1_TOPICS,
    "intermediate": PHASE_2_TOPICS,
    "advanced":     PHASE_3_TOPICS,
    "expert":       _ALL_TOPICS,   # cycles canonically Phase 1 → 2 → 3
}

# Canonical ordering across all phases — Phase 1 first, Phase 3 last
_ORDERED_SLUGS: list[str] = [
    "embeddings_and_similarity",
    "rag_pipeline_architecture",
    "chunking_strategies",
    "vector_databases",
    "retrieval_methods",
    "context_and_prompting",
    "evaluation_and_metrics",
    "production_patterns",
]

def _select_test_slug(state: AgentState) -> str | None:
    user_level: str = state.get("user_level") or "novice"
    eligible: frozenset[str] = _LEVEL_TO_PHASE.get(user_level, PHASE_1_TOPICS)

    # Priority 1: identified gaps within the eligible phase
    gaps: list[str] = state.get("identified_gaps") or []
    for slug in gaps:
        if slug in eligible and slug in VALID_MODULE_SLUGS:
            return slug

    # Priority 2: canonical ordering within the eligible phase
    for slug in _ORDERED_SLUGS:
        if slug in eligible and slug in VALID_MODULE_SLUGS:
            return slug

    return None
```

---

## Quality Gate Triage

| Reviewer | Decision | Reason |
|---|---|---|
| Viktor | **run** | Logic change in assess_node — routing correctness, type safety |
| Sage | **skip** | No auth, secrets, or external API calls |
| Quinn | **skip** | Wave runs at Commit 35 (per every-5-commit cadence); coverage accumulated |
| Mira | **skip** | Internal AI routing — no user-facing behavior visible yet (UI comes in Commits 37–38) |
| Ryan | **run** | Always runs; one-liner entry (routing logic change, no new architectural pattern) |

---

## Test Gate

Existing test suite must pass. Nova must add or extend tests for `_select_test_slug`:
- novice → returns only Phase 1 slugs
- beginner → returns only Phase 1 slugs
- intermediate → returns only Phase 2 slugs
- advanced → returns only Phase 3 slugs
- expert → returns Phase 1 slugs first (canonical ordering), not Phase 3
- identified gap within the eligible phase is returned before canonical fallback
- identified gap from a non-eligible phase is skipped
- None returned only when VALID_MODULE_SLUGS is empty

---

## Handoff Outputs

After this commit, Nova must write to her worklog:

**→ Nova (Commit 35 `mcq-assessment-engine`):**
- `PHASE_1_TOPICS`, `PHASE_2_TOPICS`, `PHASE_3_TOPICS` are now public — import from `app.profile.scoring`
- `_select_test_slug` is phase-gated on `user_level` — MCQ engine inherits this gate automatically
- No new AgentState fields — phase gate uses `user_level` already present

---

## Viktor Pre-Brief

Viktor will check:
- All collection types are explicitly typed (`frozenset[str]`, `list[str]`, `dict[str, frozenset[str]]`)
- `_LEVEL_TO_PHASE` covers all 5 Literal values (`novice`, `beginner`, `intermediate`, `advanced`, `expert`)
- Default fallback in `_LEVEL_TO_PHASE.get()` is `PHASE_1_TOPICS` (most conservative)
- `assess_node` writes only to its declared AgentState keys — no new writes added by this commit
- Internal scoring.py references updated consistently (no remaining `_PHASE_X_TOPICS` references)
