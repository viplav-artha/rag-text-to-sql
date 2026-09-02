"""Runs the financial-QA eval experiment in LangSmith: invokes the full
LangGraph pipeline against every example in the financial-qa-eval-futwork
dataset (see create_financial_qa_dataset.py), and scores three things per
question — SQL execution accuracy, schema-retrieval recall, and whether the
final answer states the correct number/currency.

Run: python -m evals.run_financial_qa_eval
"""

import math
import re
from decimal import Decimal

from dotenv import load_dotenv
from langsmith import evaluate
from sqlalchemy import text

load_dotenv()

from app.core.db import db_session
from app.graph.execute_node import _serialize_value
from app.graph.graph import graph

DATASET_NAME = "financial-qa-eval-futwork"

_NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*")


def _run_reference_sql(sql: str) -> list[dict]:
    with db_session() as db:
        result = db.execute(text(sql))
        return [{key: _serialize_value(value) for key, value in row.items()} for row in result.mappings().all()]


def _normalize_rows(rows: list[dict]) -> list[tuple]:
    return sorted(tuple(sorted(row.items())) for row in rows)


def _project_rows(rows: list[dict], columns: list[str]) -> list[dict]:
    if not columns:
        return rows
    return [{key: value for key, value in row.items() if key in columns} for row in rows]


def _extract_numbers(text_value: str) -> list[float]:
    numbers = []
    for match in _NUMBER_PATTERN.findall(text_value):
        cleaned = match.replace(",", "")
        try:
            numbers.append(float(cleaned))
        except ValueError:
            continue
    return numbers


def run_pipeline(inputs: dict) -> dict:
    result = graph.invoke({"company": inputs["company"], "question": inputs["question"]})
    context = result.get("retrieved_context")
    retrieved_columns = (
        [chunk.column_name for chunk in context.schema_chunks if chunk.column_name] if context else []
    )
    return {
        "generated_sql": result.get("generated_sql"),
        "retrieved_columns": retrieved_columns,
        "sql_result": result.get("sql_result"),
        "final_answer": result.get("final_answer"),
        "validation_error": result.get("validation_error"),
        "execution_error": result.get("execution_error"),
    }


def execution_accuracy(outputs: dict, reference_outputs: dict) -> dict:
    expected_sql = reference_outputs.get("expected_sql")
    if not expected_sql:
        return {"key": "execution_accuracy", "score": None, "comment": "No expected_sql to compare against."}

    expected_columns = reference_outputs.get("expected_columns") or []
    expected_rows = _project_rows(_run_reference_sql(expected_sql), expected_columns)
    actual_rows = _project_rows(outputs.get("sql_result") or [], expected_columns)

    # Project both sides down to just the expected columns so extra columns the
    # generated SQL adds (e.g. a helpful computed "variance") aren't penalized —
    # only whether the columns actually asked for are correct.
    score = 1.0 if _normalize_rows(actual_rows) == _normalize_rows(expected_rows) else 0.0
    return {"key": "execution_accuracy", "score": score}


def retrieval_recall(outputs: dict, reference_outputs: dict) -> dict:
    expected_columns = set(reference_outputs.get("expected_columns") or [])
    if not expected_columns:
        return {"key": "retrieval_recall", "score": None, "comment": "No expected_columns to check."}

    retrieved_columns = set(outputs.get("retrieved_columns") or [])
    found = expected_columns & retrieved_columns
    return {"key": "retrieval_recall", "score": len(found) / len(expected_columns)}


def answer_groundedness(outputs: dict, reference_outputs: dict) -> dict:
    final_answer = outputs.get("final_answer") or ""
    expected_sql = reference_outputs.get("expected_sql")
    expected_rows = _run_reference_sql(expected_sql) if expected_sql else []

    if not expected_rows:
        return {"key": "answer_groundedness", "score": None, "comment": "No reference rows to ground against."}

    expected_numbers = [
        float(value) for row in expected_rows for value in row.values() if isinstance(value, (int, float, Decimal))
    ]
    found_numbers = _extract_numbers(final_answer)

    # Tolerance-based comparison, not exact string matching — a human-readable
    # rounded answer (e.g. "13.41 months" for 13.409774217733494) is correct,
    # not ungrounded. rel_tol handles rounding on large numbers; abs_tol
    # handles rounding on small ones.
    mentions_expected_number = any(
        math.isclose(expected, found, rel_tol=1e-3, abs_tol=0.05)
        for expected in expected_numbers
        for found in found_numbers
    )
    mentions_wrong_currency = "$" in final_answer or "USD" in final_answer.upper()

    score = 1.0 if (mentions_expected_number and not mentions_wrong_currency) else 0.0
    return {"key": "answer_groundedness", "score": score}


if __name__ == "__main__":
    evaluate(
        run_pipeline,
        data=DATASET_NAME,
        evaluators=[execution_accuracy, retrieval_recall, answer_groundedness],
        experiment_prefix="financial-qa",
    )
