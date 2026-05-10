"""
Tests for Commit 14 — topic-scoring-service.

Coverage targets:
1. compute_topic_scores with a fresh profile and {"vector_databases": 0.8} returns
   merged scores, correct strengths, and the right mastery level.
2. get_mastery_level({"rag_fundamentals": 0.9, "vector_databases": 0.85}) returns "expert".
3. Purity test: same inputs always produce same outputs (call twice, assert equal).
4. Invalid module slug in assessed_topics is ignored — no exception raised, valid scores processed.

Design notes:
- scoring.py is a pure-function module: no DB, no FastAPI imports, no side effects.
  These tests require no fixtures, no monkeypatching, no temp DB.
- All tests call the public API only: compute_topic_scores and get_mastery_level.
"""

import pytest

from app.profile.scoring import TopicScoreUpdate, compute_topic_scores, get_mastery_level


# ---------------------------------------------------------------------------
# Test 1 — compute_topic_scores with fresh profile returns correct output
# ---------------------------------------------------------------------------

class TestComputeTopicScoresFreshProfile:
    """Fresh profile (topic_scores={}) merged with a single assessed topic."""

    def test_merged_scores_contain_assessed_topic(self):
        profile = {"topic_scores": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.8}, interaction_count=1)

        assert result["topic_scores"].get("vector_databases") == 0.8, (
            f"merged topic_scores must include vector_databases=0.8, "
            f"got {result['topic_scores']!r}"
        )

    def test_strengths_includes_high_score_topic(self):
        profile = {"topic_scores": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.8}, interaction_count=1)

        assert "vector_databases" in result["strengths"], (
            f"vector_databases (score=0.8 >= 0.7) must appear in strengths, "
            f"got strengths={result['strengths']!r}"
        )

    def test_gaps_is_empty_for_high_score(self):
        profile = {"topic_scores": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.8}, interaction_count=1)

        assert result["gaps"] == [], (
            f"gaps must be empty when only score is 0.8 (> 0.3), "
            f"got gaps={result['gaps']!r}"
        )

    def test_mastery_level_reflects_merged_average(self):
        # avg of {vector_databases: 0.8} = 0.8 → "expert"
        profile = {"topic_scores": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.8}, interaction_count=1)

        assert result["mastery_level"] == "expert", (
            f"mastery_level for avg=0.8 must be 'expert', got {result['mastery_level']!r}"
        )

    def test_return_type_is_topic_score_update(self):
        profile = {"topic_scores": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.8}, interaction_count=1)

        assert isinstance(result, dict), (
            f"TopicScoreUpdate must be a dict (TypedDict), got {type(result)!r}"
        )
        for key in ("topic_scores", "strengths", "gaps", "mastery_level"):
            assert key in result, (
                f"TopicScoreUpdate missing required key '{key}' — got keys: {list(result)!r}"
            )


# ---------------------------------------------------------------------------
# Test 2 — get_mastery_level returns "expert" for high average
# ---------------------------------------------------------------------------

class TestGetMasteryLevel:
    """get_mastery_level must return correct level for each threshold band."""

    def test_expert_level(self):
        scores = {"rag_fundamentals": 0.9, "vector_databases": 0.85}
        result = get_mastery_level(scores)

        assert result == "expert", (
            f"avg=0.875 (>=0.8) must return 'expert', got {result!r}"
        )

    def test_novice_for_empty_dict(self):
        result = get_mastery_level({})

        assert result == "novice", (
            f"empty dict must return 'novice' (no scores = no knowledge), got {result!r}"
        )

    def test_novice_threshold(self):
        result = get_mastery_level({"a": 0.1})

        assert result == "novice", (
            f"avg=0.1 (<0.2) must return 'novice', got {result!r}"
        )

    def test_beginner_threshold(self):
        result = get_mastery_level({"a": 0.3})

        assert result == "beginner", (
            f"avg=0.3 (0.2<=avg<0.4) must return 'beginner', got {result!r}"
        )

    def test_intermediate_threshold(self):
        result = get_mastery_level({"a": 0.5})

        assert result == "intermediate", (
            f"avg=0.5 (0.4<=avg<0.6) must return 'intermediate', got {result!r}"
        )

    def test_advanced_threshold(self):
        result = get_mastery_level({"a": 0.7})

        assert result == "advanced", (
            f"avg=0.7 (0.6<=avg<0.8) must return 'advanced', got {result!r}"
        )


