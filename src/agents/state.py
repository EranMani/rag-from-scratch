"""
AgentState and AssessmentOutput — LangGraph graph state schema.

Designed for the full Commit 07-17 arc. All Phase 4 fields are declared here
to avoid retroactive schema changes cascading through the compiled graph.

session_id is NOT a field. It is passed as thread_id in the graph invocation config:
    config = {"configurable": {"thread_id": session_id}}
    graph.astream_events(initial_state, config=config, version="v2")
LangGraph's MemorySaver checkpointer uses thread_id for cross-turn persistence.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, field_validator
from typing_extensions import TypedDict

# ---------------------------------------------------------------------------
# TopicScoresDelta — fixed-key schema compatible with OpenAI structured output.
# dict[str, float] produces additionalProperties which OpenAI rejects at schema
# validation time.  Explicit fields generate a closed object schema.
# ---------------------------------------------------------------------------

class TopicScoresDelta(BaseModel):
    """Per-turn topic score deltas with one explicit field per valid slug.

    Default 0.0 means no assessment occurred for that topic this turn.
    assess_node filters out zero-value fields before writing to AgentState
    so downstream consumers continue to receive a sparse dict[str, float].
    """
    embeddings_and_similarity: float = 0.0
    rag_pipeline_architecture: float = 0.0
    chunking_strategies: float = 0.0
    vector_databases: float = 0.0
    retrieval_methods: float = 0.0
    context_and_prompting: float = 0.0
    langchain_fundamentals: float = 0.0
    evaluation_and_metrics: float = 0.0
    production_patterns: float = 0.0

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid topic slug values.  Any key in topic_scores_delta must come from here.
# ---------------------------------------------------------------------------
VALID_MODULE_SLUGS: frozenset[str] = frozenset({
    "embeddings_and_similarity",
    "rag_pipeline_architecture",
    "chunking_strategies",
    "vector_databases",
    "retrieval_methods",
    "context_and_prompting",
    "langchain_fundamentals",
    "evaluation_and_metrics",
    "production_patterns",
})


# ---------------------------------------------------------------------------
# AgentState
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """Full state envelope for the LangGraph adaptive-RAG graph.

    Fields are grouped by lifecycle stage:
      - Turn input  : messages, question, user_id, user_level
      - Retrieval   : docs, retrieval_source
      - Generation  : answer
      - Assessment  : topic_scores_delta, identified_gaps, assessment_error
      - Observability: trace_id, latency_ms, cache_hit
    """

    # --- Turn input ---
    messages: Annotated[list[BaseMessage], add_messages]
    """LangGraph native message list.  The add_messages reducer appends incoming
    messages rather than replacing the list.  The current user question arrives
    here as a HumanMessage before graph entry; prior turns are reconstructed
    from the checkpointer via thread_id."""

    question: str
    """Convenience copy of the current user question so retrieve_node can query
    without unpacking messages[-1].content."""

    user_id: str | None
    """User identifier from the JWT.  None for anonymous (unauthenticated) calls."""

    # --- Retrieval ---
    docs: list[Document]
    """Retrieved LangChain Document objects produced by retrieve_node."""

    retrieval_source: str
    """Which retriever was used: 'chroma' (dense) or 'bm25' (keyword fallback)."""

    # --- Generation ---
    answer: str
    """Complete generated answer.  Written by generate_node; read by assess_node
    and included in the SSE 'done' event (Commit 10)."""

    gate_just_passed: str | None
    """Phase name just crossed ("phase_1", "phase_2", "phase_3") or None."""

    # --- User context ---
    user_level: Literal["novice", "beginner", "intermediate", "advanced", "expert"]
    """Learner mastery level loaded from the user profile before graph entry."""

    # --- Assessment ---
    topic_scores_delta: dict[str, float]
    """Sparse dict of module slug → score change assessed this turn.
    Keys must be drawn from VALID_MODULE_SLUGS.  Populated by assess_node."""

    identified_gaps: list[str]
    """Module slugs where understanding is low this turn.  Populated by assess_node."""

    assessment_error: bool
    """True if assess_node failed (e.g., LLM parse error).
    Triggers the fallback edge that skips profile_update_node."""

    test_mode: bool
    """True when assess_node has selected a curriculum question and is waiting for the user's answer."""

    pending_test_question: str | None
    """The curriculum test question text currently awaiting the user's answer."""

    pending_test_slug: str | None
    """The topic slug of the pending test question; must be in VALID_MODULE_SLUGS."""

    is_mcq: bool
    """True when the pending test question is MCQ format (A/B/C/D options).
    False for open-ended questions and when no question is pending."""

    pending_mcq_correct_answer: str | None
    """The correct answer letter ('A', 'B', 'C', or 'D') for the current MCQ question.
    Set when assess_node delivers an MCQ question; cleared after evaluation.
    None when no MCQ question is pending."""

    session_question_counts: dict[str, int]
    """Per-topic count of MCQ answers evaluated this session (topic slug → count).
    Used by update_profile_node to enforce the minimum-3-questions guard in compute_topic_scores."""

    is_passive_delta: bool
    """True when topic_scores_delta originates from passive inference (natural query analysis),
    False when it comes from an explicit MCQ or open-ended evaluation.
    update_profile_node passes this to compute_topic_scores so passive signals use the
    additive capped formula instead of the SRS formula — preventing passive inference
    from reducing a score the user earned through active testing."""

    # --- Observability ---
    trace_id: str
    """Unique identifier for this request trace; set before graph entry."""

    latency_ms: int
    """End-to-end latency in milliseconds; written after graph completion."""

    cache_hit: Literal["hit", "miss", "bypass"]
    """Cache status: 'hit', 'miss', or 'bypass'.
    Note: chain.py currently emits legacy values ('query', 'llm', 'none') which will
    be replaced when Commit 10 replaces run_rag_pipeline.  This Literal documents the
    intended contract going forward."""


