import json
import re
from datetime import date, datetime
from decimal import Decimal

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import text

from app.core.db import db_session
from app.core.llm import get_llm
from app.graph.state import GraphState

_ROW_LIMIT = 500
_STATEMENT_TIMEOUT_MS = 10_000


def _apply_row_limit(sql: str, limit: int = _ROW_LIMIT) -> str:
    cleaned = sql.strip().rstrip(";")
    if re.search(r"\bLIMIT\b", cleaned, re.IGNORECASE):
        return cleaned
    return f"SELECT * FROM ({cleaned}) AS limited_query LIMIT {limit}"


def _serialize_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def execute_sql_node(state: GraphState) -> dict:
    if state.get("validation_error"):
        return {
            "execution_error": f"Refusing to execute unvalidated SQL: {state['validation_error']}",
            "sql_result": None,
        }

    sql = _apply_row_limit(state["generated_sql"])

    try:
        with db_session() as db:
            db.execute(text(f"SET LOCAL statement_timeout = {_STATEMENT_TIMEOUT_MS}"))
            result = db.execute(text(sql))
            rows = [
                {key: _serialize_value(value) for key, value in row.items()}
                for row in result.mappings().all()
            ]
    except Exception as exc:
        return {"execution_error": str(exc), "sql_result": None}

    return {"sql_result": rows, "execution_error": None}


def format_answer_node(state: GraphState) -> dict:
    if state.get("execution_error"):
        return {
            "final_answer": (
                "I generated a SQL query for your question, but it failed to run: "
                f"{state['execution_error']}"
            )
        }

    rows = state.get("sql_result") or []
    if not rows:
        return {"final_answer": "I ran the query, but it returned no results."}

    context = state.get("retrieved_context")
    business_context = (context.company_profile if context else None) or "(no business context available)"

    system_prompt = (
        "You are a financial analyst assistant. Given a user's question and the SQL "
        "query results (as JSON rows), answer the question in plain, concise natural "
        "language. Reference the actual numbers from the results, using whatever "
        "currency/units are established in the business context below — do not assume "
        "USD or any other default. Do not mention SQL or the underlying table/column names."
    )
    human_prompt = (
        f"Business context: {business_context}\n\n"
        f"Question: {state['question']}\n\n"
        f"Query results (JSON): {json.dumps(rows, default=str)}"
    )

    llm = get_llm()
    response = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
    )
    return {"final_answer": str(response.content).strip()}
