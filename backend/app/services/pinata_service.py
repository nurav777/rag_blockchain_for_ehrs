from __future__ import annotations

import json
import logging

import httpx

from app.config import settings


logger = logging.getLogger(__name__)


PINATA_PIN_FILE_URL = (
    "https://api.pinata.cloud/pinning/"
    "pinFileToIPFS"
)


# ============================================================
# EXCEPTIONS
# ============================================================


class PinataUploadError(Exception):
    """
    Raised when communication with Pinata/IPFS fails.
    """

    def __init__(
        self,
        message: str,
    ) -> None:
        self.message = message
        super().__init__(message)


# ============================================================
# CONFIGURATION
# ============================================================


def is_pinata_configured() -> bool:
    """
    Return True when a Pinata JWT has been configured.
    """

    return bool(
        settings.PINATA_JWT.strip()
    )


# ============================================================
# AUTH
# ============================================================


def _authorization_headers() -> dict[str, str]:
    """
    Build Pinata bearer authentication headers.
    """

    if not is_pinata_configured():
        raise PinataUploadError(
            "Pinata JWT is not configured"
        )

    return {
        "Authorization": (
            f"Bearer {settings.PINATA_JWT}"
        )
    }


# ============================================================
# UPLOAD
# ============================================================


async def upload_pdf_to_pinata(
    content: bytes,
    filename: str,
    *,
    metadata: dict[
        str,
        str | int,
    ]
    | None = None,
) -> str:
    """
    Upload PDF bytes to Pinata/IPFS.

    The caller controls metadata.

    Medical information such as patient name, diagnosis,
    doctor name, etc. must not be included in Pinata metadata.
    """

    if not content:
        raise PinataUploadError(
            "Cannot upload empty content"
        )

    if not filename.strip():
        raise PinataUploadError(
            "Filename cannot be empty"
        )

    headers = (
        _authorization_headers()
    )

    files = {
        "file": (
            filename,
            content,
            "application/pdf",
        )
    }

    data: dict[str, str] = {}

    if metadata:
        safe_metadata = {
            str(key): str(value)
            for key, value in metadata.items()
        }

        data[
            "pinataMetadata"
        ] = json.dumps(
            {
                "name": filename,
                "keyvalues": (
                    safe_metadata
                ),
            }
        )

    else:
        #
        # Filename is based on the cryptographic record hash,
        # not patient information.
        #
        data[
            "pinataMetadata"
        ] = json.dumps(
            {
                "name": filename,
            }
        )

    try:
        async with httpx.AsyncClient(
            timeout=(
                settings
                .PINATA_UPLOAD_TIMEOUT
            )
        ) as client:
            response = await client.post(
                PINATA_PIN_FILE_URL,
                headers=headers,
                files=files,
                data=data,
            )

    except httpx.TimeoutException as exc:
        raise PinataUploadError(
            "Pinata upload timed out"
        ) from exc

    except httpx.HTTPError as exc:
        raise PinataUploadError(
            f"Pinata request failed: {exc}"
        ) from exc

    if response.status_code != 200:
        raise PinataUploadError(
            (
                "Pinata returned status "
                f"{response.status_code}: "
                f"{response.text}"
            )
        )

    try:
        payload = response.json()

    except ValueError as exc:
        raise PinataUploadError(
            "Pinata returned invalid JSON"
        ) from exc

    cid = payload.get(
        "IpfsHash"
    )

    if not cid:
        raise PinataUploadError(
            (
                "Pinata upload response did "
                "not contain an IPFS CID"
            )
        )

    cid = str(
        cid
    ).strip()

    logger.info(
        "Uploaded %s to IPFS with CID %s",
        filename,
        cid,
    )

    return cid


# ============================================================
# DOWNLOAD
# ============================================================


async def download_from_ipfs(
    cid: str,
) -> bytes:
    """
    Download record bytes from the configured IPFS gateway.
    """

    normalized_cid = cid.strip()

    if not normalized_cid:
        raise PinataUploadError(
            "IPFS CID cannot be empty"
        )

    gateway_base = (
        settings
        .PINATA_GATEWAY_URL
        .rstrip("/")
    )

    gateway_url = (
        f"{gateway_base}/"
        f"{normalized_cid}"
    )

    try:
        async with httpx.AsyncClient(
            timeout=(
                settings
                .PINATA_UPLOAD_TIMEOUT
            ),
            follow_redirects=True,
        ) as client:
            response = await client.get(
                gateway_url
            )

    except httpx.TimeoutException as exc:
        raise PinataUploadError(
            "IPFS download timed out"
        ) from exc

    except httpx.HTTPError as exc:
        raise PinataUploadError(
            f"IPFS download failed: {exc}"
        ) from exc

    if response.status_code != 200:
        raise PinataUploadError(
            (
                "IPFS gateway returned status "
                f"{response.status_code}: "
                f"{response.text}"
            )
        )

    content = response.content

    if not content:
        raise PinataUploadError(
            "IPFS download returned empty content"
        )

    logger.info(
        "Downloaded CID %s from IPFS",
        normalized_cid,
    )

    return content