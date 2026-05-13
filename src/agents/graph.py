"""
graph.py — LangGraph graph factory for the adaptive-RAG pipeline.

Factory function pattern: build_graph() is called once at application startup
inside the FastAPI lifespan and stored on app.state.rag_graph.  No module-level
singleton is created here.

Graph Flow:
    ┌───────┐     ┌──────────┐     ┌──────────┐     ┌────────┐     ┌────────────────┐     ┌─────┐
    │ START │────▶│ retrieve │────▶│ generate │────▶│ assess │────▶│ update_profile │────▶│ END │
    └───────┘     └──────────┘     └──────────┘     └────┬───┘     └────────────────┘     └─────┘
                   Fetch docs       Produce AI           │                  │
                   from vector      response grounded    │                  │
                   store            in retrieved context  │                  │
                                                         │                  │
                                              ┌──────────┴──────────┐       │
                                              │  assessment_error?  │       │
                                              └──────────┬──────────┘       │
                                               No │          │ Yes          │
                                                  ▼          ▼              │
                                              scores +    count++           │
                                              count++     only              │
                                                  └──────────┘              │
                                                         │                  │
                                                         └──────────────────┘

Both conditional paths converge at update_profile_node, which guards
internally on assessment_error — no score write on the fallback path.

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

    # Nodes — each reads from AgentState and writes back its output keys
    builder.add_node("retrieve", retrieve_node) # Retrieve => extract relevant documents based on the user's question
    builder.add_node("generate", generate_node) # Generate => generates a level-appropriate, context-aware AI response
    builder.add_node("assess", assess_node)     # Assess => evaluates mastery via passive inference or curriculum-based testing
    builder.add_node("update_profile", update_profile_node)  # Update Profile => persists score deltas and interaction count to the user DB

    # Edges — define the sequential pipeline and conditional branching
    builder.add_edge(START, "retrieve")      # User query enters → fetch relevant documents
    builder.add_edge("retrieve", "generate") # Documents ready → produce AI response grounded in context
    builder.add_edge("generate", "assess")   # Response delivered → evaluate user mastery for this turn

    # Conditional edge: after assess, a routing function decides the next node.
    # Currently both paths lead to update_profile (which guards internally on
    # assessment_error). Structured as conditional so LangGraph's get_graph()
    # renders both branches — ready for future divergence if paths split.
    builder.add_conditional_edges(
        "assess",                              # Source node: where the edge originates
        _route_after_assess,                   # Router function: inspects state, returns target node name
        {"update_profile": "update_profile"},  # Path map: {router return value → destination node}
    )

    builder.add_edge("update_profile", END) # Profile persisted → turn complete

    return builder.compile(
        checkpointer=checkpointer,
        # recursion_limit is enforced by LangGraph at graph invocation time.
        # Passing it here bakes it into the compiled graph's default config.
    ).with_config({"recursion_limit": _RECURSION_LIMIT})
