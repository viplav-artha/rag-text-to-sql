from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


def _to_psycopg_url(database_url: str) -> str:
    if database_url.startswith("postgresql+"):
        return database_url
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


settings = get_settings()

# Neon Postgres: holds each company's real financial data table (e.g.
# portfolio.futwork_vs_aop) — queried directly with raw SQL by
# execute_sql_node, never through the ORM, so no models are registered on
# `Base` today.
engine = create_engine(_to_psycopg_url(settings.database_url), pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# SQLite: the RAG bookkeeping tables (schema_chunks, few_shot_examples,
# company_profiles) — created locally at runtime (app/main.py's lifespan
# hook), independent of Neon. `check_same_thread=False` because FastAPI
# runs sync endpoints in a threadpool, not necessarily the thread that
# opened the connection.
rag_engine = create_engine(settings.rag_database_url, connect_args={"check_same_thread": False})

RagSessionLocal = sessionmaker(bind=rag_engine, autoflush=False, autocommit=False, expire_on_commit=False)


class RagBase(DeclarativeBase):
    pass


@contextmanager
def rag_db_session() -> Generator[Session, None, None]:
    db = RagSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
