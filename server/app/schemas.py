"""Pydantic schemas (API contracts)."""
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- Auth ----
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    specialty: str = "Medical Oncology"


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(ORM):
    id: int
    name: str
    email: str
    specialty: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# ---- Patients ----
class PatientBase(BaseModel):
    name: str
    phone: str
    age: int
    sex: str
    cancer_type: str
    stage: str
    treatment_line: str = "1st line"
    regimen: str = ""
    status: str = "On treatment"
    risk: str = "medium"


class PatientCreate(PatientBase):
    mrn: str | None = None
    diagnosed_on: date | None = None
    doctor_id: int | None = None


class PatientOut(ORM, PatientBase):
    id: int
    mrn: str
    diagnosed_on: date
    last_contact: date | None
    doctor_id: int


# ---- Follow-ups ----
class FollowUpBase(BaseModel):
    kind: str
    title: str
    scheduled_for: datetime
    duration_min: int = 30
    priority: str = "normal"


class FollowUpCreate(FollowUpBase):
    patient_id: int


class FollowUpOut(ORM, FollowUpBase):
    id: int
    patient_id: int
    status: str


class FollowUpWithPatient(FollowUpOut):
    patient_name: str
    cancer_type: str


# ---- Messages ----
class MessageOut(ORM):
    id: int
    patient_id: int
    direction: str
    channel: str
    body: str
    category: str
    created_at: datetime


class SendMessage(BaseModel):
    patient_id: int
    body: str


# ---- Notes ----
class NoteOut(ORM):
    id: int
    patient_id: int
    author: str
    body: str
    created_at: datetime


class NoteCreate(BaseModel):
    patient_id: int
    body: str
    author: str = "Care team"


# ---- Symptoms (post-care) ----
class SymptomOut(ORM):
    id: int
    patient_id: int
    description: str
    severity: str
    source: str
    status: str
    reported_at: datetime
