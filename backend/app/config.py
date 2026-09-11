from __future__ import annotations

from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


# ============================================================
# PROJECT PATHS
# ============================================================


BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

PROJECT_ROOT = (
    BACKEND_DIR
    .parent
)


# ============================================================
# SETTINGS
# ============================================================


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --------------------------------------------------------
    # Application
    # --------------------------------------------------------

    APP_NAME: str = (
        "Medical Records API"
    )

    APP_VERSION: str = "0.1.0"

    DEBUG: bool = True

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    #
    # SQLite stores application identity data only.
    #
    # Medical records themselves are NOT persisted here.
    #

    DATABASE_URL: str = (
        "sqlite:///./data/medical_records.db"
    )

    # --------------------------------------------------------
    # Authentication
    # --------------------------------------------------------

    SECRET_KEY: str = (
        "change-me-in-production"
    )

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --------------------------------------------------------
    # Blockchain / Hyperledger Besu
    # --------------------------------------------------------

    BESU_RPC_URL: str = (
        "http://127.0.0.1:8545"
    )

    CONTRACT_ADDRESS: str = ""

    CONTRACT_ABI_PATH: str = (
        "./blockchain/abi/"
        "MedicalRecordRegistry.json"
    )

    #
    # Local development transaction signer.
    #
    # This is NOT the final patient-controlled identity model.
    # We will replace/extend this during access-control work.
    #

    DEPLOYER_PRIVATE_KEY: str = ""

    # --------------------------------------------------------
    # RAG / AI
    # --------------------------------------------------------

    CHROMA_PERSIST_DIR: str = (
        "./data/chromadb"
    )

    OLLAMA_BASE_URL: str = (
        "http://127.0.0.1:11434"
    )

    OLLAMA_MODEL: str = "llama3"

    EMBEDDING_MODEL: str = (
        "all-MiniLM-L6-v2"
    )

    RAG_TOP_K: int = 5

    OLLAMA_TIMEOUT: int = 120

    # --------------------------------------------------------
    # Upload validation
    # --------------------------------------------------------

    MAX_UPLOAD_SIZE_MB: int = 10

    # --------------------------------------------------------
    # Pinata / IPFS
    # --------------------------------------------------------

    #
    # Current Pinata API authentication uses a bearer JWT.
    #

    PINATA_JWT: str = ""

    PINATA_UPLOAD_TIMEOUT: int = 60

    PINATA_GATEWAY_URL: str = (
        "https://gateway.pinata.cloud/ipfs"
    )

    # --------------------------------------------------------
    # CORS
    # --------------------------------------------------------

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # ========================================================
    # PATH HELPERS
    # ========================================================

    def resolve_project_path(
        self,
        value: str,
    ) -> Path:
        """
        Resolve filesystem paths relative to the project root.

        This prevents paths from changing based on the directory
        from which Uvicorn was launched.
        """

        path = Path(
            value
        )

        if path.is_absolute():
            return path.resolve()

        return (
            PROJECT_ROOT
            / path
        ).resolve()


settings = Settings()