from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FollowUp, Patient
from ..schemas import FollowUpCreate, FollowUpOut, FollowUpWithPatient
from ..services import scheduling

router = APIRouter(prefix="/api/followups", tags=["followups"])


@router.get("", response_model=list[FollowUpWithPatient])
def list_followups(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(FollowUp).order_by(FollowUp.scheduled_for)
    if status:
        stmt = stmt.where(FollowUp.status == status)
    out = []
    for fu in db.scalars(stmt):
        data = FollowUpOut.model_validate(fu).model_dump()
        data["patient_name"] = fu.patient.name
        data["cancer_type"] = fu.patient.cancer_type
        out.append(FollowUpWithPatient(**data))
    return out


@router.post("/auto-schedule")
def auto_schedule(db: Session = Depends(get_db)):
    """Deterministically schedule the next follow-up for patients who need one."""
    return scheduling.auto_schedule(db)


@router.get("/slots")
def open_slots(day: str = Query(..., description="YYYY-MM-DD"),
               duration_min: int = 30, db: Session = Depends(get_db)):
    d = datetime.fromisoformat(day)
    slots = scheduling.suggest_slots(db, d, duration_min)
    return {"day": day, "slots": [s.isoformat() for s in slots]}


@router.post("", response_model=FollowUpOut, status_code=201)
def create_followup(payload: FollowUpCreate, db: Session = Depends(get_db)):
    if not db.get(Patient, payload.patient_id):
        raise HTTPException(404, "Patient not found")
    if scheduling.has_conflict(db, payload.scheduled_for, payload.duration_min):
        raise HTTPException(
            409,
            detail="Scheduling conflict: that slot overlaps another appointment.",
        )
    fu = FollowUp(**payload.model_dump(), status="scheduled")
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return fu


@router.patch("/{followup_id}/status", response_model=FollowUpOut)
def update_status(followup_id: int, status: str, db: Session = Depends(get_db)):
    fu = db.get(FollowUp, followup_id)
    if not fu:
        raise HTTPException(404, "Follow-up not found")
    if status not in {"scheduled", "completed", "missed", "overdue"}:
        raise HTTPException(400, "Invalid status")
    fu.status = status
    db.commit()
    db.refresh(fu)
    return fu
