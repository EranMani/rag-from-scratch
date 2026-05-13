"""
AI Engineering Transition: From Probabilistic Output to Deterministic Systems

This module implements core architectural principles for integrating LLMs 
into production-grade software (e.g., AgentCanvas). Unlike standard backend 
development, AI Engineering requires wrapping stochastic models in rigid 
software guardrails.

Key Architectural Principles Applied:
    1. Defensive State Management: Uses robust patterns (like getattr) to 
       ensure the system fails gracefully. In multi-agent environments, 
       the state is dynamic; the code must never assume a perfect schema.
    2. Deterministic Gating: Instead of letting the LLM decide when to evaluate, 
       the system uses explicit "State-Gates" (e.g., _is_evaluation_mode). 
       This keeps the AI's behavior predictable and aligned with the UX.
    3. Contextual Grounding (Source-of-Truth): Forcing the LLM to grade against 
       external, human-authored Markdown rubrics. This eliminates 'knowledge drift' 
       and ensures grading consistency.
    4. Decoupled Logic & Content: Separating pedagogical flow (Python) from 
       educational content (Markdown), allowing for rapid curriculum 
       iteration without risking system stability.
    5. Managed Variation: Implements "Controlled Randomness" via modulo indexing 
       tied to conversation depth (len(messages)). This provides user variety 
       while remaining fully reproducible for debugging.
    6. Orchestrated Routing: The node acts as a central 'Traffic Controller,' 
       using the current state to route between content delivery and performance 
       evaluation.
    7. Schema-Validated Chains: Uses '.with_structured_output' to transform 
       stochastic LLM text into validated Pydantic objects. This forces the 
       model to adhere to a strict software contract (e.g., PassiveAssessmentOutput).
    8. Multi-Provider Workarounds (OpenAI Strictness): Implements explicit 
       class-based schemas (TopicScoresDelta) instead of flexible dicts to 
       bypass specific provider limitations.
    9. Functional Chaining & Resilience: Employs the Pipe-and-Filter pattern (|) 
       to create atomic, traceable execution units. This chaining ensures 
       operational robustness: if any stage (Prompt, LLM, or Parser) fails, 
       the entire unit fails predictably, allowing for clean exception handling 
       and preventing "half-baked" data from polluting the AgentState.

Role Shift: Moving from a Software Developer to an AI Engineer means 
transitioning from "building logic" to "building the framework where 
probabilistic logic is safely contained." 

As an AI Engineer, you aren't just writing functions; you are designing a 
State Machine. By adding Orchestrated Routing, you acknowledge that the 
assess_node is the "brain" that knows the difference between teaching 
(selecting a question) and testing (evaluating an answer). It ensures that 
the LLM is only called when the architectural conditions are exactly right, 
preventing the "looping" or "confusion" often seen in less structured AI agents.
"""

"""
assess_node — curriculum-driven assessment node.

Three operating modes determined from state:

  Test mode (default when no pending question):
    - Runs passive assessment LLM call to infer mastery from the user's natural query.
    - Passive scores are capped at 0.3; emitted only when confidence >= 0.4.
    - Deterministically selects a curriculum question for the current topic.
    - Loads question text from knowledge-base/curriculum/questions/<slug>.md.
    - Returns test_mode=True with pending_test_question/slug set.

  Evaluation mode (when pending_test_question is set and user has answered):
    - Calls LLM with EvaluationOutput schema (verdict: correct/partial/incorrect).
    - Maps verdict to test_answer_score: correct=1.0, partial=0.5, incorrect=0.0.
    - Derives sparse topic_scores_delta from test_answer_score and pending_test_slug.
    - Returns test_mode=False with scored result.

Node output keys (all modes):
    topic_scores_delta, identified_gaps, assessment_error,
    test_mode, pending_test_question, pending_test_slug, test_answer_score

Does NOT write: messages, docs, answer, question, retrieval_source, user_id,
trace_id, latency_ms, cache_hit, user_level.
"""

"""
NOTE: Three primary roles usually used
SYSTEM: The "boss" instructions that set the rules.
HUMAN: The user's input or question.
ASSISTENT (or "ai"): The model's own previous responses. Also can be think of as the "stored state" of the conversation
                     that you re-inject so the LLM doesnt lose the thread
E.G:
_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "Hi, who are you?"),
    ("assistant", "I am your RAG tutor! How can I help?"), # Providing context of a past response
    ("human", "{question}")
])
"""

