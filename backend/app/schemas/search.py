from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Semantic query submitted by an authenticated clinician wallet."""

    query: str = Field(min_length=1, max_length=1000)


class Citation(BaseModel):
    record_hash: str
    ipfs_cid: str
    chunk_index: int
    blockchain_verified: bool
    score: float
    excerpt: str
    source: str


class SearchResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation]
