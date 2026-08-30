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


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    if value in (None, ""):
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str
    embedding_model_name: str
    cache_ttl_seconds: int


@lru_cache
def get_settings() -> Settings:
    database_url = _env("DATABASE_URL")
    redis_url = _env("REDIS_URL")
    embedding_model_name = _env("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    cache_ttl_seconds = _env_int("CACHE_TTL_SECONDS", 3600)

    if not database_url:
        raise ValueError("DATABASE_URL not configured")
    if not redis_url:
        raise ValueError("REDIS_URL not configured")

    return Settings(
        database_url=database_url,
        redis_url=redis_url,
        embedding_model_name=embedding_model_name,
        cache_ttl_seconds=cache_ttl_seconds,
    )
