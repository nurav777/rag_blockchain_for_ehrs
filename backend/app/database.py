from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    db_path = Path(database_url.removeprefix("sqlite:///"))
    db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(settings.DATABASE_URL)

connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import Doctor, MedicalRecord, Patient  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_medical_record_columns()


def _ensure_medical_record_columns() -> None:
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    columns_to_add = {
        "ipfs_cid": "VARCHAR(100)",
        "tx_hash": "VARCHAR(66)",
    }

    with engine.connect() as connection:
        columns = connection.exec_driver_sql("PRAGMA table_info(medical_records)").fetchall()
        if not columns:
            return

        existing = {column[1] for column in columns}
        for column_name, column_type in columns_to_add.items():
            if column_name in existing:
                continue
            connection.exec_driver_sql(
                f"ALTER TABLE medical_records ADD COLUMN {column_name} {column_type}"
            )
        connection.commit()
