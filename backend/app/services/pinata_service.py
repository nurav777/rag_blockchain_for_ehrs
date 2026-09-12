from __future__ import annotations

import asyncio
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
    *,
    max_attempts: int = 5,
    initial_backoff_seconds: float = 2.0,
) -> bytes:
    """
    Download record bytes from the configured IPFS gateway.

    Gateway lookup failures are often transient even when a CID is still
    pinned.

    Retry transient HTTP/network failures with exponential backoff so
    callers such as the RAG reindexer can recover without re-uploading data.
    """

    normalized_cid = cid.strip()

    if not normalized_cid:
        raise PinataUploadError(
            "IPFS CID cannot be empty"
        )

    if max_attempts <= 0:
        raise PinataUploadError(
            "max_attempts must be greater than zero"
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

    transient_statuses = {
        408,
        425,
        429,
        500,
        502,
        503,
        504,
    }

    last_error: str | None = None

    async with httpx.AsyncClient(
        timeout=(
            settings
            .PINATA_UPLOAD_TIMEOUT
        ),
        follow_redirects=True,
    ) as client:

        for attempt in range(
            1,
            max_attempts + 1,
        ):
            try:
                response = await client.get(
                    gateway_url
                )

            except httpx.TimeoutException:
                last_error = (
                    "IPFS download timed out"
                )

            except httpx.HTTPError as exc:
                last_error = (
                    f"IPFS download failed: {exc}"
                )

            else:
                if response.status_code == 200:
                    content = response.content

                    if not content:
                        last_error = (
                            "IPFS download returned "
                            "empty content"
                        )

                    else:
                        logger.info(
                            (
                                "Downloaded CID %s "
                                "from IPFS on attempt %s"
                            ),
                            normalized_cid,
                            attempt,
                        )

                        return content

                else:
                    body = response.text[:500]

                    last_error = (
                        "IPFS gateway returned status "
                        f"{response.status_code}: "
                        f"{body}"
                    )

                    #
                    # 404 is deliberately retryable.
                    #
                    # Pinata can return a 404 when its
                    # provider lookup times out even when
                    # the CID remains pinned.
                    #
                    if (
                        response.status_code < 500
                        and response.status_code
                        not in transient_statuses
                        and response.status_code != 404
                    ):
                        raise PinataUploadError(
                            last_error
                        )

            if attempt < max_attempts:
                delay = (
                    initial_backoff_seconds
                    * (
                        2
                        ** (attempt - 1)
                    )
                )

                logger.warning(
                    (
                        "IPFS retrieval attempt "
                        "%s/%s failed for CID %s: "
                        "%s. Retrying in %.1fs"
                    ),
                    attempt,
                    max_attempts,
                    normalized_cid,
                    last_error,
                    delay,
                )

                await asyncio.sleep(
                    delay
                )

    raise PinataUploadError(
        (
            "IPFS retrieval failed after "
            f"{max_attempts} attempts "
            f"for CID {normalized_cid}: "
            f"{last_error or 'unknown error'}"
        )
    )