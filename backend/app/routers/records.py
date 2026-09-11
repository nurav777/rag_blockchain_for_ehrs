from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_doctor
from app.models.doctor import Doctor
from app.schemas.record import MedicalRecordResponse
from app.services.record_service import (
    RecordUploadError,
    upload_medical_record,
)


router = APIRouter()


@router.post(
    "/upload",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_record(
    patient_id: int = Form(..., gt=0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> MedicalRecordResponse:
    """
    Upload a medical record.

    Flow:
        1. Authenticate doctor.
        2. Resolve the patient.
        3. Validate the PDF.
        4. Calculate the record SHA-256 hash.
        5. Upload the record to IPFS.
        6. Register hash -> CID on the blockchain.
        7. Index embeddings in ChromaDB.

    The backend does not permanently store the uploaded PDF and does
    not create a MedicalRecord row in SQLite.
    """

    try:
        result = await upload_medical_record(
            db=db,
            doctor_id=current_doctor.id,
            patient_id=patient_id,
            file=file,
        )

    except RecordUploadError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc

    return MedicalRecordResponse(
        record_hash=result.record_hash,
        ipfs_cid=result.ipfs_cid,
        tx_hash=result.tx_hash,
        indexing_warning=result.indexing_warning,
    )