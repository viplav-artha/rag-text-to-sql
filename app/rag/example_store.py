from sqlalchemy import String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import RagBase
from app.rag.embeddings import get_embeddings
from app.rag.vector_utils import VectorJSON, cosine_similarity


class FewShotExample(RagBase):
    __tablename__ = "few_shot_examples"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(64))
    question: Mapped[str] = mapped_column(Text)
    sql: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(VectorJSON)


def add_example(db: Session, company: str, question: str, sql: str) -> FewShotExample:
    vector = get_embeddings().embed_query(question)
    example = FewShotExample(
        company=company, question=question, sql=sql, embedding=vector
    )
    db.add(example)
    db.flush()
    return example


def search_examples(
    db: Session, company: str, query: str, top_k: int = 3
) -> list[FewShotExample]:
    vector = get_embeddings().embed_query(query)
    stmt = select(FewShotExample).where(FewShotExample.company == company)
    candidates = list(db.execute(stmt).scalars().all())
    candidates.sort(key=lambda ex: cosine_similarity(vector, ex.embedding), reverse=True)
    return candidates[:top_k]