"""
ARCHITECTURE THINKING
Defensive Programming: In multi-agent systems, the state can sometimes be manipulated by different tools. 
                       getattr ensures that even if a message isn't a standard LangChain object, 
                       your "Evaluation Mode" logic won't crash the entire graph.

State Stability: It ensures the assessment node only triggers on valid user input, 
                 maintaining the "human-in-the-loop" oversight you've prioritized for your AI systems.
"""

import logging
import pathlib
import re
from typing import Any, Literal

from langchain_core.messages import AIMessage

from agents.prompts.assessment import assessment_prompt
from langchain_core.prompts import ChatPromptTemplate

from agents.state import (
    VALID_MODULE_SLUGS,
    AgentState,
    EvaluationOutput,
    PassiveAssessmentOutput,
)
from rag.providers import get_provider

logger = logging.getLogger(__name__)

# Repo root is parents[3] from this file (…/src/agents/nodes/assess.py).
_CURRICULUM_DIR = (
    pathlib.Path(__file__).resolve().parents[3] / "knowledge-base" / "curriculum" / "questions"
)

# Maps LLM evaluation labels to numeric weights for active testing
# NOTE: By using a predefined dictionary, the system ensures that the evaluation is deterministic
# Grades an answer
_VERDICT_SCORE: dict[str, float] = {
    "correct": 1.0,
    "partial": 0.5,
    "incorrect": 0.0,
}

# Rewards query sophistication with capped mastery increments (max 0.3)
# e.g: An expert wont be forced to answer beginner questions
# NOTE: It rewards the user for the quality of their question
_PASSIVE_LEVEL_SCORE: dict[str, float] = {
    "novice": 0.05,
    "beginner": 0.1,
    "intermediate": 0.2,
    "advanced": 0.25,
    "expert": 0.3,
}

# Validation gate (40%) to prevent skill profile corruption from low-confidence AI inference
_PASSIVE_CONFIDENCE_THRESHOLD: float = 0.4

# Constrain the LLM to a set of valid topics slugs.
# NOTE: Ensures the output is always compatiable with the rest of the system data architecture
_PASSIVE_SYSTEM = """\
You analyze a learner's question to infer their RAG knowledge level.

Valid topic slugs: embeddings_and_similarity, rag_pipeline_architecture,
chunking_strategies, vector_databases, retrieval_methods, context_and_prompting,
evaluation_and_metrics, production_patterns.

Return relevant_slug (the single most relevant slug, or null if unclear),
inferred_level (novice/beginner/intermediate/advanced/expert), and
confidence (0.0-1.0). Base level on vocabulary and specificity in the question.\
"""

_PASSIVE_HUMAN = "Question: {question}"

# NOTE: 'ChatPromptTemplate.from_messages' is a factory method used to create a structured script for an LLM
# It organizes the input into specific roles, helps distinguish between instructions and data
# NOTE: system => High-level instructions that define the model's persona, the rules it must follow and the required output format
# NOTE: human => This represents the user's input. Inject the question dynamically filled with the user's actual query during execution
_passive_prompt: ChatPromptTemplate = ChatPromptTemplate.from_messages([
    ("system", _PASSIVE_SYSTEM),
    ("human", _PASSIVE_HUMAN),
])


"""
Assessment Infrastructure: Content Extraction & Deterministic Evaluation

This module enables a "Source-of-Truth" evaluation pattern, syncing lesson 
content with AI-driven grading to ensure low-variance, objective scoring.

Core Workflow:
    - _load_question_text: Uses modulo-based rotation to pick a fresh challenge 
      from Markdown based on session length.
    - _load_rubric_text: Extracts matching grading criteria (Correct/Partial/Incorrect) 
      using Regex to feed the LLM a deterministic "Answer Key."

Pipeline:
    Slug -> Index % Len -> [Question + Rubric] -> Evaluation Prompt -> LLM Verdict.
"""


