"""
Tests for Commit 25 — profile-scoring-rewrite.

Coverage targets (spec gates from commit-25.md and knowledge-base/curriculum/gates.md):

1. VALID_MODULE_SLUGS has exactly 8 canonical entries.
2. TopicScoresDelta has exactly 8 fields (no rag_fundamentals, no langchain).
3. compute_topic_scores uses spaced-repetition formula, not additive delta.
4. First session for a topic: topic_score = current_session_score.
5. Subsequent session for a topic: topic_score = 0.7 * session + 0.3 * best_prior.
6. best_prior_session_score is the historical maximum, not the most recent.
7. None topic scores fail gate checks; 0.0 is distinct from None.
8. get_mastery_level uses phase gate state, not score averages.
9. All phase gate boundaries (phase 1 / 2 / 3) correct.
10. Purity: same inputs → same outputs; no mutation of input profile.
11. Invalid session score values skipped without raising.
12. Strengths >= 0.7; gaps <= 0.3; None scores excluded from both.

Design notes:
- scoring.py is pure-function: no DB, no FastAPI. No fixtures needed.
- Invariant: compute_topic_scores returns topic_score = new score (not a delta to add).
"""

import pytest

from app.profile.scoring import (
    TopicScoreUpdate,
    _phase_1_passed,
    compute_topic_scores,
    get_mastery_level,
)
from agents.state import VALID_MODULE_SLUGS, TopicScoresDelta


# ---------------------------------------------------------------------------
# Schema gate tests
# ---------------------------------------------------------------------------

class TestSchemaGates:
    """VALID_MODULE_SLUGS and TopicScoresDelta match the 8-slug canonical set."""

    def test_valid_module_slugs_has_exactly_8_entries(self) -> None:
        assert len(VALID_MODULE_SLUGS) == 8, (
            f"VALID_MODULE_SLUGS must have exactly 8 entries, got {len(VALID_MODULE_SLUGS)}: {VALID_MODULE_SLUGS}"
        )

    def test_valid_module_slugs_canonical_set(self) -> None:
        expected = {
            "embeddings_and_similarity",
            "rag_pipeline_architecture",
            "chunking_strategies",
            "vector_databases",
            "retrieval_methods",
            "context_and_prompting",
            "evaluation_and_metrics",
            "production_patterns",
        }
        assert VALID_MODULE_SLUGS == expected, (
            f"VALID_MODULE_SLUGS mismatch.\nExpected: {expected}\nGot: {VALID_MODULE_SLUGS}"
        )

    def test_valid_module_slugs_excludes_rag_fundamentals(self) -> None:
        assert "rag_fundamentals" not in VALID_MODULE_SLUGS, (
            "rag_fundamentals must not be in VALID_MODULE_SLUGS (dropped slug)"
        )

    def test_valid_module_slugs_excludes_langchain(self) -> None:
        assert "langchain" not in VALID_MODULE_SLUGS, (
            "langchain must not be in VALID_MODULE_SLUGS (dropped slug)"
        )

    def test_topic_scores_delta_has_exactly_8_fields(self) -> None:
        delta = TopicScoresDelta()
        fields = set(delta.model_fields.keys())
        assert len(fields) == 8, (
            f"TopicScoresDelta must have exactly 8 fields, got {len(fields)}: {fields}"
        )

    def test_topic_scores_delta_excludes_rag_fundamentals(self) -> None:
        delta = TopicScoresDelta()
        assert "rag_fundamentals" not in delta.model_fields, (
            "TopicScoresDelta must not have rag_fundamentals field"
        )

    def test_topic_scores_delta_excludes_langchain(self) -> None:
        delta = TopicScoresDelta()
        assert "langchain" not in delta.model_fields, (
            "TopicScoresDelta must not have langchain field"
        )

    def test_topic_scores_delta_has_rag_pipeline_architecture(self) -> None:
        delta = TopicScoresDelta()
        assert "rag_pipeline_architecture" in delta.model_fields, (
            "TopicScoresDelta must have rag_pipeline_architecture field"
        )

    def test_topic_scores_delta_has_all_new_slugs(self) -> None:
        delta = TopicScoresDelta()
        for slug in ("embeddings_and_similarity", "context_and_prompting", "evaluation_and_metrics"):
            assert slug in delta.model_fields, (
                f"TopicScoresDelta must have {slug} field"
            )


