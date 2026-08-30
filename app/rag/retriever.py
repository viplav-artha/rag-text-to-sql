from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.rag.company_profile import get_company_profile
from app.rag.example_store import FewShotExample, search_examples
from app.rag.schema_store import SchemaChunk, search_schema


@dataclass(frozen=True)
class RetrievedContext:
    company_profile: str | None
    schema_chunks: list[SchemaChunk]
    examples: list[FewShotExample]

    def to_prompt_text(self) -> str:
        schema_lines = "\n".join(
            f"- {chunk.schema_name}.{chunk.table_name}"
            + (f".{chunk.column_name}" if chunk.column_name else "")
            + f": {chunk.description}"
            for chunk in self.schema_chunks
        )
        example_lines = "\n\n".join(
            f"Q: {example.question}\nSQL: {example.sql}" for example in self.examples
        )
        return (
            "Business context:\n"
            f"{self.company_profile or '(none found)'}\n\n"
            "Relevant schema:\n"
            f"{schema_lines or '(none found)'}\n\n"
            "Similar past examples:\n"
            f"{example_lines or '(none found)'}"
        )


def retrieve_context(
    db: Session,
    company: str,
    question: str,
    schema_top_k: int = 5,
    example_top_k: int = 3,
) -> RetrievedContext:
    profile = get_company_profile(db, company)
    schema_chunks = search_schema(db, company, question, top_k=schema_top_k)
    examples = search_examples(db, company, question, top_k=example_top_k)
    return RetrievedContext(
        company_profile=profile.profile if profile else None,
        schema_chunks=schema_chunks,
        examples=examples,
    )