def _load_question_text(slug: str, question_index: int = 0) -> str:
    """Load the first question text from a curriculum question file.

    Args:
        slug: A valid topic slug from VALID_MODULE_SLUGS.
        question_index: Zero-based index of question to load (default: first question).

    Returns:
        The question text string.

    Raises:
        FileNotFoundError: If the curriculum file for slug does not exist.
        ValueError: If no question sections are found in the file.
    """
    # Fetch the slug markdown file and content
    path = _CURRICULUM_DIR / f"{slug}.md"
    content = path.read_text(encoding="utf-8")

    # Extract all **Question:** blocks from the content
    matches = re.findall(r"\*\*Question:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)", content, re.DOTALL)

    # Avoid returning an empty question to the user
    if not matches:
        raise ValueError(f"No question blocks found in curriculum file for slug '{slug}'")

    """
    Use modulo to prevent IndexOutOfBounds; creates an infinite rotation 
    through available questions based on session message count.
    Always guarantee a valid index
    # NOTE By using the conversation length as the key, it ensures the user sees different questions 
           in a natural "round-robin" fashion each time they revisit a topic.
    """
    # Use the session messages amount as the seed for selecting the question
    idx = question_index % len(matches)
    return matches[idx].strip()


def _load_rubric_text(slug: str, question_index: int = 0) -> str:
    """
    Extracts structured grading criteria for a specific curriculum question.

    This function parses the Markdown file associated with a topic (slug), 
    isolates the relevant question block using modulo-based indexing, 
    and extracts the 'Correct', 'Partial', and 'Incorrect' criteria using 
    regex patterns.

    Args:
        slug: The topic identifier used to locate the Markdown file.
        question_index: The desired question index, typically mapped to 
            the conversation length to ensure variation.

    Returns:
        A formatted string containing the concatenated grading rubric 
        labels and their respective criteria, separated by double newlines. 
        Returns an empty string if no valid question sections are found.

    Note:
        Uses re.MULTILINE to detect headers at line starts and re.DOTALL 
        to capture multi-line criteria descriptions.
    """
    # Fetch the correct file according to subject and extract the content
    path = _CURRICULUM_DIR / f"{slug}.md"
    content = path.read_text(encoding="utf-8")

    """
    Splits Markdown content into logical blocks using a positive lookahead.
    The lookahead (?=^## Q\d) ensures headers are preserved at the start of each split,
    while re.MULTILINE allows '^' to match every line break across the file.
    Finally, filters out any preamble text that doesn't start with a valid question header.
    """
    sections = re.split(r"(?=^## Q\d)", content, flags=re.MULTILINE)
    question_sections = [s for s in sections if s.strip().startswith("## Q")]
    if not question_sections:
        return ""
    
    # Selects the question block using modulo to ensure a valid index;
    idx = question_index % len(question_sections)
    section = question_sections[idx]

    """
    Precisely carves out the grading instructions for each possible outcome (Correct, Partial, Incorrect) 
    from the raw Markdown so they can be sent to the LLM as a structured grading guide.
    """
    rubric_parts: list[str] = []
    for label in ("Correct answer criteria", "Partial credit criteria", "Incorrect / no-credit criteria"):
        pattern = rf"\*\*{re.escape(label)}:\*\*\s*\n(.*?)(?=\n\n\*\*|\Z)"
        match = re.search(pattern, section, re.DOTALL)
        if match:
            rubric_parts.append(f"**{label}:**\n{match.group(1).strip()}")
    return "\n\n".join(rubric_parts)


def _select_question_index(state: AgentState) -> int:
    """Deterministically select a question index for the current topic.

    Ensures the index cycles within bounds (0-7) to provide question variety.
    """
    messages = state.get("messages") or []
    return len(messages) % 8  # 8 questions per topic file


def _select_test_slug(state: AgentState) -> str | None:
    """
    Determines the next learning module. 
    Prioritizes remediation of identified knowledge gaps before 
    defaulting to the standard RAG curriculum sequence.

    Priority order:
      1. First slug in identified_gaps that is in VALID_MODULE_SLUGS.
      2. Fall back to the first valid slug in the canonical ordering.

    Returns None only if VALID_MODULE_SLUGS is empty (impossible in practice).
    """
    gaps: list[str] = state.get("identified_gaps") or []
    for slug in gaps:
        if slug in VALID_MODULE_SLUGS:
            return slug

    # Canonical ordering from topic-slugs.json.
    _ORDERED_SLUGS = [
        "embeddings_and_similarity",
        "rag_pipeline_architecture",
        "chunking_strategies",
        "vector_databases",
        "retrieval_methods",
        "context_and_prompting",
        "evaluation_and_metrics",
        "production_patterns",
    ]
    for slug in _ORDERED_SLUGS:
        if slug in VALID_MODULE_SLUGS:
            return slug
    return None