# ---------------------------------------------------------------------------
# Test 3 — Purity: same inputs always produce same outputs
# ---------------------------------------------------------------------------

class TestComputeTopicScoresPurity:
    """Pure function invariant: identical inputs must produce identical outputs."""

    def test_same_inputs_same_outputs(self):
        profile = {"topic_scores": {"rag_fundamentals": 0.5}}
        assessed = {"vector_databases": 0.6, "embeddings": 0.4}

        result_a = compute_topic_scores(profile, assessed, interaction_count=3)
        result_b = compute_topic_scores(profile, assessed, interaction_count=3)

        assert result_a == result_b, (
            f"compute_topic_scores must be a pure function — "
            f"same inputs produced different outputs.\n"
            f"  First call:  {result_a!r}\n"
            f"  Second call: {result_b!r}"
        )

    def test_does_not_mutate_current_profile(self):
        """Merging must not mutate the incoming profile dict."""
        original_scores = {"rag_fundamentals": 0.5}
        profile = {"topic_scores": original_scores}

        compute_topic_scores(profile, {"vector_databases": 0.8}, interaction_count=1)

        assert profile["topic_scores"] == {"rag_fundamentals": 0.5}, (
            f"compute_topic_scores must not mutate current_profile['topic_scores'] — "
            f"original was {{'rag_fundamentals': 0.5}}, now {profile['topic_scores']!r}"
        )


# ---------------------------------------------------------------------------
# Test 4 — Invalid module slugs in assessed_topics are ignored gracefully
# ---------------------------------------------------------------------------

class TestInvalidSlugsIgnored:
    """Invalid slugs (non-float values) must not raise; valid scores must still process."""

    def test_non_float_value_is_ignored(self):
        """A slug with a non-numeric value must be silently skipped."""
        profile = {"topic_scores": {}}
        # "bad_slug" has a string value — not a float
        assessed = {"bad_slug": "not-a-number", "vector_databases": 0.75}

        # Must not raise
        result = compute_topic_scores(profile, assessed, interaction_count=1)

        assert "bad_slug" not in result["topic_scores"], (
            f"bad_slug with non-numeric value must be excluded from topic_scores, "
            f"got {result['topic_scores']!r}"
        )

    def test_valid_scores_still_processed_alongside_invalid(self):
        """Valid slugs must appear in output even when invalid slugs are also present."""
        profile = {"topic_scores": {}}
        assessed = {"bad_slug": "not-a-number", "vector_databases": 0.75}

        result = compute_topic_scores(profile, assessed, interaction_count=1)

        assert result["topic_scores"].get("vector_databases") == 0.75, (
            f"vector_databases=0.75 must appear in topic_scores even when invalid slug present, "
            f"got {result['topic_scores']!r}"
        )

    def test_none_value_is_ignored(self):
        """A slug with None value must be silently skipped."""
        profile = {"topic_scores": {}}
        assessed = {"null_slug": None, "embeddings": 0.4}

        result = compute_topic_scores(profile, assessed, interaction_count=1)

        assert "null_slug" not in result["topic_scores"], (
            f"null_slug with None value must be excluded, got {result['topic_scores']!r}"
        )
        assert result["topic_scores"].get("embeddings") == 0.4, (
            f"embeddings=0.4 must be present alongside excluded null_slug, "
            f"got {result['topic_scores']!r}"
        )

    def test_no_exception_on_all_invalid_slugs(self):
        """All invalid values must produce an empty result, not an exception."""
        profile = {"topic_scores": {}}
        assessed = {"a": "string", "b": None, "c": [1, 2]}

        # Must not raise
        result = compute_topic_scores(profile, assessed, interaction_count=0)

        assert result["topic_scores"] == {}, (
            f"All invalid values must produce empty topic_scores, "
            f"got {result['topic_scores']!r}"
        )
        assert result["mastery_level"] == "novice", (
            f"No valid scores must yield mastery_level='novice', "
            f"got {result['mastery_level']!r}"
        )


