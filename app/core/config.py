import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    return value.strip()


@dataclass(frozen=True)
class Settings:
    database_url: str
    embedding_model_name: str
    rag_database_url: str


@lru_cache
def get_settings() -> Settings:
    database_url = _env("DATABASE_URL")
    embedding_model_name = _env("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    rag_database_url = _env("RAG_DATABASE_URL", "sqlite:///./rag_store.db")

    if not database_url:
        raise ValueError("DATABASE_URL not configured")

    return Settings(
        database_url=database_url,
        embedding_model_name=embedding_model_name,
        rag_database_url=rag_database_url,
    )