def _is_evaluation_mode(state: AgentState) -> bool:
    """
    This logic acts as a state-gate that ensures the evaluator only triggers when a curriculum question 
    is currently active and the user has provided a fresh response to be graded.
    """
    # Check if the system waiting for the user answer about the provided question
    pending = state.get("pending_test_question")
    if not pending:
        return False
    
    # Get the conversation messages
    messages = state.get("messages") or []

    # There are no messages if the session just started
    if not messages:
        return False

    # The last message must be a HumanMessage (user answer), not an AIMessage.
    # It contains 'content' (the actual text) and 'type' (the role).
    last = messages[-1]

    """
    Safely checks if the last message is from the user. Using getattr prevents 
    an AttributeError if the message object is malformed or missing the 'type' field.
    """
    # Identifying the message type is how you manage the "Human-in-the-Loop" flow
    return getattr(last, "type", None) == "human"


async def assess_node(state: AgentState) -> dict[str, Any]:
    """
    LangGraph node: curriculum-driven test administration and answer evaluation.
    Acts as a traffic controller: routes to '_evaluate_answer' if a response is pending, 
    or '_select_test_question' to prompt the user with a new challenge.

    In test mode: runs passive assessment then selects a curriculum question.
    In evaluation mode: evaluates the user's answer against the rubric via LLM.

    Returns exactly: topic_scores_delta, identified_gaps, assessment_error,
                     test_mode, pending_test_question, pending_test_slug,
                     test_answer_score.
    """
    if _is_evaluation_mode(state):
        return await _evaluate_answer(state)
    return await _select_test_question(state)


async def _run_passive_assessment(question: str) -> dict[str, float]:
    """
    Analyzes the user's natural query to infer knowledge levels without a formal test.
    Uses structured output and a confidence threshold to ensure data integrity 
    before updating the user's skill profile.

    Returns an empty dict if the LLM call fails, confidence is too low,
    or relevant_slug is not a valid VALID_MODULE_SLUGS member.
    """
    try:
        # Get the actual LLM model
        llm = get_provider().get_llm()

        """
        Defines an atomic, schema-validated pipeline that forces the LLM to map 
        natural language queries into a structured PassiveAssessmentOutput object.
        """
        chain = _passive_prompt | llm.with_structured_output(PassiveAssessmentOutput)
        """
        Executes the chain asynchronously, injecting the user's question and 
        returning a validated Pydantic instance to ensure type-safety and state integrity.
        """
        result: PassiveAssessmentOutput = await chain.ainvoke({"question": question})

        if result.relevant_slug is None:
            return {}

        if result.relevant_slug not in VALID_MODULE_SLUGS:
            logger.warning(
                "passive_assessment: slug '%s' not in VALID_MODULE_SLUGS — ignoring",
                result.relevant_slug,
            )
            return {}
        
        # Use the threshold value to determine if the model decision confidence is good enough
        if result.confidence < _PASSIVE_CONFIDENCE_THRESHOLD:
            return {}

        # Using the mapped dict, return the score based on the user learning level
        score = _PASSIVE_LEVEL_SCORE.get(result.inferred_level, 0.0)
        return {result.relevant_slug: score} if score > 0.0 else {}

    except Exception:
        logger.warning("passive_assessment: LLM call failed — continuing with empty delta", exc_info=True)
        return {}


