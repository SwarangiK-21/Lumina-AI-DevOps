"""Build and run the LangGraph workflow."""

from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    classifier_node,
    coder_node,
    researcher_node,
    reviewer_node,
    should_refine,
)
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


def run_agent(error: str) -> AgentState:
    """Run one full troubleshooting pass and return the final state."""
    return graph.invoke(initial_state(error))
