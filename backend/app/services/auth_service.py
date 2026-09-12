from __future__ import annotations

import secrets
import threading
from datetime import UTC, datetime, timedelta

from eth_account import Account
from eth_account.messages import encode_defunct
from jose import JWTError, jwt
from web3 import Web3

from app.config import settings


class WalletAuthError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


_used_challenge_ids: set[str] = set()
_used_challenge_lock = threading.Lock()


def normalize_wallet_address(wallet_address: str) -> str:
    try:
        return Web3.to_checksum_address(wallet_address.strip())
    except Exception as exc:
        raise WalletAuthError("Invalid Ethereum wallet address") from exc


def create_wallet_challenge(wallet_address: str) -> tuple[str, str]:
    wallet = normalize_wallet_address(wallet_address)
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=settings.WALLET_CHALLENGE_EXPIRE_SECONDS)
    challenge_id = secrets.token_hex(16)

    message = (
        "Medical Records Wallet Authentication\n"
        f"Wallet: {wallet}\n"
        f"Challenge: {challenge_id}\n"
        f"Issued At: {now.isoformat()}\n"
        f"Expires At: {expires.isoformat()}"
    )

    payload = {
        "type": "wallet_challenge",
        "sub": wallet,
        "jti": challenge_id,
        "message": message,
        "iat": int(now.timestamp()),
        "exp": expires,
    }

    challenge_token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return message, challenge_token


def verify_wallet_challenge(
    *,
    wallet_address: str,
    signature: str,
    challenge_token: str,
) -> str:
    wallet = normalize_wallet_address(wallet_address)

    try:
        payload = jwt.decode(
            challenge_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise WalletAuthError("Invalid or expired wallet challenge") from exc

    if payload.get("type") != "wallet_challenge":
        raise WalletAuthError("Invalid wallet challenge type")

    token_wallet = normalize_wallet_address(str(payload.get("sub", "")))
    if token_wallet.lower() != wallet.lower():
        raise WalletAuthError("Wallet does not match the challenge")

    challenge_id = str(payload.get("jti", "")).strip()
    message = str(payload.get("message", ""))
    if not challenge_id or not message:
        raise WalletAuthError("Malformed wallet challenge")

    with _used_challenge_lock:
        if challenge_id in _used_challenge_ids:
            raise WalletAuthError("Wallet challenge has already been used")

    try:
        recovered = Account.recover_message(
            encode_defunct(text=message),
            signature=signature,
        )
        recovered = normalize_wallet_address(recovered)
    except Exception as exc:
        raise WalletAuthError("Invalid wallet signature") from exc

    if recovered.lower() != wallet.lower():
        raise WalletAuthError("Wallet signature does not match the requested wallet")

    with _used_challenge_lock:
        _used_challenge_ids.add(challenge_id)

    return wallet


def create_access_token(wallet_address: str) -> str:
    wallet = normalize_wallet_address(wallet_address)
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "type": "wallet_access",
        "sub": wallet,
        "iat": int(now.timestamp()),
        "exp": expires,
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise WalletAuthError("Invalid or expired access token") from exc

    if payload.get("type") != "wallet_access":
        raise WalletAuthError("Invalid access token type")

    return normalize_wallet_address(str(payload.get("sub", "")))
