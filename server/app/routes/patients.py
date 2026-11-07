from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Patient, Message, Note, FollowUp, Symptom
from ..schemas import (PatientOut, PatientCreate, MessageOut, NoteOut, NoteCreate,
                       FollowUpOut, SymptomOut)

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(q: str | None = None, risk: str | None = None,
                  db: Session = Depends(get_db)):
    stmt = select(Patient)
    if risk:
        stmt = stmt.where(Patient.risk == risk)
    patients = list(db.scalars(stmt))
    if q:
        ql = q.lower()
        patients = [p for p in patients
                    if ql in p.name.lower() or ql in p.mrn.lower()
                    or ql in p.cancer_type.lower()]
    return patients


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    count = db.scalar(select(Patient).order_by(Patient.id.desc())) is not None
    mrn = payload.mrn or f"ONC-{1000 + (db.query(Patient).count() + 1)}"
    patient = Patient(
        mrn=mrn,
        name=payload.name, phone=payload.phone, age=payload.age, sex=payload.sex,
        cancer_type=payload.cancer_type, stage=payload.stage,
        treatment_line=payload.treatment_line, regimen=payload.regimen,
        status=payload.status, risk=payload.risk,
        diagnosed_on=payload.diagnosed_on or date.today(),
        doctor_id=payload.doctor_id or 1,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    return patient


@router.get("/{patient_id}/messages", response_model=list[MessageOut])
def patient_messages(patient_id: int, db: Session = Depends(get_db)):
    return list(db.scalars(
        select(Message).where(Message.patient_id == patient_id)
        .order_by(Message.created_at)
    ))


@router.get("/{patient_id}/followups", response_model=list[FollowUpOut])
def patient_followups(patient_id: int, db: Session = Depends(get_db)):
    return list(db.scalars(
        select(FollowUp).where(FollowUp.patient_id == patient_id)
        .order_by(FollowUp.scheduled_for)
    ))


@router.get("/{patient_id}/symptoms", response_model=list[SymptomOut])
def patient_symptoms(patient_id: int, db: Session = Depends(get_db)):
    return list(db.scalars(
        select(Symptom).where(Symptom.patient_id == patient_id)
        .order_by(Symptom.reported_at.desc())
    ))


@router.get("/{patient_id}/notes", response_model=list[NoteOut])
def patient_notes(patient_id: int, db: Session = Depends(get_db)):
    return list(db.scalars(
        select(Note).where(Note.patient_id == patient_id)
        .order_by(Note.created_at.desc())
    ))


@router.post("/{patient_id}/notes", response_model=NoteOut, status_code=201)
def add_note(patient_id: int, payload: NoteCreate, db: Session = Depends(get_db)):
    if not db.get(Patient, patient_id):
        raise HTTPException(404, "Patient not found")
    note = Note(patient_id=patient_id, body=payload.body, author=payload.author)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note
