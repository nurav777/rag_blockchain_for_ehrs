from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Medical Records API"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = True

    # Wallet authentication. JWTs are session/challenge wrappers only;
    # identity is established by an Ethereum wallet signature.
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    WALLET_CHALLENGE_EXPIRE_SECONDS: int = 300

    # Hyperledger Besu / contract.
    BESU_RPC_URL: str = "http://127.0.0.1:8545"
    CONTRACT_ADDRESS: str = ""
    CONTRACT_ABI_PATH: str = "./blockchain/abi/MedicalRecordRegistry.json"

    # Local development deployer/relayer key. It is infrastructure identity,
    # not the clinician identity. Clinicians authenticate with their own wallet.
    DEPLOYER_PRIVATE_KEY: str = ""

    # RAG / AI.
    CHROMA_PERSIST_DIR: str = "./data/chromadb"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RAG_TOP_K: int = 5
    OLLAMA_TIMEOUT: int = 120

    MAX_UPLOAD_SIZE_MB: int = 10

    # Pinata is a prototype/demo IPFS pinning provider only.
    PINATA_JWT: str = ""
    PINATA_UPLOAD_TIMEOUT: int = 60
    PINATA_GATEWAY_URL: str = "https://gateway.pinata.cloud/ipfs"

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    def resolve_project_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path.resolve()
        return (PROJECT_ROOT / path).resolve()

    @property
    def blockchain_relayer_private_key(self) -> str:
        return self.DEPLOYER_PRIVATE_KEY.strip()


settings = Settings()