# ---------------------------------------------------------------------------
# Spaced-repetition formula tests
# ---------------------------------------------------------------------------

class TestFirstSessionFormula:
    """First session for a topic: topic_score = current_session_score (no prior)."""

    def test_first_session_equals_session_score(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.8})
        assert abs(result["topic_scores"]["vector_databases"] - 0.8) < 1e-9, (
            f"First session with score 0.8 must yield topic_score=0.8, "
            f"got {result['topic_scores']['vector_databases']!r}"
        )

    def test_first_session_score_1_0(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"embeddings_and_similarity": 1.0})
        assert abs(result["topic_scores"]["embeddings_and_similarity"] - 1.0) < 1e-9

    def test_first_session_score_0_0(self) -> None:
        """A session score of 0.0 is distinct from None — user was assessed, scored zero."""
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"rag_pipeline_architecture": 0.0})
        score = result["topic_scores"]["rag_pipeline_architecture"]
        assert score == 0.0, (
            f"First session score=0.0 must yield topic_score=0.0, got {score!r}"
        )
        assert score is not None, "topic_score=0.0 must be float, not None"

    def test_none_topics_not_in_delta_remain_none(self) -> None:
        """Topics not in delta keep their existing None score."""
        profile = {"topic_scores": {"chunking_strategies": None}, "session_history": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.7})
        assert result["topic_scores"].get("chunking_strategies") is None, (
            "chunking_strategies with None score must remain None when not in delta"
        )


class TestSpacedRepetitionFormula:
    """Subsequent sessions: topic_score = 0.7 * current + 0.3 * best_prior."""

    def test_second_session_formula(self) -> None:
        """Prior session=0.65, current=0.5 → 0.7*0.5 + 0.3*0.65 = 0.545."""
        profile = {
            "topic_scores": {"vector_databases": 0.65},
            "session_history": {"vector_databases": [0.65]},
        }
        result = compute_topic_scores(profile, {"vector_databases": 0.5})
        expected = 0.7 * 0.5 + 0.3 * 0.65
        actual = result["topic_scores"]["vector_databases"]
        assert abs(actual - expected) < 1e-9, (
            f"0.7*0.5 + 0.3*0.65 must = {expected:.4f}, got {actual!r}"
        )

    def test_best_prior_is_maximum_not_most_recent(self) -> None:
        """Session history [0.5, 0.9, 0.6] → best_prior=0.9, NOT 0.6 (most recent)."""
        profile = {
            "topic_scores": {"retrieval_methods": 0.72},
            "session_history": {"retrieval_methods": [0.5, 0.9, 0.6]},
        }
        result = compute_topic_scores(profile, {"retrieval_methods": 0.8})
        expected = 0.7 * 0.8 + 0.3 * 0.9  # best_prior = max([0.5, 0.9, 0.6]) = 0.9
        actual = result["topic_scores"]["retrieval_methods"]
        assert abs(actual - expected) < 1e-9, (
            f"best_prior must be max of history (0.9), not most recent (0.6). "
            f"Expected {expected:.4f}, got {actual!r}"
        )

    def test_history_appended_after_session(self) -> None:
        """Current session score is appended to session_history for future best_prior lookups."""
        profile = {
            "topic_scores": {"chunking_strategies": 0.7},
            "session_history": {"chunking_strategies": [0.7]},
        }
        result = compute_topic_scores(profile, {"chunking_strategies": 0.85})
        history = result["session_history"]["chunking_strategies"]
        assert 0.85 in history, (
            f"Current session score 0.85 must be appended to session_history, got {history!r}"
        )

    def test_concrete_example_from_spec(self) -> None:
        """Spec example: 4 questions [correct, partial, partial, incorrect] → session=0.5.
        best_prior=0.65 → topic_score = 0.7*0.5 + 0.3*0.65 = 0.545."""
        profile = {
            "topic_scores": {"embeddings_and_similarity": 0.65},
            "session_history": {"embeddings_and_similarity": [0.65]},
        }
        result = compute_topic_scores(profile, {"embeddings_and_similarity": 0.5})
        expected = 0.35 + 0.195  # 0.7*0.5 + 0.3*0.65
        actual = result["topic_scores"]["embeddings_and_similarity"]
        assert abs(actual - expected) < 1e-9, (
            f"Spec example: expected 0.545, got {actual!r}"
        )

    def test_not_additive_to_existing_score(self) -> None:
        """session score 0.8 is NOT added to existing 0.6 — it IS the current_session_score."""
        profile = {
            "topic_scores": {"vector_databases": 0.6},
            "session_history": {"vector_databases": [0.6]},
        }
        result = compute_topic_scores(profile, {"vector_databases": 0.8})
        # Correct: 0.7*0.8 + 0.3*0.6 = 0.56 + 0.18 = 0.74
        # Wrong (additive): 0.6 + 0.8 = 1.4 → clamped 1.0
        expected = 0.7 * 0.8 + 0.3 * 0.6
        actual = result["topic_scores"]["vector_databases"]
        assert abs(actual - expected) < 1e-9, (
            f"0.8 is the session score, not a delta. Expected {expected:.4f}, got {actual!r}"
        )


