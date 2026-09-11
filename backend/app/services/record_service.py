from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.services.blockchain_service import (
    BlockchainError,
    blockchain_service,
)
from app.services.patient_service import get_patient_by_id
from app.services.pinata_service import (
    PinataUploadError,
    is_pinata_configured,
    upload_pdf_to_pinata,
)
from app.services.rag_service import rag_service


logger = logging.getLogger(__name__)


PDF_MAGIC = b"%PDF"

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
}


# ============================================================
# EXCEPTIONS
# ============================================================


class RecordUploadError(Exception):
    """
    Raised when a medical-record upload cannot be completed.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
    ) -> None:
        self.message = message
        self.status_code = status_code

        super().__init__(message)


# ============================================================
# RESULT
# ============================================================


@dataclass
class RecordUploadResult:
    """
    Result of a completed medical-record upload.

    No SQLite MedicalRecord object is returned because medical
    records are no longer persisted in the relational database.
    """

    record_hash: str
    ipfs_cid: str
    tx_hash: str
    indexing_warning: str | None = None


# ============================================================
# VALIDATION
# ============================================================


def validate_pdf(
    filename: str,
    content_type: str | None,
    content: bytes,
) -> None:
    """
    Validate that the uploaded content is a PDF and remains within
    the configured upload-size limit.
    """

    max_bytes = (
        settings.MAX_UPLOAD_SIZE_MB
        * 1024
        * 1024
    )

    if not content:
        raise RecordUploadError(
            "Uploaded file is empty"
        )

    if len(content) > max_bytes:
        raise RecordUploadError(
            (
                "File exceeds maximum size of "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB"
            )
        )

    if not filename.lower().endswith(".pdf"):
        raise RecordUploadError(
            "Only PDF files are allowed"
        )

    if (
        content_type
        and content_type not in ALLOWED_CONTENT_TYPES
    ):
        raise RecordUploadError(
            "Invalid file type; PDF required"
        )

    if not content.startswith(PDF_MAGIC):
        raise RecordUploadError(
            "Invalid PDF file"
        )


# ============================================================
# HASHING
# ============================================================


def compute_sha256(
    content: bytes,
) -> str:
    """
    Calculate the SHA-256 digest of the original PDF.

    The resulting 64-character hexadecimal value is the canonical
    identifier for the medical record throughout the system.
    """

    return hashlib.sha256(
        content
    ).hexdigest()


# ============================================================
# IPFS
# ============================================================


async def _upload_to_ipfs(
    content: bytes,
    record_hash: str,
) -> str:
    """
    Upload the medical record to IPFS through Pinata.

    IPFS storage is mandatory in the new architecture.
    """

    if not is_pinata_configured():
        raise RecordUploadError(
            (
                "Medical-record upload requires IPFS, "
                "but Pinata credentials are not configured"
            ),
            status_code=503,
        )

    #
    # Do not put patient name, patient ID, diagnosis, doctor ID,
    # or any other medical information into Pinata metadata.
    #
    # At this stage the hash is the only record identifier.
    #
    filename = f"{record_hash}.pdf"

    try:
        cid = await upload_pdf_to_pinata(
            content=content,
            filename=filename,
        )

    except PinataUploadError as exc:
        logger.error(
            "IPFS upload failed for record %s: %s",
            record_hash,
            exc.message,
        )

        raise RecordUploadError(
            f"IPFS upload failed: {exc.message}",
            status_code=502,
        ) from exc

    if not cid:
        raise RecordUploadError(
            "IPFS upload did not return a CID",
            status_code=502,
        )

    logger.info(
        "Uploaded medical record %s to IPFS as %s",
        record_hash,
        cid,
    )

    return cid


# ============================================================
# BLOCKCHAIN
# ============================================================


def _register_on_blockchain(
    *,
    record_hash: str,
    ipfs_cid: str,
    doctor_id: int,
    hospital_id: str,
) -> str:
    """
    Register the mapping

        SHA-256 record hash -> IPFS CID

    in the MedicalRecordRegistry smart contract.
    """

    if not blockchain_service.is_configured():
        raise RecordUploadError(
            (
                "Medical-record upload requires blockchain "
                "registration, but blockchain credentials "
                "are not configured"
            ),
            status_code=503,
        )

    try:
        tx_hash = blockchain_service.register_record(
            record_hash=record_hash,
            ipfs_cid=ipfs_cid,
            doctor_id=doctor_id,
            hospital_id=hospital_id,
        )

    except BlockchainError as exc:
        logger.error(
            (
                "Blockchain registration failed for "
                "record %s: %s"
            ),
            record_hash,
            exc.message,
        )

        raise RecordUploadError(
            (
                "Blockchain registration failed: "
                f"{exc.message}"
            ),
            status_code=502,
        ) from exc

    if not tx_hash:
        raise RecordUploadError(
            (
                "Blockchain registration completed "
                "without returning a transaction hash"
            ),
            status_code=502,
        )

    logger.info(
        (
            "Registered medical record %s on blockchain "
            "with transaction %s"
        ),
        record_hash,
        tx_hash,
    )

    return tx_hash


# ============================================================
# VECTOR INDEX
# ============================================================


def _index_record(
    *,
    record_hash: str,
    content: bytes,
) -> str | None:
    """
    Index the medical record in ChromaDB.

    ChromaDB is a discovery/indexing layer only.

    It must not become the authoritative medical-record store.
    The RAG service will store:

        embedding
        record_hash
        chunk_index

    It will NOT store plaintext medical text.

    Indexing failure does not invalidate the IPFS + blockchain
    record. It is returned as a warning so indexing can later
    be retried.
    """

    try:
        rag_service.index_record(
            record_hash=record_hash,
            pdf_content=content,
        )

    except Exception as exc:
        warning = (
            "Record was stored successfully, "
            "but vector indexing failed: "
            f"{exc}"
        )

        logger.warning(
            (
                "Failed to index medical record %s "
                "in ChromaDB: %s"
            ),
            record_hash,
            exc,
        )

        return warning

    logger.info(
        "Indexed medical record %s in ChromaDB",
        record_hash,
    )

    return None


# ============================================================
# UPLOAD FLOW
# ============================================================


async def upload_medical_record(
    db: Session,
    doctor_id: int,
    patient_id: int,
    file: UploadFile,
) -> RecordUploadResult:
    """
    Process and register a medical record.

    The relational database is used only to resolve the existing
    patient during this operation.

    The medical record itself is NOT inserted into SQLite.

    The uploaded PDF is NOT written to the backend filesystem.

    Authoritative storage flow:

        PDF bytes
            -> SHA-256
            -> IPFS
            -> blockchain
            -> ChromaDB embeddings

    After this function returns, this service retains no local
    plaintext copy of the uploaded PDF.
    """

    # --------------------------------------------------------
    # 1. Resolve patient
    # --------------------------------------------------------

    patient = get_patient_by_id(
        db,
        patient_id,
    )

    if not patient:
        raise RecordUploadError(
            "Patient not found",
            status_code=404,
        )

    # --------------------------------------------------------
    # 2. Require authoritative storage services
    # --------------------------------------------------------

    if not is_pinata_configured():
        raise RecordUploadError(
            (
                "Medical-record upload requires IPFS, "
                "but Pinata credentials are not configured"
            ),
            status_code=503,
        )

    if not blockchain_service.is_configured():
        raise RecordUploadError(
            (
                "Medical-record upload requires blockchain "
                "registration, but blockchain credentials "
                "are not configured"
            ),
            status_code=503,
        )

    # --------------------------------------------------------
    # 3. Read record into memory
    # --------------------------------------------------------

    try:
        content = await file.read()

    except Exception as exc:
        raise RecordUploadError(
            "Unable to read uploaded file"
        ) from exc

    # --------------------------------------------------------
    # 4. Validate PDF
    # --------------------------------------------------------

    validate_pdf(
        filename=file.filename or "",
        content_type=file.content_type,
        content=content,
    )

    # --------------------------------------------------------
    # 5. Calculate canonical record identity
    # --------------------------------------------------------

    record_hash = compute_sha256(
        content
    )

    logger.info(
        "Calculated record hash %s",
        record_hash,
    )

    # --------------------------------------------------------
    # 6. Upload original record to IPFS
    # --------------------------------------------------------

    ipfs_cid = await _upload_to_ipfs(
        content=content,
        record_hash=record_hash,
    )

    # --------------------------------------------------------
    # 7. Register hash -> CID on blockchain
    # --------------------------------------------------------

    tx_hash = _register_on_blockchain(
        record_hash=record_hash,
        ipfs_cid=ipfs_cid,
        doctor_id=doctor_id,
        hospital_id=patient.hospital_id,
    )

    # --------------------------------------------------------
    # 8. Build semantic index
    # --------------------------------------------------------

    indexing_warning = _index_record(
        record_hash=record_hash,
        content=content,
    )

    # --------------------------------------------------------
    # 9. Return references only
    # --------------------------------------------------------

    return RecordUploadResult(
        record_hash=record_hash,
        ipfs_cid=ipfs_cid,
        tx_hash=tx_hash,
        indexing_warning=indexing_warning,
    )