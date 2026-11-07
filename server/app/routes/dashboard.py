from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Patient, FollowUp, Message, Symptom, Doctor
from .auth import current_doctor

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(doctor: Doctor = Depends(current_doctor), db: Session = Depends(get_db)):
    now = datetime.now()
    today = date.today()

    patients = list(db.scalars(
        select(Patient).where(Patient.doctor_id == doctor.id)))
    pids = {p.id for p in patients}
    total_patients = len(patients)
    high_risk = sum(1 for p in patients if p.risk == "high")

    followups = [f for f in db.scalars(select(FollowUp)) if f.patient_id in pids]
    overdue = sum(
        1 for f in followups
        if f.status == "scheduled" and f.scheduled_for < now
    )
    due_today = sum(
        1 for f in followups
        if f.status == "scheduled" and f.scheduled_for.date() == today
    )
    completed = sum(1 for f in followups if f.status == "completed")
    missed = sum(1 for f in followups if f.status == "missed")

    new_symptoms = sum(
        1 for s in db.scalars(select(Symptom).where(Symptom.status == "open"))
        if s.patient_id in pids
    )

    # Follow-up adherence = completed / (completed + missed)
    denom = completed + missed
    adherence = round(100 * completed / denom) if denom else 100

    return {
        "total_patients": total_patients,
        "high_risk": high_risk,
        "overdue": overdue,
        "due_today": due_today,
        "new_symptoms": new_symptoms,
        "adherence": adherence,
        # Traction metric from the brief — demo figure, not clinically validated.
        "followup_uplift_pct": 35,
    }


@router.get("/activity")
def activity(doctor: Doctor = Depends(current_doctor), db: Session = Depends(get_db)):
    msgs = list(db.scalars(
        select(Message).join(Patient)
        .where(Patient.doctor_id == doctor.id)
        .order_by(Message.created_at.desc()).limit(8)
    ))
    out = []
    for m in msgs:
        out.append({
            "patient_id": m.patient_id,
            "patient_name": m.patient.name,
            "body": m.body,
            "category": m.category,
            "direction": m.direction,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return out


@router.get("/symptoms")
def symptoms(doctor: Doctor = Depends(current_doctor), db: Session = Depends(get_db)):
    rows = list(db.scalars(
        select(Symptom).join(Patient)
        .where(Patient.doctor_id == doctor.id)
        .order_by(Symptom.reported_at.desc()).limit(50)
    ))
    out = []
    for s in rows:
        out.append({
            "id": s.id,
            "patient_id": s.patient_id,
            "patient_name": s.patient.name,
            "cancer_type": s.patient.cancer_type,
            "regimen": s.patient.regimen,
            "description": s.description,
            "severity": s.severity,
            "status": s.status,
            "reported_at": s.reported_at.isoformat() if s.reported_at else None,
        })
    return out


@router.get("/trend")
def trend(doctor: Doctor = Depends(current_doctor), db: Session = Depends(get_db)):
    """Follow-up completions over the last 6 months (for the chart)."""
    followups = list(db.scalars(
        select(FollowUp).join(Patient).where(Patient.doctor_id == doctor.id)))
    buckets: dict[str, int] = {}
    today = date.today()
    labels = []
    for i in range(5, -1, -1):
        month = (today.replace(day=1) - timedelta(days=i * 30)).strftime("%b")
        labels.append(month)
        buckets[month] = 0
    for f in followups:
        if f.status == "completed":
            label = f.scheduled_for.strftime("%b")
            if label in buckets:
                buckets[label] += 1
    return [{"month": m, "completed": buckets[m]} for m in labels]
