from pydantic import BaseModel, Field, field_validator
from web3 import Web3


class WalletChallengeRequest(BaseModel):
    wallet_address: str

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet_address(cls, value: str) -> str:
        try:
            return Web3.to_checksum_address(value.strip())
        except Exception as exc:
            raise ValueError("Invalid Ethereum wallet address") from exc


class WalletChallengeResponse(BaseModel):
    wallet_address: str
    message: str
    challenge_token: str
    expires_in_seconds: int


class WalletVerifyRequest(BaseModel):
    wallet_address: str
    signature: str = Field(min_length=2)
    challenge_token: str = Field(min_length=2)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet_address(cls, value: str) -> str:
        try:
            return Web3.to_checksum_address(value.strip())
        except Exception as exc:
            raise ValueError("Invalid Ethereum wallet address") from exc


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    wallet_address: str


class WalletIdentity(BaseModel):
    wallet_address: str
