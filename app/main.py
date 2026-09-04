from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.rag  # noqa: F401 -- ensures all RAG models are registered before create_all()
from app.api.routes import router
from app.core.db import Base, engine, init_pgvector_extension


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_pgvector_extension()
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="rag-text-to-sql", lifespan=lifespan)
app.include_router(router)
