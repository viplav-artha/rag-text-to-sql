from app.core.cache import cache_get, cache_set, make_cache_key
from app.graph.graph import graph

_CACHE_NAMESPACE = "query"


def _extract_result(state: dict) -> dict:
    return {
        "generated_sql": state.get("generated_sql"),
        "sql_result": state.get("sql_result"),
        "final_answer": state.get("final_answer"),
        "validation_error": state.get("validation_error"),
        "execution_error": state.get("execution_error"),
    }


def run_query(company: str, question: str) -> dict:
    cache_key = make_cache_key(_CACHE_NAMESPACE, company, question)

    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    state = graph.invoke({"company": company, "question": question})
    result = _extract_result(state)

    if result["validation_error"] is None and result["execution_error"] is None:
        cache_set(cache_key, result)

    return result
