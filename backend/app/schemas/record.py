from pydantic import BaseModel


class MedicalRecordResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    diagnosis: str
    record_hash: str
    file_path: str
    ipfs_cid: str | None = None
    tx_hash: str | None = None
    ipfs_warning: str | None = None
    blockchain_warning: str | None = None

    model_config = {"from_attributes": True}
