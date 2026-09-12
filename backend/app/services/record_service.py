from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from fastapi import UploadFile

from app.config import settings
from app.services.blockchain_service import BlockchainError, blockchain_service
from app.services.pinata_service import (
    PinataUploadError,
    is_pinata_configured,
    upload_pdf_to_pinata,
)
from app.services.rag_service import rag_service


logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF"
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


class RecordUploadError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class RecordUploadResult:
    record_hash: str
    ipfs_cid: str
    tx_hash: str
    uploader_wallet: str
    indexing_warning: str | None = None


def validate_pdf(filename: str, content_type: str | None, content: bytes) -> None:
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if not content:
        raise RecordUploadError("Uploaded file is empty")
    if len(content) > max_bytes:
        raise RecordUploadError(
            f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB"
        )
    if not filename.lower().endswith(".pdf"):
        raise RecordUploadError("Only PDF files are allowed")
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise RecordUploadError("Invalid file type; PDF required")
    if not content.startswith(PDF_MAGIC):
        raise RecordUploadError("Invalid PDF file")


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def _upload_to_ipfs(content: bytes, record_hash: str) -> str:
    if not is_pinata_configured():
        raise RecordUploadError(
            "Medical-record upload requires IPFS, but Pinata credentials are not configured",
            status_code=503,
        )

    # Only the cryptographic record hash is used as Pinata metadata/filename.
    filename = f"{record_hash}.pdf"
    try:
        cid = await upload_pdf_to_pinata(content=content, filename=filename)
    except PinataUploadError as exc:
        raise RecordUploadError(
            f"IPFS upload failed: {exc.message}",
            status_code=502,
        ) from exc

    if not cid:
        raise RecordUploadError("IPFS upload did not return a CID", status_code=502)
    return cid


def _register_on_blockchain(
    *,
    record_hash: str,
    ipfs_cid: str,
    uploader_wallet: str,
) -> str:
    if not blockchain_service.can_write():
        raise RecordUploadError(
            "Medical-record upload requires blockchain registration, but the relayer is not configured",
            status_code=503,
        )

    try:
        return blockchain_service.register_record(
            record_hash=record_hash,
            ipfs_cid=ipfs_cid,
            uploader_wallet=uploader_wallet,
        )
    except BlockchainError as exc:
        raise RecordUploadError(
            f"Blockchain registration failed: {exc.message}",
            status_code=502,
        ) from exc


def _index_record(*, record_hash: str, content: bytes) -> str | None:
    try:
        rag_service.index_record(record_hash=record_hash, pdf_content=content)
        return None
    except Exception as exc:
        logger.warning("Failed to index record %s: %s", record_hash, exc)
        return f"Record was stored successfully, but vector indexing failed: {exc}"


async def upload_medical_record(
    *,
    uploader_wallet: str,
    file: UploadFile,
) -> RecordUploadResult:
    """
    Wallet-authenticated upload flow.

    No SQL database, patient ID, patient name, doctor ID, or hospital ID is
    required. The authenticated wallet is the only application identity.
    """
    if not is_pinata_configured():
        raise RecordUploadError(
            "Medical-record upload requires IPFS, but Pinata credentials are not configured",
            status_code=503,
        )
    if not blockchain_service.can_write():
        raise RecordUploadError(
            "Medical-record upload requires blockchain registration, but the relayer is not configured",
            status_code=503,
        )

    try:
        content = await file.read()
    except Exception as exc:
        raise RecordUploadError("Unable to read uploaded file") from exc

    validate_pdf(
        filename=file.filename or "",
        content_type=file.content_type,
        content=content,
    )

    record_hash = compute_sha256(content)
    ipfs_cid = await _upload_to_ipfs(content, record_hash)
    tx_hash = _register_on_blockchain(
        record_hash=record_hash,
        ipfs_cid=ipfs_cid,
        uploader_wallet=uploader_wallet,
    )
    indexing_warning = _index_record(record_hash=record_hash, content=content)

    return RecordUploadResult(
        record_hash=record_hash,
        ipfs_cid=ipfs_cid,
        tx_hash=tx_hash,
        uploader_wallet=uploader_wallet,
        indexing_warning=indexing_warning,
    )
