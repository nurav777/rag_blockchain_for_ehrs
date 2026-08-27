import json
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

PINATA_PIN_FILE_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"


class PinataUploadError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def is_pinata_configured() -> bool:
    return bool(settings.PINATA_API_KEY and settings.PINATA_SECRET_API_KEY)


async def upload_pdf_to_pinata(
    content: bytes,
    filename: str,
    *,
    metadata: dict[str, str | int] | None = None,
) -> str:
    if not is_pinata_configured():
        raise PinataUploadError("Pinata credentials are not configured")

    headers = {
        "pinata_api_key": settings.PINATA_API_KEY,
        "pinata_secret_api_key": settings.PINATA_SECRET_API_KEY,
    }
    files = {"file": (filename, content, "application/pdf")}
    data: dict[str, str] = {}

    if metadata:
        data["pinataMetadata"] = json.dumps(
            {
                "name": filename,
                "keyvalues": {str(key): str(value) for key, value in metadata.items()},
            }
        )

    try:
        async with httpx.AsyncClient(timeout=settings.PINATA_UPLOAD_TIMEOUT) as client:
            response = await client.post(
                PINATA_PIN_FILE_URL,
                headers=headers,
                files=files,
                data=data or None,
            )
    except httpx.TimeoutException as exc:
        raise PinataUploadError("Pinata upload timed out") from exc
    except httpx.HTTPError as exc:
        raise PinataUploadError(f"Pinata request failed: {exc}") from exc

    if response.status_code != 200:
        raise PinataUploadError(
            f"Pinata returned status {response.status_code}: {response.text}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise PinataUploadError("Pinata returned an invalid response") from exc

    cid = payload.get("IpfsHash")
    if not cid:
        raise PinataUploadError("Pinata response did not include a CID")

    logger.info("Uploaded %s to Pinata with CID %s", filename, cid)
    return cid


async def download_from_ipfs(cid: str) -> bytes:
    gateway_url = f"{settings.PINATA_GATEWAY_URL.rstrip('/')}/{cid}"

    try:
        async with httpx.AsyncClient(timeout=settings.PINATA_UPLOAD_TIMEOUT) as client:
            response = await client.get(gateway_url)
    except httpx.TimeoutException as exc:
        raise PinataUploadError("IPFS download timed out") from exc
    except httpx.HTTPError as exc:
        raise PinataUploadError(f"IPFS download failed: {exc}") from exc

    if response.status_code != 200:
        raise PinataUploadError(
            f"IPFS gateway returned status {response.status_code}: {response.text}"
        )

    content = response.content
    if not content:
        raise PinataUploadError("IPFS download returned empty content")

    logger.info("Downloaded CID %s from IPFS gateway", cid)
    return content
