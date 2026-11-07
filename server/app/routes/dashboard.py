from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Patient, FollowUp, Message, Symptom

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    now = datetime.now()
    today = date.today()

    total_patients = db.scalar(select(func.count()).select_from(Patient)) or 0
    high_risk = db.scalar(
        select(func.count()).select_from(Patient).where(Patient.risk == "high")
    ) or 0

    followups = list(db.scalars(select(FollowUp)))
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

    new_symptoms = db.scalar(
        select(func.count()).select_from(Symptom).where(Symptom.status == "open")
    ) or 0

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
def activity(db: Session = Depends(get_db)):
    msgs = list(db.scalars(
        select(Message).order_by(Message.created_at.desc()).limit(8)
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
def symptoms(db: Session = Depends(get_db)):
    rows = list(db.scalars(
        select(Symptom).order_by(Symptom.reported_at.desc()).limit(50)
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
def trend(db: Session = Depends(get_db)):
    """Follow-up completions over the last 6 months (for the chart)."""
    followups = list(db.scalars(select(FollowUp)))
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
