from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base
from app.rag.embeddings import get_embeddings


class FewShotExample(Base):
    __tablename__ = "few_shot_examples"
    __table_args__ = {"schema": "rag"}

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(64))
    question: Mapped[str] = mapped_column(Text)
    sql: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))


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
    stmt = (
        select(FewShotExample)
        .where(FewShotExample.company == company)
        .order_by(FewShotExample.embedding.cosine_distance(vector))
        .limit(top_k)
    )
    return list(db.execute(stmt).scalars().all())
