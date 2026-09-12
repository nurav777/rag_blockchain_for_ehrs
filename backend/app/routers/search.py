from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_wallet
from app.schemas.search import Citation, SearchRequest, SearchResponse
from app.services.rag_service import rag_service


router = APIRouter(
    tags=["search"],
)


@router.post(
    "/query",
    response_model=SearchResponse,
)
async def search_records(
    payload: SearchRequest,
    wallet_address: str = Depends(get_current_wallet),
) -> SearchResponse:

    answer, retrieved_chunks = await rag_service.answer(
        query=payload.query
    )

    citations = [
        Citation(
            record_hash=chunk.record_hash,
            ipfs_cid=chunk.ipfs_cid,
            chunk_index=chunk.chunk_index,
            blockchain_verified=chunk.blockchain_verified,
            score=chunk.score,
            excerpt=chunk.excerpt,
            source=chunk.source,
        )
        for chunk in retrieved_chunks
    ]

    return SearchResponse(
        query=payload.query,
        answer=answer,
        citations=citations,
    )