# ---------------------------------------------------------------------------
# Test 5 — Additive delta merge semantics
# ---------------------------------------------------------------------------

class TestDeltaMergeSemantics:
    """assessed_topics values are deltas; they are added to existing scores, not used as replacements."""

    def test_positive_delta_adds_to_existing_score(self):
        """existing=0.5 + delta=+0.3 → 0.8"""
        profile = {"topic_scores": {"rag_fundamentals": 0.5}}
        result = compute_topic_scores(profile, {"rag_fundamentals": 0.3}, interaction_count=1)

        assert abs(result["topic_scores"]["rag_fundamentals"] - 0.8) < 1e-9, (
            f"existing=0.5 + delta=0.3 must yield 0.8, "
            f"got {result['topic_scores']['rag_fundamentals']!r}"
        )

    def test_negative_delta_subtracts_from_existing_score(self):
        """existing=0.5 + delta=-0.2 → 0.3 (not clamped to 0.5)"""
        profile = {"topic_scores": {"rag_fundamentals": 0.5}}
        result = compute_topic_scores(profile, {"rag_fundamentals": -0.2}, interaction_count=1)

        assert abs(result["topic_scores"]["rag_fundamentals"] - 0.3) < 1e-9, (
            f"existing=0.5 + delta=-0.2 must yield 0.3, "
            f"got {result['topic_scores']['rag_fundamentals']!r}"
        )

    def test_delta_clamps_upper_bound(self):
        """existing=0.7 + delta=+0.9 → 1.0 (not 1.6)"""
        profile = {"topic_scores": {"embeddings": 0.7}}
        result = compute_topic_scores(profile, {"embeddings": 0.9}, interaction_count=1)

        assert result["topic_scores"]["embeddings"] == 1.0, (
            f"existing=0.7 + delta=0.9 must clamp to 1.0, "
            f"got {result['topic_scores']['embeddings']!r}"
        )

    def test_delta_clamps_lower_bound(self):
        """existing=0.2 + delta=-0.9 → 0.0 (not -0.7)"""
        profile = {"topic_scores": {"embeddings": 0.2}}
        result = compute_topic_scores(profile, {"embeddings": -0.9}, interaction_count=1)

        assert result["topic_scores"]["embeddings"] == 0.0, (
            f"existing=0.2 + delta=-0.9 must clamp to 0.0, "
            f"got {result['topic_scores']['embeddings']!r}"
        )

    def test_new_slug_with_delta_uses_zero_as_base(self):
        """New slug (no existing score) + delta=+0.6 → 0.6"""
        profile = {"topic_scores": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.6}, interaction_count=1)

        assert abs(result["topic_scores"]["vector_databases"] - 0.6) < 1e-9, (
            f"new slug with delta=0.6 (base=0.0) must yield 0.6, "
            f"got {result['topic_scores']['vector_databases']!r}"
        )

    def test_existing_slug_not_in_assessed_is_preserved(self):
        """Slugs present in current_profile but absent from assessed_topics survive the merge."""
        profile = {"topic_scores": {"rag_fundamentals": 0.5, "embeddings": 0.4}}
        result = compute_topic_scores(profile, {"rag_fundamentals": 0.1}, interaction_count=1)

        assert abs(result["topic_scores"].get("embeddings", -1) - 0.4) < 1e-9, (
            f"embeddings not in assessed_topics must survive merge unchanged at 0.4, "
            f"got {result['topic_scores']!r}"
        )

    def test_invalid_value_in_assessed_topics_silently_dropped(self):
        """Non-numeric delta value must be ignored — existing score must remain unchanged."""
        profile = {"topic_scores": {"rag_fundamentals": 0.5}}
        result = compute_topic_scores(profile, {"rag_fundamentals": "bad"}, interaction_count=1)

        assert abs(result["topic_scores"]["rag_fundamentals"] - 0.5) < 1e-9, (
            f"invalid delta must be dropped; existing score 0.5 must remain unchanged, "
            f"got {result['topic_scores']!r}"
        )


