from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.dependencies.auth import (
    get_current_doctor,
)
from app.models.doctor import Doctor
from app.services.blockchain_service import (
    BlockchainError,
    blockchain_service,
)


router = APIRouter()


# ============================================================
# HASH NORMALIZATION
# ============================================================


def _normalize_record_hash(
    record_hash: str,
) -> str:
    """
    Validate and normalize a SHA-256 medical-record hash.
    """

    normalized = (
        record_hash
        .strip()
        .lower()
        .removeprefix("0x")
    )

    if len(normalized) != 64:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "record_hash must be a "
                "64-character SHA-256 hash"
            ),
        )

    try:
        bytes.fromhex(
            normalized
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "record_hash must contain only "
                "hexadecimal characters"
            ),
        ) from exc

    return normalized


# ============================================================
# VERIFY RECORD
# ============================================================


@router.get(
    "/{record_hash}",
)
def verify_record(
    record_hash: str,
    _: Doctor = Depends(
        get_current_doctor
    ),
) -> dict[str, Any]:
    """
    Verify that a medical-record hash is registered on the
    consortium blockchain.

    Source of truth:

        record_hash
            ↓
        MedicalRecordRegistry
            ↓
        IPFS CID

    SQLite is not consulted.
    """

    normalized_hash = (
        _normalize_record_hash(
            record_hash
        )
    )

    if not blockchain_service.is_configured():
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=(
                "Blockchain service is not configured"
            ),
        )

    try:
        record = (
            blockchain_service.get_record(
                normalized_hash
            )
        )

    except BlockchainError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "Record was not found on the "
                f"blockchain: {exc.message}"
            ),
        ) from exc

    returned_hash = str(
        record.get(
            "record_hash",
            "",
        )
    )

    returned_hash = (
        returned_hash
        .strip()
        .lower()
        .removeprefix("0x")
    )

    verified = (
        returned_hash
        == normalized_hash
    )

    if not verified:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Blockchain record hash does "
                "not match the requested hash"
            ),
        )

    return {
        "verified": True,
        "record_hash": (
            normalized_hash
        ),
        "ipfs_cid": (
            record.get(
                "ipfs_cid"
            )
        ),
        "doctor_id": (
            record.get(
                "doctor_id"
            )
        ),
        "hospital_id": (
            record.get(
                "hospital_id"
            )
        ),
        "timestamp": (
            record.get(
                "timestamp"
            )
        ),
    }