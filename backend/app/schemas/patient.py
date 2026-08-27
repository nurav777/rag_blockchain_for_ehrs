from pydantic import BaseModel, Field

from app.models.patient import Hospital


class PatientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=150)
    gender: str = Field(min_length=1, max_length=20)
    hospital_id: Hospital


class PatientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    age: int | None = Field(default=None, ge=0, le=150)
    gender: str | None = Field(default=None, min_length=1, max_length=20)
    hospital_id: Hospital | None = None


class PatientResponse(BaseModel):
    id: int
    name: str
    age: int
    gender: str
    hospital_id: Hospital

    model_config = {"from_attributes": True}
