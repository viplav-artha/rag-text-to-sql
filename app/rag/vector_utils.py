import json
import math

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


class VectorJSON(TypeDecorator):
    """Stores a list[float] embedding as a JSON-encoded string column.

    SQLite has no native vector column type (unlike pgvector on Postgres,
    used before the RAG store moved off Neon) — this keeps every ORM model
    that holds an embedding unchanged in shape while storing it as plain
    portable JSON text under the hood.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: list[float] | None, dialect) -> str | None:
        return json.dumps(value) if value is not None else None

    def process_result_value(self, value: str | None, dialect) -> list[float] | None:
        return json.loads(value) if value is not None else None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
