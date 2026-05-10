"""
graph.py — LangGraph graph factory for the adaptive-RAG pipeline.

Factory function pattern: build_graph() is called once at application startup
inside the FastAPI lifespan and stored on app.state.rag_graph.  No module-level
singleton is created here.

Graph topology (Commit 10 — linear):
    START → retrieve_node → generate_node → END

Later commits will add assess_node and profile_update_node between generate and END.

Recursion limit is set defensively at compile time via graph_config to prevent
an unconstrained loop from blocking a user request indefinitely.
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.nodes.generate import generate_node
from agents.nodes.retrieve import retrieve_node
from agents.state import AgentState

# Maximum number of node transitions before LangGraph raises GraphRecursionError.
# A linear 2-node graph cannot legitimately exceed this value; it exists as a
# hard guardrail against graph wiring bugs or future conditional edge cycles.
_RECURSION_LIMIT: int = 10


def build_graph(checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    """Build and compile the LangGraph RAG graph.

    Args:
        checkpointer: A LangGraph checkpoint saver.  In production this is a
            MemorySaver instance created once in the FastAPI lifespan.  In tests
            a MemorySaver or any BaseCheckpointSaver mock may be passed.

    Returns:
        A compiled LangGraph StateGraph ready for astream_events() calls.
        The graph is stateful via the checkpointer — cross-turn history is
        replayed automatically from the checkpoint keyed by thread_id.
    """
    builder: StateGraph = StateGraph(AgentState)

    # Nodes
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)

    # Edges
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", END)

    return builder.compile(
        checkpointer=checkpointer,
        # recursion_limit is enforced by LangGraph at graph invocation time.
        # Passing it here bakes it into the compiled graph's default config.
    ).with_config({"recursion_limit": _RECURSION_LIMIT})
