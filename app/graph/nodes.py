import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.db import rag_db_session
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


def _format_allowed_tables(tables: list[dict]) -> str:
    return "\n".join(f"- {t['schema']}.{t['table']}: {t['description']}" for t in tables)


def _table_in_sql(sql: str, table: dict) -> bool:
    return f"{table['schema']}.{table['table']}".lower() in sql.lower()


def _format_known_companies() -> str:
    lines = []
    for key, module in _COMPANY_DATA.items():
        summary = module.PROFILE.split(".")[0].strip() + "."
        lines.append(f"- {key}: {summary}")
    return "\n".join(lines)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def detect_company_node(state: GraphState) -> dict:
    system_prompt = (
        "You identify which company a financial question is about, from a "
        "fixed list of known companies.\n"
        "Known companies:\n"
        f"{_format_known_companies()}\n"
        "Respond with ONLY the exact company key from the list above (e.g. "
        "'futwork') that this question refers to — no explanation, no "
        "punctuation. If the question does not clearly name or match any "
        "company in that list, respond with exactly: UNKNOWN"
    )
    human_prompt = f"Question: {state['question']}"
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]

    llm = get_llm()
    response = llm.invoke(messages)
    detected = str(response.content).strip().strip(".\"'").lower()

    if detected not in _COMPANY_DATA:
        return {
            "company_detection_error": (
                f"Could not determine which known company this question refers "
                f"to (got: {detected!r})."
            ),
        }

    return {"company": detected, "company_detection_error": None}


def retrieve_node(state: GraphState) -> dict:
    with rag_db_session() as db:
        context = retrieve_context(db, state["company"], state["question"])
    return {"retrieved_context": context}


def generate_sql_node(state: GraphState) -> dict:
    company_data = _get_company_data(state["company"])
    tables_text = _format_allowed_tables(company_data.TABLES)

    context = state.get("retrieved_context")
    context_text = context.to_prompt_text() if context else "(no context retrieved)"

    system_prompt = (
        "You are a financial data analyst assistant that writes PostgreSQL SELECT queries.\n"
        "This company has the following table(s) available. Pick whichever one actually "
        "matches the question — you may only query a table from this list, never any "
        "other table or schema:\n"
        f"{tables_text}\n"
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
    allowed_tables = company_data.TABLES
    if not any(_table_in_sql(sql, table) for table in allowed_tables):
        allowed_names = ", ".join(f"{t['schema']}.{t['table']}" for t in allowed_tables)
        return {
            "validation_error": f"Generated SQL must query one of: {allowed_names}.",
            "retry_count": retry_count + 1,
        }

    return {"validation_error": None}
