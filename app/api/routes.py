from fastapi import APIRouter, HTTPException

from app.api.schemas import QueryRequest, QueryResponse
from app.services.query_service import run_query

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        result = run_query(request.company, request.question)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown company: {request.company!r}")
    return QueryResponse(**result)