# ---------------------------------------------------------------------------
# None vs 0.0 distinction
# ---------------------------------------------------------------------------

class TestNullVsZeroDistinction:
    """None means unassessed; 0.0 means assessed with zero score. Gate behavior differs."""

    def test_none_topic_fails_phase_1_gate(self) -> None:
        """A Phase 1 topic with None score must fail phase_1_passed check."""
        # Phase 1 requires embeddings_and_similarity AND rag_pipeline_architecture >= 0.70
        scores: dict = {
            "embeddings_and_similarity": None,
            "rag_pipeline_architecture": 0.80,
            "chunking_strategies": 0.80,
            "vector_databases": 0.80,
            "retrieval_methods": 0.80,
            "context_and_prompting": 0.80,
            "evaluation_and_metrics": 0.80,
            "production_patterns": 0.80,
        }
        level = get_mastery_level(scores)
        assert level != "expert", "None Phase 1 score must prevent expert level"
        assert level != "advanced", "None Phase 1 score must prevent advanced level"
        assert level != "intermediate", "None Phase 1 score must prevent intermediate level"

    def test_zero_topic_score_is_not_none(self) -> None:
        """A topic score of exactly 0.0 is a valid non-null score."""
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"embeddings_and_similarity": 0.0})
        score = result["topic_scores"]["embeddings_and_similarity"]
        assert score is not None, "0.0 session score must produce 0.0 topic score, not None"
        assert score == 0.0

    def test_zero_topic_fails_gate_below_threshold(self) -> None:
        """0.0 score fails a >= 0.70 gate check."""
        scores: dict = {
            "embeddings_and_similarity": 0.0,
            "rag_pipeline_architecture": 0.75,
        }
        result = get_mastery_level(scores)
        # Phase 1 not passed; Phase 1 topic has non-null score → beginner
        assert result == "beginner", (
            f"0.0 score on embeddings_and_similarity must produce 'beginner', got {result!r}"
        )

    def test_unassessed_topic_is_novice(self) -> None:
        """Profile with no scores at all → novice (all Phase 1 topics are None)."""
        result = get_mastery_level({})
        assert result == "novice", (
            f"Empty topic scores must yield 'novice', got {result!r}"
        )

    def test_none_scores_not_in_strengths_or_gaps(self) -> None:
        """None scores must not appear in strengths or gaps."""
        profile = {
            "topic_scores": {"embeddings_and_similarity": None},
            "session_history": {},
        }
        result = compute_topic_scores(profile, {"vector_databases": 0.8})
        assert "embeddings_and_similarity" not in result["strengths"], (
            "None score must not appear in strengths"
        )
        assert "embeddings_and_similarity" not in result["gaps"], (
            "None score must not appear in gaps"
        )


# ---------------------------------------------------------------------------
# get_mastery_level — phase gate state mapping
# ---------------------------------------------------------------------------

