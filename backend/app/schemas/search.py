from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """
    Semantic query submitted by an authenticated doctor.
    """

    query: str = Field(
        min_length=1,
        max_length=1000,
    )


class Citation(BaseModel):
    """
    Reference to one relevant chunk retrieved from an IPFS-backed
    medical record.

    No SQLite medical-record ID is involved.
    """

    record_hash: str
    ipfs_cid: str
    chunk_index: int

    blockchain_verified: bool

    score: float

    excerpt: str
    source: str


class SearchResponse(BaseModel):
    """
    RAG response containing the generated answer and the retrieved
    record chunks that supported it.
    """

    query: str
    answer: str
    citations: list[Citation]