import enum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Hospital(str, enum.Enum):
    HOSPITAL_A = "hospital_a"
    HOSPITAL_B = "hospital_b"
    HOSPITAL_C = "hospital_c"


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    hospital_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
