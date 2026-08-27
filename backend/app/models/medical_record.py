from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True, nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True, nullable=False)
    diagnosis: Mapped[str] = mapped_column(String(500), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    ipfs_cid: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True, index=True)
