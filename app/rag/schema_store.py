from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base
from app.rag.embeddings import get_embeddings


class SchemaChunk(Base):
    __tablename__ = "schema_chunks"
    __table_args__ = {"schema": "rag"}

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(64))
    schema_name: Mapped[str] = mapped_column(String(64))
    table_name: Mapped[str] = mapped_column(String(128))
    column_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    is_per_entity: Mapped[bool] = mapped_column(Boolean, default=False)


def add_schema_chunk(
    db: Session,
    company: str,
    schema_name: str,
    table_name: str,
    description: str,
    column_name: str | None = None,
    is_per_entity: bool = False,
) -> SchemaChunk:
    vector = get_embeddings().embed_query(description)
    chunk = SchemaChunk(
        company=company,
        schema_name=schema_name,
        table_name=table_name,
        column_name=column_name,
        description=description,
        embedding=vector,
        is_per_entity=is_per_entity,
    )
    db.add(chunk)
    db.flush()
    return chunk


def search_schema(
    db: Session,
    company: str,
    query: str,
    top_k: int = 5,
    is_per_entity: bool | None = None,
) -> list[SchemaChunk]:
    vector = get_embeddings().embed_query(query)
    stmt = select(SchemaChunk).where(SchemaChunk.company == company)
    if is_per_entity is not None:
        stmt = stmt.where(SchemaChunk.is_per_entity == is_per_entity)
    stmt = stmt.order_by(SchemaChunk.embedding.cosine_distance(vector)).limit(top_k)
    return list(db.execute(stmt).scalars().all())
