from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FollowUp, Patient, Doctor
from ..schemas import FollowUpCreate, FollowUpOut, FollowUpWithPatient
from ..services import scheduling
from ..security import calendar_token, verify_calendar_token
from .auth import current_doctor

router = APIRouter(prefix="/api/followups", tags=["followups"])


def _ics_escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def _build_ics(doctor: Doctor, followups: list[FollowUp]) -> str:
    """Render the doctor's follow-ups as an iCalendar feed (floating local
    time, so it displays as booked regardless of the viewer's timezone)."""
    now = datetime.now().strftime("%Y%m%dT%H%M%S")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//OncoFlow//Follow-ups//EN", "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:OncoFlow — {_ics_escape(doctor.name)}",
    ]
    for f in followups:
        start = f.scheduled_for
        end = start + timedelta(minutes=f.duration_min or 30)
        patient = f.patient.name if f.patient else "Patient"
        desc_bits = [f"Patient: {patient}"]
        if f.patient:
            desc_bits.append(f"Diagnosis: {f.patient.cancer_type}")
        if f.reason:
            desc_bits.append(f"Reason: {f.reason}")
        desc_bits.append(f"Status: {f.status}")
        lines += [
            "BEGIN:VEVENT",
            f"UID:followup-{f.id}@oncoflow.health",
            f"DTSTAMP:{now}",
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{_ics_escape(f.title)} — {_ics_escape(patient)}",
            f"DESCRIPTION:{_ics_escape(' · '.join(desc_bits))}",
            "LOCATION:Clinic",
            f"STATUS:{'CONFIRMED' if f.status == 'scheduled' else 'TENTATIVE'}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


@router.get("/calendar-url")
def calendar_url(doctor: Doctor = Depends(current_doctor)):
    """The subscribable feed path for this doctor (prefix with the API base)."""
    token = calendar_token(doctor.id)
    return {"path": f"/api/followups/calendar/{token}.ics", "token": token}


@router.get("/calendar/{token}.ics")
def calendar_feed(token: str, db: Session = Depends(get_db)):
    """Public per-doctor iCalendar feed (token-authenticated, read-only)."""
    doctor_id = verify_calendar_token(token)
    if doctor_id is None:
        raise HTTPException(404, "Calendar not found")
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(404, "Calendar not found")
    followups = list(db.scalars(
        select(FollowUp).join(Patient)
        .where(Patient.doctor_id == doctor_id)
        .order_by(FollowUp.scheduled_for)))
    ics = _build_ics(doctor, followups)
    return Response(content=ics, media_type="text/calendar",
                    headers={"Content-Disposition": "inline; filename=oncoflow.ics"})


@router.get("", response_model=list[FollowUpWithPatient])
def list_followups(status: str | None = None,
                   doctor: Doctor = Depends(current_doctor),
                   db: Session = Depends(get_db)):
    stmt = (select(FollowUp).join(Patient)
            .where(Patient.doctor_id == doctor.id)
            .order_by(FollowUp.scheduled_for))
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
def auto_schedule(doctor: Doctor = Depends(current_doctor),
                  db: Session = Depends(get_db)):
    """Schedule the next follow-up for this doctor's patients who need one."""
    return scheduling.auto_schedule(db, doctor_id=doctor.id)


@router.get("/slots")
def open_slots(day: str = Query(..., description="YYYY-MM-DD"),
               duration_min: int = 30,
               doctor: Doctor = Depends(current_doctor),
               db: Session = Depends(get_db)):
    d = datetime.fromisoformat(day)
    slots = scheduling.suggest_slots(db, d, duration_min)
    return {"day": day, "slots": [s.isoformat() for s in slots]}


@router.post("", response_model=FollowUpOut, status_code=201)
def create_followup(payload: FollowUpCreate,
                    doctor: Doctor = Depends(current_doctor),
                    db: Session = Depends(get_db)):
    patient = db.get(Patient, payload.patient_id)
    if not patient or patient.doctor_id != doctor.id:
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
def update_status(followup_id: int, status: str,
                  doctor: Doctor = Depends(current_doctor),
                  db: Session = Depends(get_db)):
    fu = db.get(FollowUp, followup_id)
    if not fu or fu.patient.doctor_id != doctor.id:
        raise HTTPException(404, "Follow-up not found")
    if status not in {"scheduled", "completed", "missed", "overdue"}:
        raise HTTPException(400, "Invalid status")
    fu.status = status
    db.commit()
    db.refresh(fu)
    return fu
