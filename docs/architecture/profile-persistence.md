# Profile Persistence — Bridging AI Scores to Database

## Core Concept

The `update_profile_node` is a **side-effect node**: it writes to the database but returns `{}` (no state mutation). This pattern cleanly separates AI computation (upstream nodes) from persistence (this terminal node).

## The Side-Effect Node Pattern

```python
def update_profile_node(state: AgentState) -> dict[str, Any]:
    # ... DB writes ...
    return {}  # never modifies AgentState
```

Why return empty?
- The graph's state machine remains the single source of truth for in-flight data
- DB writes are isolated — if they fail, state is unaffected
- Makes the node independently testable (mock the DB, assert it was called)

## Defensive Persistence

### Fast-Exit Paths

Before touching the database, guard against invalid states:

1. **Anonymous user** (`user_id is None`) → return `{}` immediately
2. **Missing profile row** → log warning, return `{}` (profile creation is the auth layer's responsibility, not this node's)

### Error Path: Eventual Consistency

When `assessment_error=True`:
- Only increment `interaction_count` and update `last_activity_at`
- Never touch scores — prevents corrupting the profile with failed assessment data
- The activity log stays accurate even when scoring fails

This is **eventual consistency by design**: the system prioritizes data integrity over completeness. A missed score update is recoverable on the next turn; a corrupted score is not.

## The Scoring Formula

Source of truth: `knowledge-base/curriculum/gates.md`

```
topic_score = 0.7 * current_session_score + 0.3 * best_prior_session_score
```

- If no prior session exists: `topic_score = current_session_score`
- Topics with no sessions: score = `None` (not 0.0 — absence of data is different from zero performance)
- Session scores outside [0.0, 1.0] are clamped before storage

This is a **spaced-repetition weighting**: recent performance matters more (70%), but historical best prevents a single bad session from wiping progress.

## Phase Gates for Mastery Levels

Mastery level is derived deterministically from topic scores:

| Level | Requirement |
|-------|-------------|
| Expert | Phase 1 + Phase 2 + Phase 3 all passed |
| Advanced | Phase 1 + Phase 2 passed |
| Intermediate | Phase 1 passed |
| Beginner | At least one Phase 1 topic has a non-null score |
| Novice | No scores recorded |

Phase thresholds:
- Phase 1 (fundamentals): all topics >= 0.70
- Phase 2 (core): all topics >= 0.70 AND mean >= 0.75
- Phase 3 (advanced): all topics >= 0.75

Evaluation order is expert → novice; first match wins.

## Separation of Concerns

The persistence layer is split into three modules:

| Module | Responsibility | Side Effects |
|--------|---------------|--------------|
| `scoring.py` | Pure scoring math, phase gates, mastery level | None — no DB, no imports beyond typing |
| `db.py` | SQLite CRUD, JSON serialization, migrations | DB reads/writes |
| `update_profile.py` | Orchestration: reads state, calls scoring, calls DB | DB write via `db.py` |

This means:
- Scoring logic is testable with plain dicts (no DB fixtures needed)
- DB layer can be swapped (SQLite → Postgres) without touching scoring
- The node only orchestrates — it doesn't own any computation

## SQL Injection Prevention

```python
_ALLOWED_PROFILE_COLUMNS: frozenset[str] = frozenset({
    "mastery_level", "interaction_count", "topic_scores", ...
})
```

Column names are interpolated into the SQL `SET` clause. The allowlist prevents a caller-supplied key from becoming a structural injection path. Any unknown column raises `ValueError` before the query executes.

## Synchronous Node in an Async Graph

`update_profile_node` is synchronous (SQLite doesn't benefit from async). It's called via `asyncio.to_thread()` at the graph invocation level. Important: never introduce nested thread dispatch or asyncio calls inside this node — it would deadlock.

## Key Takeaway

Profile persistence in an AI system requires:
- Clear boundaries between scoring (pure functions) and storage (side effects)
- Defensive guards that prevent bad data from reaching the DB
- Eventual consistency design — prioritize data integrity over completeness
- The side-effect node pattern: write to external systems, but never mutate graph state
