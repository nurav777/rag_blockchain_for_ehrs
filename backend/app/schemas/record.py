from pydantic import BaseModel


class MedicalRecordResponse(BaseModel):
    record_hash: str
    ipfs_cid: str
    tx_hash: str
    uploader_wallet: str
    indexing_warning: str | None = None
