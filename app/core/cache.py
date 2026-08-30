import hashlib
import json
from functools import lru_cache
from typing import Any

import redis

from app.core.config import get_settings


@lru_cache
def get_redis_client() -> redis.Redis:
    settings = get_settings()
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


def make_cache_key(namespace: str, *parts: str) -> str:
    raw = "|".join(part.strip().lower() for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{namespace}:{digest}"


def cache_get(key: str) -> Any | None:
    client = get_redis_client()
    raw = client.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    settings = get_settings()
    client = get_redis_client()
    client.set(key, json.dumps(value), ex=ttl or settings.cache_ttl_seconds)
