from typing import NotRequired, TypedDict

from app.rag.retriever import RetrievedContext


class GraphState(TypedDict):
    question: str
    company: NotRequired[str]
    company_detection_error: NotRequired[str | None]
    retrieved_context: NotRequired[RetrievedContext | None]
    generated_sql: NotRequired[str | None]
    validation_error: NotRequired[str | None]
    retry_count: NotRequired[int]
    sql_result: NotRequired[list[dict] | None]
    execution_error: NotRequired[str | None]
    final_answer: NotRequired[str | None]
