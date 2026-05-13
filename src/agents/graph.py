"""
graph.py — LangGraph graph factory for the adaptive-RAG pipeline.

Factory function pattern: build_graph() is called once at application startup
inside the FastAPI lifespan and stored on app.state.rag_graph.  No module-level
singleton is created here.

Graph topology (Commit 15):
    START → retrieve_node → generate_node → assess_node
                                                ↓ (assessment_error == False)
                                          update_profile_node → END
                                                ↓ (assessment_error == True)
                                          update_profile_node → END   (skips DB write)

Both the normal path and the fallback path converge at update_profile_node.
update_profile_node guards internally on assessment_error — no DB write on fallback path.

Recursion limit is set defensively at compile time via graph_config to prevent
an unconstrained loop from blocking a user request indefinitely.
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.nodes.assess import assess_node
from agents.nodes.generate import generate_node
from agents.nodes.retrieve import retrieve_node
from agents.nodes.update_profile import update_profile_node
from agents.state import AgentState

# Maximum number of node transitions before LangGraph raises GraphRecursionError.
# With a 4-node linear graph this limit cannot be reached legitimately; it guards
# against graph wiring bugs or future conditional edge cycles.
_RECURSION_LIMIT: int = 10


# ---------------------------------------------------------------------------
# Conditional edge — reads assessment_error from state
# ---------------------------------------------------------------------------

def _route_after_assess(state: AgentState) -> str:
    """Routes assess_node output to update_profile_node.

    Both paths (assessment_error True and False) converge at update_profile_node.
    update_profile_node guards internally on assessment_error — the conditional edge
    is kept for graph visualization and future divergence if the paths split.
    """
    return "update_profile"


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

    # StateGraph allows to create a state machine workflow
    # AgentState passes through all the nodes and conditional edges
    """ 
    NOTE: A node reads the data from agent state and can update or new information to it
    StateGraph built-in persistence manages the workflow state in a single object
    Allows to pause, save and resume process at any time
    This brings stateful memory to traditionally stateless web applications
    """
    builder: StateGraph = StateGraph(AgentState)

    # Nodes
    builder.add_node("retrieve", retrieve_node) # Retrieve => extract relevant documents based on the user's question
    builder.add_node("generate", generate_node) # Generate => generates a level-appropriate, context-aware AI response
    builder.add_node("assess", assess_node) # 
    builder.add_node("update_profile", update_profile_node)

    # Edges
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", "assess")

    # Conditional edge: both True and False paths lead to update_profile.
    # Using add_conditional_edges makes the branching explicit and inspectable
    # (LangGraph visualization / get_graph() will show both paths).
    builder.add_conditional_edges(
        "assess",
        _route_after_assess,
        {
            "update_profile": "update_profile",
        },
    )

    builder.add_edge("update_profile", END)

    return builder.compile(
        checkpointer=checkpointer,
        # recursion_limit is enforced by LangGraph at graph invocation time.
        # Passing it here bakes it into the compiled graph's default config.
    ).with_config({"recursion_limit": _RECURSION_LIMIT})
