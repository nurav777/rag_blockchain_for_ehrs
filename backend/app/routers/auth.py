from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_doctor
from app.models.doctor import Doctor
from app.schemas.auth import DoctorResponse, LoginRequest, TokenResponse
from app.services.auth_service import authenticate_doctor, create_access_token

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    doctor = authenticate_doctor(db, credentials.email, credentials.password)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(doctor.id, doctor.email)
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=DoctorResponse)
def get_me(current_doctor: Doctor = Depends(get_current_doctor)) -> Doctor:
    return current_doctor
