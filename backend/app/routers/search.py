from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_doctor
from app.models.doctor import Doctor
from app.schemas.search import SearchRequest, SearchResponse
from app.services.rag_service import RagError, rag_service

router = APIRouter()


@router.post("/query", response_model=SearchResponse)
async def search_records(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    _: Doctor = Depends(get_current_doctor),
) -> SearchResponse:
    try:
        answer, citations = await rag_service.search(db, payload.query)
        return SearchResponse(query=payload.query, answer=answer, citations=citations)
    except RagError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
