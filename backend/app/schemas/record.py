from pydantic import BaseModel


class MedicalRecordResponse(BaseModel):
    """
    Response returned after a medical record has been successfully
    stored in IPFS and registered on the blockchain.

    The backend does not persist the medical record itself in SQLite
    or on the local filesystem.
    """

    record_hash: str
    ipfs_cid: str
    tx_hash: str

    indexing_warning: str | None = None
