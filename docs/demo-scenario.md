# Canonical Demo Scenario

This is the one path the repository should make obvious, runnable, and easy to
explain in an interview.

## Demo Promise

The demo proves that the system can:

- retrieve relevant RAG knowledge from local documents
- run the turn through a LangGraph state machine
- answer with retrieved context separated from generation
- infer lightweight knowledge-profile updates during the session
- reuse the updated session profile on the next response

## Scenario

The user is learning how LangGraph helps structure RAG applications. They first
ask a broad question, then ask a follow-up that should be shaped by the profile
signal extracted from the first turn.

### Turn 1

User message:

```text
I understand basic RAG, but I am confused about why LangGraph is useful. Can you explain it briefly?
```

Expected retrieval intent:

- find material about RAG pipeline stages
- find material about LangGraph/state-machine orchestration
- prefer concise explanatory context over deep implementation detail

Expected assistant behavior:

- explain that LangGraph makes the RAG flow explicit as state transitions
- mention retrieval, generation, assessment/profile-update as separate nodes
- keep the explanation concise because the user asked for brevity

Expected knowledge-profile update:

```text
- prefers concise explanations
- already understands basic RAG
- interested in LangGraph state machines
```

### Turn 2

User message:

```text
How would that profile update change the next answer?
```

Expected retrieval intent:

- retrieve material about session state and knowledge-profile updates
- connect profile state back to answer generation

Expected assistant behavior:

- explicitly use the session profile from turn 1
- answer concisely
- frame the explanation around LangGraph state passing and profile-aware prompts

Expected answer shape:

```text
Because your profile says you prefer concise explanations and already know basic
RAG, I would skip the introductory RAG recap and focus on the LangGraph state:
the retrieve node adds documents, the generate node uses those documents plus
your profile, and the update_profile node records new signals for the next turn.
```

## Transcript Contract

The runnable demo should print a transcript with these sections for each turn:

```text
User:
...

Retrieved context:
- ...
- ...

Assistant:
...

Knowledge profile:
- ...
```

Turn 2 must clearly show that the assistant is using the profile updates from
turn 1.

## Implementation Notes

- The default demo should use bundled local sample documents.
- The primary path uses OpenAI embeddings and OpenAI generation when
  `OPENAI_API_KEY` is configured.
- If `OPENAI_API_KEY` is missing, the demo routes to the fallback path:
  local Hugging Face embeddings for Chroma retrieval and Ollama for generation.
- To intentionally show the fallback path even with an API key configured, set
  `DEMO_FORCE_OLLAMA=true`.
- The Ollama fallback requires a running local Ollama server and the configured
  model to be pulled first, for example: `ollama pull gemma3:4b`.
- The README, smoke tests, and demo entry point should all follow this scenario.