class TestGetMasteryLevel:
    """get_mastery_level uses phase gate state, evaluated expert → novice."""

    def _all_passing(self) -> dict:
        """All 8 topics at a score that passes all phase gates."""
        return {
            "embeddings_and_similarity": 0.80,
            "rag_pipeline_architecture": 0.80,
            "chunking_strategies": 0.80,
            "vector_databases": 0.80,
            "retrieval_methods": 0.80,
            "context_and_prompting": 0.80,
            "evaluation_and_metrics": 0.80,
            "production_patterns": 0.80,
        }

    def test_novice_all_null(self) -> None:
        """All Phase 1 topics None → novice."""
        result = get_mastery_level({})
        assert result == "novice", f"Empty scores must be novice, got {result!r}"

    def test_novice_only_phase2_assessed(self) -> None:
        """If only Phase 2 topics have scores but Phase 1 is all None → novice."""
        scores: dict = {"chunking_strategies": 0.8, "vector_databases": 0.8}
        result = get_mastery_level(scores)
        assert result == "novice", (
            f"Phase 1 all None (only Phase 2 scored) must be novice, got {result!r}"
        )

    def test_beginner_one_phase1_topic_scored(self) -> None:
        """One Phase 1 topic scored (non-null), phase_1 not passed → beginner."""
        scores: dict = {"embeddings_and_similarity": 0.5}
        result = get_mastery_level(scores)
        assert result == "beginner", (
            f"One Phase 1 topic scored below threshold must be 'beginner', got {result!r}"
        )

    def test_beginner_phase1_partially_failing(self) -> None:
        """Both Phase 1 topics scored but one below 0.70 → beginner."""
        scores: dict = {
            "embeddings_and_similarity": 0.8,
            "rag_pipeline_architecture": 0.60,
        }
        result = get_mastery_level(scores)
        assert result == "beginner", (
            f"Phase 1 partially failing must be 'beginner', got {result!r}"
        )

    def test_intermediate_phase1_passed_phase2_not(self) -> None:
        """phase_1_passed AND phase_2_not_passed → intermediate."""
        scores: dict = {
            "embeddings_and_similarity": 0.75,
            "rag_pipeline_architecture": 0.75,
            "chunking_strategies": 0.60,  # below Phase 2 threshold
        }
        result = get_mastery_level(scores)
        assert result == "intermediate", (
            f"phase_1_passed + phase_2_not_passed must be 'intermediate', got {result!r}"
        )

    def test_intermediate_phase1_exactly_at_threshold(self) -> None:
        """Phase 1 topics at exactly 0.70 → phase_1_passed → intermediate (if phase 2 not passed)."""
        scores: dict = {
            "embeddings_and_similarity": 0.70,
            "rag_pipeline_architecture": 0.70,
        }
        result = get_mastery_level(scores)
        assert result == "intermediate", (
            f"Phase 1 exactly at 0.70 must pass and yield 'intermediate', got {result!r}"
        )

    def test_advanced_phase2_passed_phase3_not(self) -> None:
        """phase_2_passed AND phase_3_not_passed → advanced."""
        scores: dict = {
            "embeddings_and_similarity": 0.80,
            "rag_pipeline_architecture": 0.80,
            "chunking_strategies": 0.80,
            "vector_databases": 0.80,
            "retrieval_methods": 0.80,
            "context_and_prompting": 0.80,
            "evaluation_and_metrics": 0.60,  # below Phase 3 threshold
            "production_patterns": 0.80,
        }
        result = get_mastery_level(scores)
        assert result == "advanced", (
            f"phase_2_passed + phase_3_not_passed must be 'advanced', got {result!r}"
        )

    def test_expert_all_phases_passed(self) -> None:
        """All three phases passed → expert."""
        scores = self._all_passing()
        result = get_mastery_level(scores)
        assert result == "expert", (
            f"All phases passed must be 'expert', got {result!r}"
        )

    def test_phase2_individual_threshold_passes_but_mean_fails(self) -> None:
        """Phase 2 individual per-topic >= 0.70 but mean < 0.75 → phase_2 NOT passed → intermediate."""
        # mean of [0.70, 0.70, 0.70, 0.70] = 0.70 < 0.75
        scores: dict = {
            "embeddings_and_similarity": 0.80,
            "rag_pipeline_architecture": 0.80,
            "chunking_strategies": 0.70,
            "vector_databases": 0.70,
            "retrieval_methods": 0.70,
            "context_and_prompting": 0.70,
        }
        result = get_mastery_level(scores)
        assert result == "intermediate", (
            f"Phase 2 individual pass but mean < 0.75 must still be 'intermediate', got {result!r}"
        )

    def test_phase3_threshold_is_0_75_not_0_70(self) -> None:
        """Phase 3 topics need >= 0.75; a score of 0.70 must NOT pass Phase 3."""
        scores = self._all_passing()
        scores["evaluation_and_metrics"] = 0.70  # below Phase 3 threshold of 0.75
        result = get_mastery_level(scores)
        assert result == "advanced", (
            f"Phase 3 topic at 0.70 (< 0.75) must not pass Phase 3 gate; expected 'advanced', got {result!r}"
        )

    def test_not_using_score_average(self) -> None:
        """A user with 8 topics all at 0.85 (avg=0.85) but Phase 1 not touched → novice.
        This confirms gate-state logic, not average-based logic."""
        # All non-Phase-1 topics scored; Phase 1 topics are None
        scores: dict = {
            "chunking_strategies": 0.85,
            "vector_databases": 0.85,
            "retrieval_methods": 0.85,
            "context_and_prompting": 0.85,
            "evaluation_and_metrics": 0.85,
            "production_patterns": 0.85,
        }
        result = get_mastery_level(scores)
        assert result == "novice", (
            f"Phase 1 all null → novice regardless of other scores. "
            f"Average-based logic would give 'expert'; gate logic gives 'novice'. Got {result!r}"
        )


