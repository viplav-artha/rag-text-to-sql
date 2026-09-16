from app.core.cache import cache_get, cache_set, make_cache_key
from app.graph.graph import graph

_CACHE_NAMESPACE = "query"


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


def _is_cacheable(result: dict) -> bool:
    return (
        result["company_detection_error"] is None
        and result["validation_error"] is None
        and result["execution_error"] is None
    )


def run_query(question: str) -> dict:
    cache_key = make_cache_key(_CACHE_NAMESPACE, question)

    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    state = graph.invoke({"question": question})
    result = _extract_result(state)

    if _is_cacheable(result):
        cache_set(cache_key, result)

    return result


def run_query_no_cache(question: str) -> dict:
    state = graph.invoke({"question": question})
    return _extract_result(state)
