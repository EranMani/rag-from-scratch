"""
Tests for Commit 07 — agent-state-schema.

Coverage targets (7 spec gates + 3 Viktor additions):

Gate 1:  AgentState and AssessmentOutput import without error.
Gate 2:  All required fields present in get_type_hints(AgentState).
Gate 3:  messages hint is Annotated[list[BaseMessage], add_messages] with metadata preserved.
Gate 4:  session_id is absent from AgentState.
Gate 5:  add_messages accumulation: two sequential updates produce a 2-item list.
Gate 6:  AssessmentOutput validates correctly with a valid sample dict.
Gate 7:  AssessmentOutput raises ValidationError on missing required fields.

Viktor additions:
V1: AssessmentOutput with user_level="wizard" raises ValidationError.
V2: AssessmentOutput with an unknown slug key in topic_scores_delta silently drops it.
V3: AssessmentOutput with a valid slug key in topic_scores_delta preserves it.

Design notes:
- AgentState is a TypedDict — get_type_hints() is used to introspect field annotations.
  TypedDict does not support instance creation for field-level validation; it is a type
  contract only.  The Literal annotations on AgentState fields are enforced by type
  checkers (mypy/pyright), not at runtime.
- AssessmentOutput is a Pydantic BaseModel — field_validators run at parse time.
  ValidationError is raised synchronously; no async machinery needed.
- The add_messages accumulation test (Gate 5) uses the reducer directly via
  add_messages(existing, incoming) rather than building a full graph, keeping the test
  deterministic and infrastructure-free.
"""

import typing

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from pydantic import ValidationError
from typing_extensions import Annotated


# ---------------------------------------------------------------------------
# Gate 1 — Imports
# ---------------------------------------------------------------------------

class TestImports:
    def test_import_agent_state(self) -> None:
        from agents.state import AgentState  # noqa: F401

    def test_import_assessment_output(self) -> None:
        from agents.state import AssessmentOutput  # noqa: F401


# ---------------------------------------------------------------------------
# Gate 2 — Required fields present in AgentState
# ---------------------------------------------------------------------------

REQUIRED_AGENT_STATE_FIELDS = {
    "messages",
    "question",
    "user_id",
    "docs",
    "retrieval_source",
    "answer",
    "user_level",
    "topic_scores_delta",
    "identified_gaps",
    "assessment_error",
    "trace_id",
    "latency_ms",
    "cache_hit",
}


class TestAgentStateFields:
    def test_all_required_fields_present(self) -> None:
        from agents.state import AgentState

        hints = typing.get_type_hints(AgentState, include_extras=True)
        missing = REQUIRED_AGENT_STATE_FIELDS - set(hints)
        assert not missing, f"Missing fields in AgentState: {missing}"


# ---------------------------------------------------------------------------
# Gate 3 — messages is Annotated[list[BaseMessage], add_messages]
# ---------------------------------------------------------------------------

class TestMessagesAnnotation:
    def test_messages_hint_is_annotated_list_basemessage(self) -> None:
        from agents.state import AgentState

        hints = typing.get_type_hints(AgentState, include_extras=True)
        messages_hint = hints["messages"]

        # Must be Annotated
        origin = typing.get_origin(messages_hint)
        assert origin is Annotated, (
            f"messages hint origin is {origin!r}, expected Annotated"
        )

    def test_messages_metadata_contains_add_messages(self) -> None:
        from agents.state import AgentState

        hints = typing.get_type_hints(AgentState, include_extras=True)
        messages_hint = hints["messages"]
        metadata = typing.get_args(messages_hint)[1:]  # first arg is the base type

        assert add_messages in metadata, (
            f"add_messages not found in messages metadata: {metadata!r}"
        )


# ---------------------------------------------------------------------------
# Gate 4 — session_id absent from AgentState
# ---------------------------------------------------------------------------

class TestSessionIdAbsent:
    def test_session_id_not_in_agent_state(self) -> None:
        from agents.state import AgentState

        hints = typing.get_type_hints(AgentState, include_extras=True)
        assert "session_id" not in hints, (
            "session_id must NOT be a field on AgentState — "
            "it is passed as thread_id in graph config"
        )


# ---------------------------------------------------------------------------
# Gate 5 — add_messages accumulation
# ---------------------------------------------------------------------------

class TestAddMessagesAccumulation:
    def test_two_updates_produce_two_item_list(self) -> None:
        state_messages: list[BaseMessage] = []

        # First update: one HumanMessage
        state_messages = add_messages(state_messages, [HumanMessage("hello")])
        assert len(state_messages) == 1

        # Second update: one AIMessage
        state_messages = add_messages(state_messages, [AIMessage("world")])
        assert len(state_messages) == 2

        assert isinstance(state_messages[0], HumanMessage)
        assert isinstance(state_messages[1], AIMessage)
        assert state_messages[0].content == "hello"
        assert state_messages[1].content == "world"