# ---------------------------------------------------------------------------
# Test 6 — Mastery level boundary verification
# ---------------------------------------------------------------------------

class TestMasteryLevelBoundaries:
    """Verify mastery level thresholds use strict less-than (not less-than-or-equal)."""

    def test_empty_topic_scores_yields_novice(self):
        """compute_topic_scores with no valid scores must yield mastery_level='novice'."""
        profile = {"topic_scores": {}}
        result = compute_topic_scores(profile, {}, interaction_count=0)

        assert result["mastery_level"] == "novice", (
            f"empty topic_scores must yield 'novice', got {result['mastery_level']!r}"
        )

    def test_score_exactly_02_yields_beginner_not_novice(self):
        """avg=0.2 is the novice/beginner boundary; 0.2 must be 'beginner' (threshold is avg < 0.2)."""
        result = get_mastery_level({"a": 0.2})

        assert result == "beginner", (
            f"avg=0.2 must be 'beginner' (novice threshold is avg < 0.2), got {result!r}"
        )

    def test_score_exactly_08_yields_expert(self):
        """avg=0.8 is the advanced/expert boundary; 0.8 must be 'expert' (advanced threshold is avg < 0.8)."""
        result = get_mastery_level({"a": 0.8})

        assert result == "expert", (
            f"avg=0.8 must be 'expert' (advanced threshold is avg < 0.8, so 0.8 passes through), got {result!r}"
        )


# ---------------------------------------------------------------------------
# Test 7 — Strengths and gaps extraction
# ---------------------------------------------------------------------------

class TestStrengthsAndGaps:
    """Strengths (>=0.7) and gaps (<=0.3) are extracted from the merged scores."""

    def test_strengths_contain_all_high_scores(self):
        """All slugs with merged score >= 0.7 appear in strengths."""
        profile = {"topic_scores": {"rag_fundamentals": 0.5}}
        # delta +0.2 → rag_fundamentals = 0.7; new slug embeddings = 0.8
        result = compute_topic_scores(
            profile,
            {"rag_fundamentals": 0.2, "embeddings": 0.8},
            interaction_count=1,
        )

        assert "rag_fundamentals" in result["strengths"], (
            f"rag_fundamentals at 0.7 must be in strengths (>=0.7), "
            f"got strengths={result['strengths']!r}"
        )
        assert "embeddings" in result["strengths"], (
            f"embeddings at 0.8 must be in strengths (>=0.7), "
            f"got strengths={result['strengths']!r}"
        )

    def test_gaps_contain_all_low_scores(self):
        """All slugs with merged score <= 0.3 appear in gaps."""
        profile = {"topic_scores": {"rag_fundamentals": 0.5}}
        # delta -0.3 → rag_fundamentals = 0.2; new slug embeddings = 0.1
        result = compute_topic_scores(
            profile,
            {"rag_fundamentals": -0.3, "embeddings": 0.1},
            interaction_count=1,
        )

        assert "rag_fundamentals" in result["gaps"], (
            f"rag_fundamentals at 0.2 must be in gaps (<=0.3), "
            f"got gaps={result['gaps']!r}"
        )
        assert "embeddings" in result["gaps"], (
            f"embeddings at 0.1 must be in gaps (<=0.3), "
            f"got gaps={result['gaps']!r}"
        )

    def test_clamped_lower_bound_appears_in_gaps(self):
        """A score clamped to 0.0 must appear in gaps."""
        profile = {"topic_scores": {"embeddings": 0.2}}
        result = compute_topic_scores(profile, {"embeddings": -0.9}, interaction_count=1)

        assert "embeddings" in result["gaps"], (
            f"embeddings clamped to 0.0 must appear in gaps, "
            f"got gaps={result['gaps']!r}"
        )

    def test_clamped_upper_bound_appears_in_strengths(self):
        """A score clamped to 1.0 must appear in strengths."""
        profile = {"topic_scores": {"embeddings": 0.7}}
        result = compute_topic_scores(profile, {"embeddings": 0.9}, interaction_count=1)

        assert "embeddings" in result["strengths"], (
            f"embeddings clamped to 1.0 must appear in strengths, "
            f"got strengths={result['strengths']!r}"
        )
