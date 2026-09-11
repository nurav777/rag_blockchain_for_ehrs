from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.dependencies.auth import get_current_doctor
from app.models.doctor import Doctor
from app.schemas.search import (
    SearchRequest,
    SearchResponse,
)
from app.services.rag_service import (
    RagError,
    rag_service,
)


router = APIRouter()


@router.post(
    "/query",
    response_model=SearchResponse,
)
async def search_records(
    payload: SearchRequest,
    _: Doctor = Depends(
        get_current_doctor
    ),
) -> SearchResponse:
    """
    Search medical records semantically.

    Retrieval path:

        query
            -> query embedding
            -> ChromaDB top-k
            -> record_hash + chunk_index
            -> blockchain
            -> IPFS CID
            -> IPFS record
            -> relevant chunk
            -> Ollama

    SQLite is not involved in resolving medical records.
    """

    try:
        answer, citations = (
            await rag_service.search(
                query=payload.query
            )
        )

    except RagError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=exc.message,
        ) from exc

    return SearchResponse(
        query=payload.query,
        answer=answer,
        citations=citations,
    )