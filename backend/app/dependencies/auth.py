from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.doctor import Doctor
from app.services.auth_service import decode_access_token, get_doctor_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_doctor(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Doctor:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        doctor_id = payload.get("sub")
        if doctor_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    doctor = get_doctor_by_id(db, int(doctor_id))
    if doctor is None:
        raise credentials_exception

    return doctor
