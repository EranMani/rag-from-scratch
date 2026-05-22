"""
Compatibility shim — assess_node has moved to agents.assessment.

Import path agents.nodes.assess is preserved for graph.py and any external references.
"""

from agents.assessment import assess_node  # noqa: F401
