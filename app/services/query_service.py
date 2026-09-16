from app.graph.graph import graph


def _extract_result(state: dict) -> dict:
    return {
        "company": state.get("company"),
        "company_detection_error": state.get("company_detection_error"),
        "generated_sql": state.get("generated_sql"),
        "sql_result": state.get("sql_result"),
        "final_answer": state.get("final_answer"),
        "validation_error": state.get("validation_error"),
        "execution_error": state.get("execution_error"),
    }


def run_query(question: str) -> dict:
    state = graph.invoke({"question": question})
    return _extract_result(state)
