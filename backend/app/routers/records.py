from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies.auth import get_current_wallet
from app.schemas.auth import WalletIdentity
from app.schemas.record import MedicalRecordResponse
from app.services.record_service import RecordUploadError, upload_medical_record


router = APIRouter()


@router.post(
    "/upload",
    response_model=MedicalRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_record(
    file: UploadFile = File(...),
    wallet: WalletIdentity = Depends(get_current_wallet),
) -> MedicalRecordResponse:
    """
    Upload a medical record using the authenticated clinician wallet.

    There is no patient database lookup and no patient ID in the API.
    The backend never needs a patient name to store or retrieve a record.
    """
    try:
        result = await upload_medical_record(
            uploader_wallet=wallet.wallet_address,
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
        uploader_wallet=result.uploader_wallet,
        indexing_warning=result.indexing_warning,
    )
