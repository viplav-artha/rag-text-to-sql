import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.db import db_session
from app.core.llm import get_llm
from app.graph.state import GraphState
from app.rag.retriever import retrieve_context
from data.companies import futwork

_COMPANY_DATA = {
    "futwork": futwork,
}

_FORBIDDEN_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "MERGE",
    "CALL",
    "EXECUTE",
)


def _get_company_data(company: str):
    return _COMPANY_DATA[company]


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def retrieve_node(state: GraphState) -> dict:
    with db_session() as db:
        context = retrieve_context(db, state["company"], state["question"])
    return {"retrieved_context": context}


def generate_sql_node(state: GraphState) -> dict:
    company_data = _get_company_data(state["company"])
    allowed_table = f"{company_data.SCHEMA_NAME}.{company_data.TABLE_NAME}"

    context = state.get("retrieved_context")
    context_text = context.to_prompt_text() if context else "(no context retrieved)"

    system_prompt = (
        "You are a financial data analyst assistant that writes PostgreSQL SELECT queries.\n"
        f"You may only query the table {allowed_table} — never any other table or schema.\n"
        "Only ever write SELECT statements — never INSERT, UPDATE, DELETE, DROP, ALTER, or "
        "any other data-modifying or schema-modifying statement.\n"
        "When filtering by month_name, always use the lowercase full month name (e.g. "
        "'march', 'december') — Postgres string comparison is case-sensitive and the "
        "stored values are lowercase.\n"
        "Respond with ONLY the SQL query — no explanation, no markdown code fences."
    )

    human_prompt = f"{context_text}\n\nQuestion: {state['question']}"
    if state.get("validation_error"):
        human_prompt += (
            f"\n\nThe previous SQL you generated was invalid: {state['validation_error']}\n"
            "Please generate a corrected query."
        )

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]

    llm = get_llm()
    response = llm.invoke(messages)
    sql = _strip_code_fences(str(response.content))

    return {"generated_sql": sql}


def validate_sql_node(state: GraphState) -> dict:
    sql = state.get("generated_sql") or ""
    upper_sql = sql.upper().strip()
    retry_count = state.get("retry_count", 0)

    if not upper_sql.startswith("SELECT"):
        return {
            "validation_error": "Generated SQL must be a SELECT statement.",
            "retry_count": retry_count + 1,
        }

    for keyword in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper_sql):
            return {
                "validation_error": f"Generated SQL contains forbidden keyword: {keyword}.",
                "retry_count": retry_count + 1,
            }

    company_data = _get_company_data(state["company"])
    allowed_table = f"{company_data.SCHEMA_NAME}.{company_data.TABLE_NAME}"
    if allowed_table.lower() not in sql.lower():
        return {
            "validation_error": f"Generated SQL must query {allowed_table}.",
            "retry_count": retry_count + 1,
        }

    return {"validation_error": None}
