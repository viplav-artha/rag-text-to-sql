from langgraph.graph import END, START, StateGraph

from app.graph.execute_node import execute_sql_node, format_answer_node
from app.graph.nodes import generate_sql_node, retrieve_node, validate_sql_node
from app.graph.state import GraphState

_MAX_RETRIES = 2


def _route_after_validation(state: GraphState) -> str:
    if state.get("validation_error") and state.get("retry_count", 0) < _MAX_RETRIES:
        return "generate"
    return "execute"


def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("generate", generate_sql_node)
    workflow.add_node("validate", validate_sql_node)
    workflow.add_node("execute", execute_sql_node)
    workflow.add_node("format", format_answer_node)

    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", "validate")
    workflow.add_conditional_edges(
        "validate",
        _route_after_validation,
        {"generate": "generate", "execute": "execute"},
    )
    workflow.add_edge("execute", "format")
    workflow.add_edge("format", END)

    return workflow.compile()


graph = build_graph()
