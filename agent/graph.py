"""Build and run the LangGraph workflow."""

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from agent.injection import defence_on, find_injection
from agent.nodes import (
    classifier_node,
    coder_node,
    researcher_node,
    reviewer_node,
    should_refine,
)
from agent.redact import redact_secrets
from agent.schemas import AgentState, initial_state


def build_graph():
    """Compile the agent workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("classifier", classifier_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("reviewer", reviewer_node)

    workflow.add_edge(START, "classifier")
    workflow.add_edge("classifier", "researcher")
    workflow.add_edge("researcher", "coder")
    workflow.add_edge("coder", "reviewer")

    workflow.add_conditional_edges(
        "reviewer",
        should_refine,
        {
            "research": "researcher",
            "finish": END
        }
    )

    return workflow.compile()


graph = build_graph()


def run_agent(error: str, on_step: Callable[[str, dict], None] | None = None) -> AgentState:
    """Run one full troubleshooting pass and return the final state.

    on_step, if given, is called with each finished node's name and update.
    Secrets are masked first, so no step can send them to the LLM or search.
    """
    clean_error, redactions = redact_secrets(error)
    warnings = find_injection(clean_error) if defence_on() else []
    state = initial_state(clean_error, redactions, warnings)
    final_state = None

    for mode, chunk in graph.stream(state, stream_mode=["updates", "values"]):
        if mode == "values":
            final_state = chunk
        elif on_step:
            for node, update in chunk.items():
                on_step(node, update)

    return final_state
