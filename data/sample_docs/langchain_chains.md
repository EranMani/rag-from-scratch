# LangChain Chains

LangChain chains compose model calls, prompts, retrievers, and parsers into a
linear or branching workflow. A chain is useful when the application flow is
mostly predictable: retrieve context, format a prompt, call a model, and parse
the result.

Compared with a LangGraph state machine, a chain is usually simpler to read for
straight-line tasks. LangGraph becomes more useful when the application needs
durable state, conditional routing, retries, tool loops, or profile updates
across turns.
