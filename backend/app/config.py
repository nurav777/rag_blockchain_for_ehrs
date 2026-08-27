from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (parent of app/)
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Medical Records API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'medical_records.db'}"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Blockchain
    BESU_RPC_URL: str = "http://127.0.0.1:8545"
    CONTRACT_ADDRESS: str = ""
    CONTRACT_ABI_PATH: str = str(PROJECT_ROOT / "blockchain" / "abi" / "MedicalRecordRegistry.json")
    DEPLOYER_PRIVATE_KEY: str = ""

    # RAG / AI
    CHROMA_PERSIST_DIR: str = str(PROJECT_ROOT / "data" / "chromadb")
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # File storage
    UPLOAD_DIR: str = str(PROJECT_ROOT / "data" / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 10

    # Pinata IPFS
    PINATA_API_KEY: str = ""
    PINATA_SECRET_API_KEY: str = ""
    PINATA_UPLOAD_TIMEOUT: int = 60
    PINATA_GATEWAY_URL: str = "https://gateway.pinata.cloud/ipfs"

    # RAG retrieval
    RAG_TOP_K: int = 5
    OLLAMA_TIMEOUT: int = 120

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
