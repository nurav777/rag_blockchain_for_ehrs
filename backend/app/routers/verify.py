from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_wallet
from app.schemas.auth import WalletIdentity
from app.services.blockchain_service import BlockchainError, blockchain_service


router = APIRouter()


def _normalize_record_hash(record_hash: str) -> str:
    normalized = record_hash.strip().lower().removeprefix("0x")
    if len(normalized) != 64:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="record_hash must be a 64-character SHA-256 hash",
        )
    try:
        bytes.fromhex(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="record_hash must contain only hexadecimal characters",
        ) from exc
    return normalized


@router.get("/{record_hash}")
def verify_record(
    record_hash: str,
    _: WalletIdentity = Depends(get_current_wallet),
) -> dict[str, Any]:
    normalized_hash = _normalize_record_hash(record_hash)

    if not blockchain_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blockchain service is not configured",
        )

    try:
        record = blockchain_service.get_record(normalized_hash)
    except BlockchainError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record was not found on the blockchain: {exc.message}",
        ) from exc

    returned_hash = str(record.get("record_hash", "")).strip().lower().removeprefix("0x")
    if returned_hash != normalized_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Blockchain record hash does not match the requested hash",
        )

    return {
        "verified": True,
        "record_hash": normalized_hash,
        "ipfs_cid": record.get("ipfs_cid"),
        "uploader_wallet": record.get("uploader_wallet"),
        "timestamp": record.get("timestamp"),
    }
