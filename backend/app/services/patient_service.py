from sqlalchemy.orm import Session

from app.models.patient import Hospital, Patient
from app.schemas.patient import PatientCreate, PatientUpdate


def create_patient(db: Session, data: PatientCreate) -> Patient:
    patient = Patient(
        name=data.name,
        age=data.age,
        gender=data.gender,
        hospital_id=data.hospital_id.value,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def get_patients(db: Session, hospital_id: Hospital | None = None) -> list[Patient]:
    query = db.query(Patient)
    if hospital_id is not None:
        query = query.filter(Patient.hospital_id == hospital_id.value)
    return query.order_by(Patient.id).all()


def get_patient_by_id(db: Session, patient_id: int) -> Patient | None:
    return db.query(Patient).filter(Patient.id == patient_id).first()


def update_patient(db: Session, patient_id: int, data: PatientUpdate) -> Patient | None:
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        return None

    updates = data.model_dump(exclude_unset=True)
    if "hospital_id" in updates and updates["hospital_id"] is not None:
        updates["hospital_id"] = updates["hospital_id"].value

    for field, value in updates.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return patient


def delete_patient(db: Session, patient_id: int) -> bool:
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        return False

    db.delete(patient)
    db.commit()
    return True
