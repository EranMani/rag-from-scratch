# Adaptive Prompting — Level-Gated Prompt Engineering

## Core Concept

Rather than using a single prompt for all users, this system maintains **one prompt template per mastery level** (novice through expert). The factual grounding constraint stays constant; only explanation depth varies.

## The Invariant Constraint

Every prompt template, regardless of level, includes:

```
"Answer using ONLY the provided context."
```

This is **non-negotiable**. It prevents hallucination by grounding all responses in retrieved documents. Relaxing this per level would break the RAG guarantee.

## What Varies Per Level

| Level | Explanation Style |
|-------|-------------------|
| Novice | Analogies, plain language, define every term, step-by-step |
| Beginner | Simplified explanations, minimal jargon, concrete examples |
| Intermediate | Technical vocabulary allowed, assume basic understanding |
| Advanced | Concise, assume deep knowledge, focus on nuances |
| Expert | Dense, reference cutting-edge techniques, compare trade-offs |

## Template Resolution

```python
template = PROMPT_TEMPLATES.get(user_level, DEFAULT_PROMPT)
system_msg = template.format_messages(context=context)[0]
```

- Templates use `{context}` as the sole variable — resolved at call time, not at import time
- No f-strings at module level; `ChatPromptTemplate` handles interpolation safely
- `DEFAULT_PROMPT` is functionally identical to the pre-assessment fallback, ensuring zero regression when assessment hasn't run yet

## Message Assembly Pattern

```python
messages: list[BaseMessage] = [system_msg] + list(state["messages"])
response: BaseMessage = await llm.ainvoke(messages)
```

The `SystemMessage` is **prepended** (not appended) so the LLM sees it as role framing before any user content. The full conversation history follows, giving the model multi-turn context.

## Why Async (`ainvoke`)

- LLM calls are I/O-bound (network round-trip to the provider)
- `ainvoke` keeps the event loop alive, allowing concurrent request handling
- When wired with `graph.astream_events()`, token-level `on_chat_model_stream` events fire automatically — zero changes needed in the node
- A single async node naturally supports streaming responses to the frontend

## The `question` vs `messages` Distinction

- `state["messages"]` contains the full conversation (prior turns + current HumanMessage)
- `state["question"]` is a convenience copy of the current user input for retrieve_node
- `generate_node` does NOT read `question` — the current query is already the last HumanMessage in `messages`

This separation prevents double-reading and makes each node's input contract explicit.

## Provider Abstraction

```python
llm = get_provider().get_llm()
```

The LLM is never instantiated directly. `get_provider()` honours the OpenAI circuit breaker → Ollama fallback chain. This means:
- Model swaps require zero code changes in nodes
- Failure recovery is handled at the provider layer
- All nodes get the same resilience guarantees

## Key Takeaway

Adaptive prompting at the system level means:
- Prompts are **data** (stored in a dict/module), not inline strings scattered across functions
- The grounding constraint is separated from the style constraint
- Level detection and prompt selection are decoupled — scoring happens in `assess_node`, prompt selection happens in `generate_node`
- The system scales to new levels by adding a template, not modifying logic
