from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import require_api_key
from app.api.schemas import QueryRequest, QueryResponse
from app.services.query_service import run_query

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    result = run_query(request.question)
    if result["company_detection_error"]:
        raise HTTPException(status_code=404, detail=result["company_detection_error"])
    return QueryResponse(**result)
