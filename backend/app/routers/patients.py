from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_doctor
from app.models.doctor import Doctor
from app.models.patient import Hospital
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from app.services import patient_service

router = APIRouter()


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    _: Doctor = Depends(get_current_doctor),
) -> PatientResponse:
    return patient_service.create_patient(db, payload)


@router.get("", response_model=list[PatientResponse])
def list_patients(
    hospital_id: Hospital | None = Query(default=None),
    db: Session = Depends(get_db),
    _: Doctor = Depends(get_current_doctor),
) -> list[PatientResponse]:
    return patient_service.get_patients(db, hospital_id)


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: Doctor = Depends(get_current_doctor),
) -> PatientResponse:
    patient = patient_service.get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    _: Doctor = Depends(get_current_doctor),
) -> PatientResponse:
    patient = patient_service.update_patient(db, patient_id, payload)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: Doctor = Depends(get_current_doctor),
) -> None:
    deleted = patient_service.delete_patient(db, patient_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
