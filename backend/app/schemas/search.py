from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)


class Citation(BaseModel):
    record_id: int
    patient_id: int
    diagnosis: str
    record_hash: str
    ipfs_cid: str | None = None
    blockchain_verified: bool
    score: float
    excerpt: str
    source: str


class SearchResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation]
