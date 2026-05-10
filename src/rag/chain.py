"""
chain.py — RAG pipeline utilities.

run_rag_pipeline() and the SessionMemory import have been removed in Commit 10.
Conversation history is now managed by LangGraph's MemorySaver checkpointer
(keyed by thread_id / session_id) and the graph is streamed via astream_events()
in app/api/routes/chat.py.

The Redis query-level cache (rag.cache.redis_cache) is retained.  Per-user
cache invalidation is deferred to Commit 17.

Decision: this module is kept as a thin placeholder rather than deleted.
It may be extended in future commits for pipeline-level utilities that do
not belong in a graph node (e.g., cache warming helpers, analytics hooks).
Deleting it now would require updating several import paths; preserving it
as an empty module is the lower-risk choice at this stage of the project.
"""
