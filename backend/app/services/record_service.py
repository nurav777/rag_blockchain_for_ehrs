import hashlib
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT, settings
from app.models.medical_record import MedicalRecord
from app.services.blockchain_service import BlockchainError, blockchain_service
from app.services.patient_service import get_patient_by_id
from app.services.pinata_service import PinataUploadError, is_pinata_configured, upload_pdf_to_pinata
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF"
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


class RecordUploadError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class RecordUploadResult:
    def __init__(
        self,
        record: MedicalRecord,
        ipfs_warning: str | None = None,
        blockchain_warning: str | None = None,
    ) -> None:
        self.record = record
        self.ipfs_warning = ipfs_warning
        self.blockchain_warning = blockchain_warning


def validate_pdf(filename: str, content_type: str | None, content: bytes) -> None:
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    if not content:
        raise RecordUploadError("Uploaded file is empty")

    if len(content) > max_bytes:
        raise RecordUploadError(f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB")

    if not filename.lower().endswith(".pdf"):
        raise RecordUploadError("Only PDF files are allowed")

    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise RecordUploadError("Invalid file type; PDF required")

    if not content.startswith(PDF_MAGIC):
        raise RecordUploadError("Invalid PDF file")


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def save_pdf(content: bytes) -> str:
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4()}.pdf"
    file_path = upload_dir / filename
    file_path.write_bytes(content)

    return str(file_path.relative_to(PROJECT_ROOT))


async def _upload_to_pinata(
    content: bytes,
    record: MedicalRecord,
) -> tuple[str | None, str | None]:
    if not is_pinata_configured():
        warning = "IPFS upload skipped: Pinata credentials are not configured"
        logger.warning(warning)
        return None, warning

    filename = f"medical-record-{record.id}.pdf"
    metadata = {
        "record_id": record.id,
        "patient_id": record.patient_id,
        "doctor_id": record.doctor_id,
        "record_hash": record.record_hash,
    }

    try:
        cid = await upload_pdf_to_pinata(content, filename, metadata=metadata)
        return cid, None
    except PinataUploadError as exc:
        logger.warning("Pinata upload failed for record %s: %s", record.id, exc.message)
        return None, exc.message


def _register_on_blockchain(
    record: MedicalRecord,
    hospital_id: str,
) -> tuple[str | None, str | None]:
    if not blockchain_service.is_configured():
        warning = "Blockchain registration skipped: credentials are not configured"
        logger.warning(warning)
        return None, warning

    try:
        tx_hash = blockchain_service.register_record(
            record_id=record.id,
            record_hash=record.record_hash,
            ipfs_cid=record.ipfs_cid or "",
            doctor_id=record.doctor_id,
            hospital_id=hospital_id,
        )
        return tx_hash, None
    except BlockchainError as exc:
        logger.warning("Blockchain registration failed for record %s: %s", record.id, exc.message)
        return None, exc.message


async def upload_medical_record(
    db: Session,
    doctor_id: int,
    patient_id: int,
    diagnosis: str,
    file: UploadFile,
) -> RecordUploadResult:
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        raise RecordUploadError("Patient not found")

    content = await file.read()
    validate_pdf(file.filename or "", file.content_type, content)

    record_hash = compute_sha256(content)
    file_path = save_pdf(content)

    record = MedicalRecord(
        patient_id=patient_id,
        doctor_id=doctor_id,
        diagnosis=diagnosis,
        record_hash=record_hash,
        file_path=file_path,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    try:
        rag_service.index_record(record, content)
    except Exception as exc:
        logger.warning("Failed to index record %s in ChromaDB: %s", record.id, exc)

    ipfs_cid, ipfs_warning = await _upload_to_pinata(content, record)
    blockchain_warning: str | None = None

    if ipfs_cid:
        record.ipfs_cid = ipfs_cid
        db.commit()
        db.refresh(record)
        logger.info("Saved IPFS CID %s for medical record %s", ipfs_cid, record.id)

        try:
            rag_service.index_record(record, content)
        except Exception as exc:
            logger.warning("Failed to re-index record %s with IPFS CID: %s", record.id, exc)

        tx_hash, blockchain_warning = _register_on_blockchain(record, patient.hospital_id)
        if tx_hash:
            record.tx_hash = tx_hash
            db.commit()
            db.refresh(record)
            logger.info("Saved blockchain tx hash %s for medical record %s", tx_hash, record.id)

    return RecordUploadResult(
        record=record,
        ipfs_warning=ipfs_warning,
        blockchain_warning=blockchain_warning,
    )


def get_medical_record_by_id(db: Session, record_id: int) -> MedicalRecord | None:
    return db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
