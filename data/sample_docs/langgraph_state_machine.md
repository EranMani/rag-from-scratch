# LangGraph State Machines for RAG

LangGraph is useful for RAG because it turns a conversation pipeline into an
explicit state machine. A user message enters the graph, the retrieve node adds
documents to state, the generate node writes an answer, and a profile-update
node records what the turn revealed.

This shape is easier to test than a single opaque chain because each node has a
clear input and output contract.
