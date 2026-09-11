from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import PROJECT_ROOT, settings


# ============================================================
# SQLALCHEMY BASE
# ============================================================


class Base(DeclarativeBase):
    pass


# ============================================================
# DATABASE PATH
# ============================================================


def _normalize_database_url(
    database_url: str,
) -> str:
    """
    Normalize relative SQLite database paths against PROJECT_ROOT.

    Example:

        sqlite:///./data/medical_records.db

    becomes:

        sqlite:///F:/rag_blockchain_medical_records/data/medical_records.db

    This prevents the database location from changing depending on
    the directory from which Uvicorn is started.
    """

    if not database_url.startswith("sqlite:///"):
        return database_url

    raw_path = database_url.removeprefix(
        "sqlite:///"
    )

    db_path = Path(
        raw_path
    )

    if not db_path.is_absolute():
        db_path = (
            PROJECT_ROOT
            / db_path
        ).resolve()
    else:
        db_path = db_path.resolve()

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return f"sqlite:///{db_path.as_posix()}"


DATABASE_URL = _normalize_database_url(
    settings.DATABASE_URL
)


# ============================================================
# ENGINE
# ============================================================


connect_args = (
    {
        "check_same_thread": False,
    }
    if DATABASE_URL.startswith(
        "sqlite"
    )
    else {}
)


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ============================================================
# DATABASE DEPENDENCY
# ============================================================


def get_db() -> Generator[
    Session,
    None,
    None,
]:
    """
    Provide a SQLAlchemy session for one FastAPI request.

    SQLite is currently used for application identity data such as:

        doctors
        patients

    Medical records themselves are NOT stored here.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# DATABASE INITIALIZATION
# ============================================================


def init_db() -> None:
    """
    Create application identity tables.

    Only models imported here are registered with SQLAlchemy.

    MedicalRecord is intentionally absent because medical records
    are stored through IPFS + blockchain rather than SQLite.
    """

    from app.models import Doctor, Patient  # noqa: F401

    Base.metadata.create_all(
        bind=engine
    )