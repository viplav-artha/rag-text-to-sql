from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def _strip_and_reject_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class QueryResponse(BaseModel):
    company: str | None = None
    company_detection_error: str | None = None
    generated_sql: str | None = None
    sql_result: list[dict] | None = None
    final_answer: str | None = None
    validation_error: str | None = None
    execution_error: str | None = None