# ---------------------------------------------------------------------------
# Purity and mutation tests
# ---------------------------------------------------------------------------

class TestComputeTopicScoresPurity:
    """Pure function invariants."""

    def test_same_inputs_same_outputs(self) -> None:
        profile = {"topic_scores": {"vector_databases": 0.6}, "session_history": {"vector_databases": [0.6]}}
        delta = {"vector_databases": 0.8}
        result_a = compute_topic_scores(profile, delta)
        result_b = compute_topic_scores(profile, delta)
        assert result_a["topic_scores"] == result_b["topic_scores"], (
            f"compute_topic_scores must be pure — same inputs produced different outputs."
        )

    def test_does_not_mutate_current_profile(self) -> None:
        original_scores = {"vector_databases": 0.6}
        profile = {"topic_scores": original_scores, "session_history": {}}
        compute_topic_scores(profile, {"vector_databases": 0.8})
        assert profile["topic_scores"] == {"vector_databases": 0.6}, (
            f"compute_topic_scores must not mutate current_profile['topic_scores']. "
            f"Got {profile['topic_scores']!r}"
        )

    def test_does_not_mutate_session_history(self) -> None:
        original_history = {"vector_databases": [0.6]}
        profile = {"topic_scores": {}, "session_history": original_history}
        compute_topic_scores(profile, {"vector_databases": 0.8})
        assert original_history == {"vector_databases": [0.6]}, (
            f"compute_topic_scores must not mutate session_history input. "
            f"Got {original_history!r}"
        )

    def test_return_type_is_topic_score_update(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.8})
        assert isinstance(result, dict)
        for key in ("topic_scores", "session_history", "strengths", "gaps", "mastery_level"):
            assert key in result, f"TopicScoreUpdate missing required key '{key}' — got {list(result)!r}"


# ---------------------------------------------------------------------------
# Invalid input handling
# ---------------------------------------------------------------------------

class TestInvalidSessionScores:
    """Non-numeric session score values are skipped with logging; valid slugs still process."""

    def test_non_float_value_is_ignored(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"bad_slug": "not-a-number", "vector_databases": 0.75})
        assert "bad_slug" not in result["topic_scores"]

    def test_valid_scores_still_processed(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"bad_slug": "not-a-number", "vector_databases": 0.75})
        assert abs(result["topic_scores"].get("vector_databases", -1) - 0.75) < 1e-9

    def test_none_value_is_ignored(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"null_slug": None, "vector_databases": 0.4})
        assert "null_slug" not in result["topic_scores"]

    def test_no_exception_on_all_invalid(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"a": "string", "b": None, "c": [1, 2]})
        assert result["topic_scores"] == {}
        assert result["mastery_level"] == "novice"


# ---------------------------------------------------------------------------
# Strengths and gaps
# ---------------------------------------------------------------------------

