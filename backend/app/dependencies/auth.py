from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import WalletIdentity
from app.services.auth_service import WalletAuthError, decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_wallet(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> WalletIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wallet access token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        wallet_address = decode_access_token(credentials.credentials)
    except WalletAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return WalletIdentity(wallet_address=wallet_address)