async def _select_test_question(state: AgentState) -> dict[str, Any]:
    """
    Orchestrates the transition to testing: captures passive learning signals from the 
    current turn, then selects and loads a deterministic curriculum question to 
    advance the agent's state into evaluation mode.
    """
    # Infers a knowledge-level score change from the user's natural query before transitioning to the formal curriculum question
    passive_delta = await _run_passive_assessment(state.get("question") or "")

    # Select the next question from the relative slug
    slug = _select_test_slug(state)
    if slug is None:
        logger.warning("assess_node: no valid slug available for test selection")
        return {
            "topic_scores_delta": passive_delta,
            "identified_gaps": state.get("identified_gaps") or [],
            "assessment_error": True,
            "test_mode": False,
            "pending_test_question": None,
            "pending_test_slug": None,
            "test_answer_score": None,
        }
    try:
        # Generate the index for selecting the question
        q_idx = _select_question_index(state)
        question_text = _load_question_text(slug, q_idx)
    except (FileNotFoundError, ValueError) as exc:
        logger.warning(
            "assess_node: failed to load curriculum question for slug '%s': %s",
            slug,
            exc,
        )
        return {
            "topic_scores_delta": passive_delta,
            "identified_gaps": state.get("identified_gaps") or [],
            "assessment_error": True,
            "test_mode": False,
            "pending_test_question": None,
            "pending_test_slug": None,
            "test_answer_score": None,
        }

    """
    Updates the graph state with the new curriculum question, persists passive scores, 
    and locks the agent into test_mode to wait for the user's answer.
    """
    return {
        "messages": [AIMessage(content=f"\n\nKnowledge check: {question_text}")],
        "topic_scores_delta": passive_delta,
        "identified_gaps": state.get("identified_gaps") or [],
        "assessment_error": False,
        "test_mode": True,
        "pending_test_question": question_text,
        "pending_test_slug": slug,
        "test_answer_score": None,
    }


async def _evaluate_answer(state: AgentState) -> dict[str, Any]:
    """
    Synchronizes the evaluation by grounding the LLM with a specific rubric, 
    converting a probabilistic verdict into a deterministic score, and 
    merging identified gaps before resetting the agent to conversation mode.
    """
    # Get the test slug from the state
    pending_slug: str | None = state.get("pending_test_slug")

    # Guard: slug must be valid.
    if pending_slug not in VALID_MODULE_SLUGS:
        logger.warning(
            "assess_node: pending_test_slug '%s' is not in VALID_MODULE_SLUGS — "
            "setting assessment_error=True, trace_id=%s",
            pending_slug,
            state.get("trace_id"),
        )
        return _eval_error_result(state)

    try:
        # Get the index based on the messages amount in the state
        q_idx = _select_question_index(state)
        # Get the criterais guidelines for the model
        rubric = _load_rubric_text(pending_slug, q_idx)
        # Get the current pending question from the previous state
        pending_question: str = state.get("pending_test_question") or ""
        # Get the user answer for the question
        user_answer: str = state.get("question") or ""
        # Get the actual model
        llm = get_provider().get_llm()

        # Perform atomic chain to create the runnable object
        chain = assessment_prompt | llm.with_structured_output(EvaluationOutput)

        # Invoke the runnable by injecting the values that the prompt needs
        result: EvaluationOutput = await chain.ainvoke({
            "question": pending_question,
            "rubric": rubric,
            "user_answer": user_answer,
        })

        # Map verdict to score; treat unknown verdicts as incorrect.
        verdict: str = result.verdict if result.verdict in _VERDICT_SCORE else "incorrect"
        if result.verdict not in _VERDICT_SCORE:
            logger.warning(
                "assess_node: invalid verdict '%s' received — treating as incorrect",
                result.verdict,
            )
        score: float = _VERDICT_SCORE[verdict]

        # Derive sparse delta from score and slug.
        delta: dict[str, float] = {pending_slug: score} if score > 0.0 else {}

        return {
            "topic_scores_delta": delta,
            "identified_gaps": result.identified_gaps,
            "assessment_error": False,
            "test_mode": False,
            "pending_test_question": None,
            "pending_test_slug": None,
            "test_answer_score": score,
        }

    except Exception:
        logger.warning(
            "assess_node: evaluation failed — setting assessment_error=True, "
            "trace_id=%s",
            state.get("trace_id"),  # type: ignore[call-overload]
            exc_info=True,
        )
        return _eval_error_result(state)


def _eval_error_result(state: AgentState) -> dict[str, Any]:
    """Return the standard error payload for evaluation failures."""
    return {
        "topic_scores_delta": {},
        "identified_gaps": [],
        "assessment_error": True,
        "test_mode": False,
        "pending_test_question": None,
        "pending_test_slug": None,
        "test_answer_score": None,
    }
