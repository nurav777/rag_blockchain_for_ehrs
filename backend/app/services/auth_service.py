import bcrypt
from datetime import UTC, datetime, timedelta

from jose import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.doctor import Doctor


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(doctor_id: int, email: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(doctor_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def authenticate_doctor(db: Session, email: str, password: str) -> Doctor | None:
    doctor = db.query(Doctor).filter(Doctor.email == email).first()
    if not doctor or not verify_password(password, doctor.hashed_password):
        return None
    return doctor


def get_doctor_by_id(db: Session, doctor_id: int) -> Doctor | None:
    return db.query(Doctor).filter(Doctor.id == doctor_id).first()
