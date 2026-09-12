from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.schemas.auth import (
    TokenResponse,
    WalletChallengeRequest,
    WalletChallengeResponse,
    WalletIdentity,
    WalletVerifyRequest,
)
from app.services.auth_service import (
    WalletAuthError,
    create_access_token,
    create_wallet_challenge,
    verify_wallet_challenge,
)
from app.services.blockchain_service import BlockchainError, blockchain_service
from app.dependencies.auth import get_current_wallet
from fastapi import Depends


router = APIRouter()


@router.post("/challenge", response_model=WalletChallengeResponse)
def wallet_challenge(payload: WalletChallengeRequest) -> WalletChallengeResponse:
    message, challenge_token = create_wallet_challenge(payload.wallet_address)
    return WalletChallengeResponse(
        wallet_address=payload.wallet_address,
        message=message,
        challenge_token=challenge_token,
        expires_in_seconds=settings.WALLET_CHALLENGE_EXPIRE_SECONDS,
    )


@router.post("/verify", response_model=TokenResponse)
def wallet_verify(payload: WalletVerifyRequest) -> TokenResponse:
    try:
        wallet = verify_wallet_challenge(
            wallet_address=payload.wallet_address,
            signature=payload.signature,
            challenge_token=payload.challenge_token,
        )
    except WalletAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        ) from exc

    try:
        authorized = blockchain_service.is_authorized_clinician(wallet)
    except BlockchainError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to verify clinician wallet on blockchain: {exc.message}",
        ) from exc

    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Wallet is not authorized as a clinician",
        )

    return TokenResponse(
        access_token=create_access_token(wallet),
        wallet_address=wallet,
    )


@router.get("/me", response_model=WalletIdentity)
def get_me(
    wallet: WalletIdentity = Depends(get_current_wallet),
) -> WalletIdentity:
    return wallet
