from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.rag  # noqa: F401 -- ensures all RAG models are registered before create_all()
from app.api.routes import router
from app.core.db import RagBase, rag_engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    RagBase.metadata.create_all(rag_engine)
    yield


app = FastAPI(title="rag-text-to-sql", lifespan=lifespan)
app.include_router(router)