class TestStrengthsAndGaps:
    """Strengths >= 0.7; gaps <= 0.3; None scores excluded from both."""

    def test_strengths_contain_high_score_topic(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.8})
        assert "vector_databases" in result["strengths"]

    def test_gaps_contain_low_score_topic(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.2})
        assert "vector_databases" in result["gaps"]

    def test_middle_score_not_in_strengths_or_gaps(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.5})
        assert "vector_databases" not in result["strengths"]
        assert "vector_databases" not in result["gaps"]

    def test_none_scores_excluded_from_both(self) -> None:
        profile = {"topic_scores": {"chunking_strategies": None}, "session_history": {}}
        result = compute_topic_scores(profile, {})
        assert "chunking_strategies" not in result["strengths"]
        assert "chunking_strategies" not in result["gaps"]

    def test_exactly_07_is_in_strengths(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.7})
        assert "vector_databases" in result["strengths"], (
            "score=0.7 (>= 0.7) must be in strengths"
        )

    def test_exactly_03_is_in_gaps(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.3})
        assert "vector_databases" in result["gaps"], (
            "score=0.3 (<= 0.3) must be in gaps"
        )

    def test_existing_none_topic_preserved_in_output(self) -> None:
        """Topics in current_profile with None score survive the merge."""
        profile = {
            "topic_scores": {"evaluation_and_metrics": None},
            "session_history": {},
        }
        result = compute_topic_scores(profile, {"vector_databases": 0.7})
        assert result["topic_scores"].get("evaluation_and_metrics") is None


# ---------------------------------------------------------------------------
# Session history tracking
# ---------------------------------------------------------------------------

class TestSessionHistoryTracking:
    """Session history is correctly updated and used for best_prior computation."""

    def test_session_history_initialized_for_new_topic(self) -> None:
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.7})
        assert "vector_databases" in result["session_history"]
        assert result["session_history"]["vector_databases"] == [0.7]

    def test_multiple_sessions_accumulate_in_history(self) -> None:
        """Three sessions; history grows with each call."""
        profile1 = {"topic_scores": {}, "session_history": {}}
        result1 = compute_topic_scores(profile1, {"vector_databases": 0.6})

        profile2 = {
            "topic_scores": result1["topic_scores"],
            "session_history": result1["session_history"],
        }
        result2 = compute_topic_scores(profile2, {"vector_databases": 0.8})

        profile3 = {
            "topic_scores": result2["topic_scores"],
            "session_history": result2["session_history"],
        }
        result3 = compute_topic_scores(profile3, {"vector_databases": 0.5})

        history = result3["session_history"]["vector_databases"]
        assert len(history) == 3, f"After 3 sessions, history must have 3 entries, got {history!r}"
        assert 0.6 in history and 0.8 in history and 0.5 in history

    def test_best_prior_uses_max_across_all_sessions(self) -> None:
        """History [0.4, 0.9, 0.5] → best_prior=0.9."""
        profile = {
            "topic_scores": {"vector_databases": 0.75},
            "session_history": {"vector_databases": [0.4, 0.9, 0.5]},
        }
        result = compute_topic_scores(profile, {"vector_databases": 0.7})
        expected = 0.7 * 0.7 + 0.3 * 0.9  # best_prior = 0.9
        actual = result["topic_scores"]["vector_databases"]
        assert abs(actual - expected) < 1e-9, (
            f"best_prior=max([0.4,0.9,0.5])=0.9. Expected {expected:.4f}, got {actual!r}"
        )


# ---------------------------------------------------------------------------
# Passive scoring (is_passive=True)  — Commit 39 bug fix
# ---------------------------------------------------------------------------

