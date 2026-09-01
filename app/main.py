from fastapi import FastAPI
from pydantic import BaseModel

from app.graph.graph import graph

app = FastAPI(title="rag-text-to-sql (test harness)")


class QueryRequest(BaseModel):
    company: str
    question: str


class QueryResponse(BaseModel):
    generated_sql: str | None = None
    sql_result: list[dict] | None = None
    final_answer: str | None = None
    validation_error: str | None = None
    execution_error: str | None = None


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    result = graph.invoke({"company": request.company, "question": request.question})
    return QueryResponse(
        generated_sql=result.get("generated_sql"),
        sql_result=result.get("sql_result"),
        final_answer=result.get("final_answer"),
        validation_error=result.get("validation_error"),
        execution_error=result.get("execution_error"),
    )