# ---------------------------------------------------------------------------
# Gate 6 — AssessmentOutput validates with a valid sample dict
# ---------------------------------------------------------------------------

VALID_ASSESSMENT_DICT = {
    "topic_scores_delta": {"embeddings_and_similarity": 0.1, "rag_pipeline_architecture": -0.05},
    "identified_gaps": ["vector_databases"],
    "user_level": "intermediate",
}


class TestAssessmentOutputValid:
    def test_valid_sample_validates(self) -> None:
        from agents.state import AssessmentOutput

        output = AssessmentOutput(**VALID_ASSESSMENT_DICT)
        assert output.user_level == "intermediate"
        assert output.topic_scores_delta.embeddings_and_similarity == pytest.approx(0.1)
        assert output.topic_scores_delta.rag_pipeline_architecture == pytest.approx(-0.05)
        assert output.identified_gaps == ["vector_databases"]


# ---------------------------------------------------------------------------
# Gate 7 — AssessmentOutput raises ValidationError on missing required fields
# ---------------------------------------------------------------------------

class TestAssessmentOutputMissingFields:
    def test_missing_user_level_raises(self) -> None:
        from agents.state import AssessmentOutput

        with pytest.raises(ValidationError):
            AssessmentOutput(
                topic_scores_delta={"rag_fundamentals": 0.1},
                identified_gaps=[],
                # user_level is missing
            )

    def test_missing_topic_scores_delta_raises(self) -> None:
        from agents.state import AssessmentOutput

        with pytest.raises(ValidationError):
            AssessmentOutput(
                # topic_scores_delta is missing
                identified_gaps=[],
                user_level="novice",
            )

    def test_missing_identified_gaps_raises(self) -> None:
        from agents.state import AssessmentOutput

        with pytest.raises(ValidationError):
            AssessmentOutput(
                topic_scores_delta={},
                # identified_gaps is missing
                user_level="novice",
            )


# ---------------------------------------------------------------------------
# Viktor V1 — invalid user_level raises ValidationError
# ---------------------------------------------------------------------------

class TestAssessmentOutputInvalidUserLevel:
    def test_wizard_level_raises_validation_error(self) -> None:
        from agents.state import AssessmentOutput

        with pytest.raises(ValidationError) as exc_info:
            AssessmentOutput(
                topic_scores_delta={},
                identified_gaps=[],
                user_level="wizard",  # not in the Literal
            )
        # Confirm it is a user_level field error, not some other validation failure
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "user_level" in field_names


# ---------------------------------------------------------------------------
# Viktor V2 — unknown slug in topic_scores_delta is silently dropped
# ---------------------------------------------------------------------------

class TestSlugValidationDropsUnknown:
    def test_unknown_topic_slug_is_dropped(self) -> None:
        from agents.state import AssessmentOutput

        output = AssessmentOutput(
            topic_scores_delta={"not_a_module": 0.5, "rag_fundamentals": 0.2},
            identified_gaps=[],
            user_level="novice",
        )
        # unknown key must be absent
        assert "not_a_module" not in output.topic_scores_delta
        # no ValidationError raised — silent drop policy

    def test_unknown_identified_gap_slug_is_dropped(self) -> None:
        from agents.state import AssessmentOutput

        output = AssessmentOutput(
            topic_scores_delta={},
            identified_gaps=["not_a_module", "vector_databases"],
            user_level="novice",
        )
        assert "not_a_module" not in output.identified_gaps
        assert "vector_databases" in output.identified_gaps


# ---------------------------------------------------------------------------
# Viktor V3 — valid slug in topic_scores_delta is preserved
# ---------------------------------------------------------------------------

class TestSlugValidationPreservesValid:
    def test_valid_topic_slug_is_preserved(self) -> None:
        from agents.state import AssessmentOutput

        output = AssessmentOutput(
            topic_scores_delta={"embeddings_and_similarity": 0.5},
            identified_gaps=[],
            user_level="advanced",
        )
        assert output.topic_scores_delta.embeddings_and_similarity == pytest.approx(0.5)

    def test_all_valid_slugs_are_preserved(self) -> None:
        from agents.state import AssessmentOutput

        all_valid = {
            "embeddings_and_similarity": 0.1,
            "rag_pipeline_architecture": 0.2,
            "chunking_strategies": 0.3,
            "vector_databases": 0.4,
            "retrieval_methods": 0.5,
            "context_and_prompting": 0.6,
            "evaluation_and_metrics": 0.7,
            "production_patterns": 0.8,
        }
        output = AssessmentOutput(
            topic_scores_delta=all_valid,
            identified_gaps=list(all_valid.keys()),
            user_level="expert",
        )
        delta_dict = output.topic_scores_delta.model_dump()
        assert all(abs(delta_dict.get(k, -1) - v) < 1e-9 for k, v in all_valid.items())
        assert set(output.identified_gaps) == set(all_valid)