# ---------------------------------------------------------------------------
# EvaluationOutput — structured LLM output for curriculum answer evaluation.
# Used exclusively in assess_node evaluation mode (Commit 24+).
# ---------------------------------------------------------------------------

class EvaluationOutput(BaseModel):
    """Structured evaluator output: verdict on user's answer to a curriculum question."""

    verdict: Literal["correct", "partial", "incorrect"]
    """LLM's judgment of the user answer against the open question grading criteria."""

    confidence: float
    """Evaluator confidence in the verdict: 0.0–1.0."""

    identified_gaps: list[str]
    """Topic slugs where the answer reveals gaps; values not in VALID_MODULE_SLUGS are dropped."""

    user_level: Literal["novice", "beginner", "intermediate", "advanced", "expert"]
    """Assessed mastery level for this turn."""

    @field_validator("identified_gaps", mode="before")
    @classmethod
    def filter_eval_gaps_slugs(cls, v: object) -> object:
        if not isinstance(v, list):
            return v
        filtered = [s for s in v if s in VALID_MODULE_SLUGS]
        dropped = set(v) - set(filtered)  # type: ignore[arg-type]
        if dropped:
            logger.warning(
                "EvaluationOutput.identified_gaps: dropped unknown slugs %s", dropped
            )
        return filtered

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: object) -> object:
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return v


# ---------------------------------------------------------------------------
# PassiveAssessmentOutput — structured output for passive turn-signal inference.
# Used by assess_node test mode to infer mastery from the user's natural query.
# ---------------------------------------------------------------------------

class PassiveAssessmentOutput(BaseModel):
    """Side-channel mastery signal inferred from the user's natural query."""

    relevant_slug: str | None
    """primary topic from the question, or null if off-topic/unclear."""

    inferred_level: Literal["novice", "beginner", "intermediate", "advanced", "expert"]
    """ mastery implied by vocabulary and specificity in the question"""

    confidence: float
    """certainty in both relevant_slug and inferred_level (0.0–1.0)"""

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_passive_confidence(cls, v: object) -> object:
        if isinstance(v, (int, float)):
            return max(0.0, min(1.0, float(v)))
        return v


# ---------------------------------------------------------------------------
# AssessmentOutput
# ---------------------------------------------------------------------------

class AssessmentOutput(BaseModel):
    """Structured output schema for assess_node's LLM call.

    The LLM is constrained to return exactly this shape; langchain's
    .with_structured_output(AssessmentOutput) enforces it at parse time.
    This is a per-turn delta — it captures what the model assessed this turn,
    not a cumulative DB read.  profile_update_node (Commit 15) applies these
    deltas to the persistent user_profiles table.

    topic_scores_delta uses TopicScoresDelta (explicit fields) rather than
    dict[str, float] because OpenAI's structured output endpoint rejects any
    schema that contains additionalProperties, which is what dict[str, float]
    serialises to.  assess_node converts TopicScoresDelta back to a sparse
    dict[str, float] before writing to AgentState.
    """

    topic_scores_delta: TopicScoresDelta
    """Fixed-key topic score deltas this turn.  Zero-value fields are filtered
    out by assess_node before writing to AgentState.topic_scores_delta."""

    identified_gaps: list[str]
    """Module slugs where understanding is judged to be low this turn.
    Values not in VALID_MODULE_SLUGS are silently dropped."""

    user_level: Literal["novice", "beginner", "intermediate", "advanced", "expert"]
    """Assessed user mastery level for this turn."""

    @field_validator("identified_gaps", mode="before")
    @classmethod
    def filter_identified_gaps_slugs(cls, v: object) -> object:
        if not isinstance(v, list):
            return v
        filtered = [s for s in v if s in VALID_MODULE_SLUGS]
        dropped = set(v) - set(filtered)
        if dropped:
            logger.warning(
                "AssessmentOutput.identified_gaps: dropped unknown slugs %s", dropped
            )
        return filtered
