from fastapi import APIRouter, HTTPException

from app.api.schemas import QueryRequest, QueryResponse
from app.services.query_service import run_query, run_query_no_cache

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        result = run_query(request.company, request.question)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown company: {request.company!r}")
    return QueryResponse(**result)


@router.post("/query/no-cache", response_model=QueryResponse)
def query_no_cache(request: QueryRequest) -> QueryResponse:
    try:
        result = run_query_no_cache(request.company, request.question)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown company: {request.company!r}")
    return QueryResponse(**result)
