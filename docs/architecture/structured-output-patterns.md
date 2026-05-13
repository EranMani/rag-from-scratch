# Structured Output Patterns — Making LLMs Behave Like Software

## The Problem

LLMs produce free-form text. Software systems need typed, validated data. The gap between these two worlds is where most AI engineering bugs live.

## The Pipe-and-Filter Chain

```python
chain = prompt | llm.with_structured_output(PydanticSchema)
result = await chain.ainvoke({"question": user_input})
```

This single line encapsulates three stages:

1. **Prompt** — formats the input into a structured message sequence
2. **LLM** — generates a response constrained to the schema
3. **Parser** — validates the response into a typed Pydantic object

The `|` operator creates an **atomic unit**: if any stage fails, the entire chain fails cleanly. No "half-baked" data ever reaches the system state.

## Why Pydantic Schemas

```python
class EvaluationOutput(BaseModel):
    verdict: Literal["correct", "partial", "incorrect"]
    confidence: float
    identified_gaps: list[str]
    user_level: Literal["novice", "beginner", "intermediate", "advanced", "expert"]
```

- Forces the LLM to map natural language into **exact types**
- Eliminates free-text parsing, regex extraction, or string matching
- Provides compile-time guarantees downstream — every consumer knows the shape
- Failed validation raises immediately rather than silently corrupting state

## The OpenAI Strictness Workaround

OpenAI's structured output rejects schemas with `additionalProperties` (which `dict[str, float]` produces). The solution: explicit class-based schemas with one field per valid key.

```python
class TopicScoresDelta(BaseModel):
    embeddings_and_similarity: float = 0.0
    rag_pipeline_architecture: float = 0.0
    chunking_strategies: float = 0.0
    # ... one field per valid slug
```

This generates a **closed object schema** that OpenAI accepts. The trade-off: less flexible, but provider-compatible and self-documenting.

## Prompt Structure Standard

All prompts in this project follow a consistent structure:

```
role → task → constraints → output format
```

- **Role**: who the LLM is ("You are a curriculum evaluator...")
- **Task**: what it must do ("Evaluate the learner's answer against the rubric...")
- **Constraints**: hard boundaries ("verdict MUST be exactly one of: correct, partial, incorrect")
- **Output format**: implied by the Pydantic schema via `.with_structured_output()`

## Error Boundaries

```python
try:
    chain = prompt | llm.with_structured_output(Schema)
    result = await chain.ainvoke(inputs)
except Exception:
    logger.warning("LLM call failed", exc_info=True)
    return fallback_value
```

Every LLM chain is wrapped in a try/except that:
- Logs the failure with full traceback
- Returns a well-defined fallback (empty dict, error flag, etc.)
- Never lets a failed LLM call crash the graph or pollute state

This is the "Functional Chaining & Resilience" principle: atomic chains that either succeed fully or fail predictably.

## Async Invocation

```python
result = await chain.ainvoke({"question": question})
```

- `ainvoke` is non-blocking — keeps the event loop alive while waiting for the LLM response
- LLM calls are I/O-heavy; async allows handling many concurrent requests with minimal resources
- Supports streaming: when wired with `astream_events()`, token-level events fire automatically

## Key Takeaway

Structured output is the bridge between probabilistic AI and deterministic software. By forcing every LLM response through a Pydantic schema, you get:
- Type safety at the boundary
- Atomic success/failure semantics
- Self-documenting contracts between nodes
- Provider-agnostic code (swap models without changing consumers)
