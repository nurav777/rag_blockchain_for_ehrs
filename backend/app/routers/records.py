from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_doctor
from app.models.doctor import Doctor
from app.schemas.record import MedicalRecordResponse
from app.services.record_service import RecordUploadError, upload_medical_record

router = APIRouter()


@router.post("/upload", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
async def upload_record(
    patient_id: int = Form(..., gt=0),
    diagnosis: str = Form(..., min_length=1, max_length=500),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> MedicalRecordResponse:
    try:
        result = await upload_medical_record(
            db=db,
            doctor_id=current_doctor.id,
            patient_id=patient_id,
            diagnosis=diagnosis,
            file=file,
        )
        return MedicalRecordResponse.model_validate(result.record).model_copy(
            update={
                "ipfs_warning": result.ipfs_warning,
                "blockchain_warning": result.blockchain_warning,
            }
        )
    except RecordUploadError as exc:
        status_code = status.HTTP_404_NOT_FOUND if exc.message == "Patient not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=exc.message) from exc
