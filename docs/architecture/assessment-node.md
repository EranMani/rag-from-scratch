# Assessment Node — Architecture & Design Principles

## From Probabilistic Output to Deterministic Systems

This module (`src/agents/nodes/assess.py`) implements core architectural principles for integrating LLMs into production-grade software (e.g., AgentCanvas). Unlike standard backend development, AI Engineering requires wrapping stochastic models in rigid software guardrails.

### Key Architectural Principles

1. **Defensive State Management**: Uses robust patterns (like `getattr`) to ensure the system fails gracefully. In multi-agent environments, the state is dynamic; the code must never assume a perfect schema.

2. **Deterministic Gating**: Instead of letting the LLM decide when to evaluate, the system uses explicit "State-Gates" (e.g., `_is_evaluation_mode`). This keeps the AI's behavior predictable and aligned with the UX.

3. **Contextual Grounding (Source-of-Truth)**: Forcing the LLM to grade against external, human-authored Markdown rubrics. This eliminates 'knowledge drift' and ensures grading consistency.

4. **Decoupled Logic & Content**: Separating pedagogical flow (Python) from educational content (Markdown), allowing for rapid curriculum iteration without risking system stability.

5. **Managed Variation**: Implements "Controlled Randomness" via modulo indexing tied to conversation depth (`len(messages)`). This provides user variety while remaining fully reproducible for debugging.

6. **Orchestrated Routing**: The node acts as a central 'Traffic Controller,' using the current state to route between content delivery and performance evaluation.

7. **Schema-Validated Chains**: Uses `.with_structured_output` to transform stochastic LLM text into validated Pydantic objects. This forces the model to adhere to a strict software contract (e.g., `PassiveAssessmentOutput`).

8. **Multi-Provider Workarounds (OpenAI Strictness)**: Implements explicit class-based schemas (`TopicScoresDelta`) instead of flexible dicts to bypass specific provider limitations.

9. **Functional Chaining & Resilience**: Employs the Pipe-and-Filter pattern (`|`) to create atomic, traceable execution units. This chaining ensures operational robustness: if any stage (Prompt, LLM, or Parser) fails, the entire unit fails predictably, allowing for clean exception handling and preventing "half-baked" data from polluting the AgentState.

---

## Role Shift: Software Developer → AI Engineer

Moving from a Software Developer to an AI Engineer means transitioning from "building logic" to "building the framework where probabilistic logic is safely contained."

As an AI Engineer, you aren't just writing functions; you are designing a State Machine. By adding Orchestrated Routing, you acknowledge that the `assess_node` is the "brain" that knows the difference between teaching (selecting a question) and testing (evaluating an answer). It ensures that the LLM is only called when the architectural conditions are exactly right, preventing the "looping" or "confusion" often seen in less structured AI agents.

---

## LangChain Message Roles Reference

Three primary roles used in prompt templates:

| Role | Purpose |
|------|---------|
| **SYSTEM** | The "boss" instructions that set the rules. |
| **HUMAN** | The user's input or question. |
| **ASSISTANT** | The model's own previous responses. Can be thought of as the "stored state" of the conversation that you re-inject so the LLM doesn't lose the thread. |

Example:

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("human", "Hi, who are you?"),
    ("assistant", "I am your RAG tutor! How can I help?"),
    ("human", "{question}")
])
```

---

## Defensive Programming in Multi-Agent State

In multi-agent systems, the state can sometimes be manipulated by different tools. `getattr` ensures that even if a message isn't a standard LangChain object, the "Evaluation Mode" logic won't crash the entire graph.

State Stability: It ensures the assessment node only triggers on valid user input, maintaining the "human-in-the-loop" oversight prioritized for AI systems.

---

## Content Extraction & Deterministic Evaluation Pipeline

The assessment infrastructure enables a "Source-of-Truth" evaluation pattern, syncing lesson content with AI-driven grading to ensure low-variance, objective scoring.

### Core Workflow

- **`_load_question_text`**: Uses modulo-based rotation to pick a fresh challenge from Markdown based on session length.
- **`_load_rubric_text`**: Extracts matching grading criteria (Correct/Partial/Incorrect) using regex to feed the LLM a deterministic "Answer Key."

### Pipeline

```
Slug → Index % Len → [Question + Rubric] → Evaluation Prompt → LLM Verdict
```
