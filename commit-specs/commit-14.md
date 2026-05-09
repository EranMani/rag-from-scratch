# Commit 14 Spec — `topic-scoring-service`
> **Project:** rag-from-scratch · **Assignee:** Rex · **Load only for the active commit.**

---

### Commit 14 — `topic-scoring-service`

**Commit message:** `feat: topic scoring service — TopicScoreUpdate interface and tests`

**Body:**
Pure-function scoring service. Nova's `update_profile_node` (Commit 15) imports and
calls this. The typed interface is the contract between Rex's domain (profile DB)
and Nova's domain (LangGraph nodes). It ships as a named deliverable.

`TopicScoreUpdate` TypedDict:
```python
class TopicScoreUpdate(TypedDict):
    topic_scores: dict[str, float]   # full updated scores (all modules)
    strengths:    list[str]           # module slugs with score >= 0.7
    gaps:         list[str]           # module slugs with score <= 0.3
    mastery_level: str                # computed deterministically from avg score
```

`compute_topic_scores(current_profile: dict, assessed_topics: dict[str, float], interaction_count: int) -> TopicScoreUpdate`
- Pure function — no DB calls inside
- Merges `assessed_topics` deltas into existing `topic_scores`
- Computes `mastery_level` from average of all topic scores (deterministic formula)
- Returns full updated `TopicScoreUpdate`

`get_mastery_level(topic_scores: dict[str, float]) -> str`
- Standalone helper: novice < 0.2, beginner 0.2–0.4, intermediate 0.4–0.6, advanced 0.6–0.8, expert >= 0.8

Ships with unit tests in `tests/test_scoring.py`.

**Assignee:** Rex (`rex.stockagent@gmail.com`)

**Files touched:**
- `src/app/profile/scoring.py` (new)
- `tests/test_scoring.py` (new)

**Depends on:** 05

**Testing — done when:**
- [ ] `compute_topic_scores` with a fresh profile and `{"vector_databases": 0.8}` returns correct merged scores
- [ ] `get_mastery_level({"rag_fundamentals": 0.9, "vector_databases": 0.85})` returns `"expert"`
- [ ] Function is pure: same inputs always produce same outputs
- [ ] Invalid module slug in `assessed_topics` is ignored gracefully (not raised)