class TestPassiveScoringLogic:
    """is_passive=True uses additive clamped logic — cap 0.3, never reduce existing score."""

    def test_passive_delta_does_not_reduce_high_score(self) -> None:
        """Passive delta of 0.3 on a topic scored 1.0 must NOT reduce the topic score."""
        profile = {
            "topic_scores": {"embeddings_and_similarity": 1.0},
            "session_history": {"embeddings_and_similarity": [1.0]},
        }
        result = compute_topic_scores(
            profile, {"embeddings_and_similarity": 0.3}, is_passive=True
        )
        score = result["topic_scores"]["embeddings_and_similarity"]
        assert score == 1.0, (
            f"Passive delta on topic scored 1.0 must not reduce score; got {score!r}"
        )

    def test_passive_delta_caps_at_0_3_for_unscored_topic(self) -> None:
        """Passive scoring on an unscored topic must not exceed 0.3."""
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(
            profile, {"embeddings_and_similarity": 0.3}, is_passive=True
        )
        score = result["topic_scores"]["embeddings_and_similarity"]
        assert score <= 0.3, f"Passive score must cap at 0.3; got {score!r}"

    def test_passive_delta_never_passes_phase_gate(self) -> None:
        """Passive max of 0.3 is below the 0.70 Phase 1 threshold — never unlocks a phase."""
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(
            profile,
            {"embeddings_and_similarity": 0.3, "rag_pipeline_architecture": 0.3},
            is_passive=True,
        )
        assert not _phase_1_passed(result["topic_scores"]), (
            "Passive max of 0.3 must never pass the 0.70 Phase 1 gate"
        )

    def test_passive_does_not_update_session_history(self) -> None:
        """Passive assessments must not pollute session_history used for best_prior."""
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(
            profile, {"embeddings_and_similarity": 0.2}, is_passive=True
        )
        assert result["session_history"].get("embeddings_and_similarity") is None, (
            "Passive scoring must not append to session_history"
        )

    def test_passive_additive_accumulation(self) -> None:
        """Two passive 0.1 signals on same topic accumulate to 0.2."""
        profile1 = {"topic_scores": {}, "session_history": {}}
        r1 = compute_topic_scores(profile1, {"embeddings_and_similarity": 0.1}, is_passive=True)
        profile2 = {"topic_scores": r1["topic_scores"], "session_history": r1["session_history"]}
        r2 = compute_topic_scores(profile2, {"embeddings_and_similarity": 0.1}, is_passive=True)
        score = r2["topic_scores"]["embeddings_and_similarity"]
        assert abs(score - 0.2) < 1e-9, (
            f"Two passive 0.1 signals should accumulate to 0.2; got {score!r}"
        )


# ---------------------------------------------------------------------------
# Minimum-session guard (session_question_count)  — Commit 39 bug fix
# ---------------------------------------------------------------------------

class TestSessionMinimumGuard:
    """Explicit session_question_count < 3 skips scoring; None default skips the guard."""

    def test_explicit_count_1_returns_unchanged_scores(self) -> None:
        """session_question_count=1 explicitly passed must return current scores unchanged."""
        profile = {
            "topic_scores": {"vector_databases": 0.6},
            "session_history": {"vector_databases": [0.6]},
        }
        result = compute_topic_scores(
            profile, {"vector_databases": 1.0}, session_question_count=1
        )
        score = result["topic_scores"]["vector_databases"]
        assert abs(score - 0.6) < 1e-9, (
            f"session_question_count=1 must return unchanged score 0.6; got {score!r}"
        )

    def test_explicit_count_2_returns_unchanged_scores(self) -> None:
        """session_question_count=2 (< 3) also triggers the guard."""
        profile = {"topic_scores": {"vector_databases": 0.5}, "session_history": {}}
        result = compute_topic_scores(
            profile, {"vector_databases": 1.0}, session_question_count=2
        )
        assert abs(result["topic_scores"]["vector_databases"] - 0.5) < 1e-9

    def test_explicit_count_3_allows_scoring(self) -> None:
        """session_question_count=3 (= minimum) allows normal scoring."""
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(
            profile, {"vector_databases": 1.0}, session_question_count=3
        )
        assert abs(result["topic_scores"]["vector_databases"] - 1.0) < 1e-9

    def test_none_count_default_allows_scoring(self) -> None:
        """Default (None) skips the guard entirely — backward-compatible with all existing callers."""
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(profile, {"vector_databases": 0.8})
        assert abs(result["topic_scores"]["vector_databases"] - 0.8) < 1e-9

    def test_guard_bypassed_for_passive_with_count_1(self) -> None:
        """is_passive=True bypasses the session count guard — passive signals always apply."""
        profile = {"topic_scores": {}, "session_history": {}}
        result = compute_topic_scores(
            profile, {"vector_databases": 0.2}, is_passive=True, session_question_count=1
        )
        assert result["topic_scores"].get("vector_databases") is not None, (
            "Passive scoring with session_question_count=1 must still apply"
        )
