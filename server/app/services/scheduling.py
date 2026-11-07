"""Conflict-free follow-up scheduling.

Keeps the doctor's calendar free of overlaps and surfaces the next open slots
so follow-ups make the best use of clinic time.
"""
from datetime import datetime, timedelta, time
from statistics import median
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import FollowUp, Patient

CLINIC_START = time(9, 0)
CLINIC_END = time(17, 0)
SLOT_MIN = 30

# Fallback cadence (days) inferred from regimen when a patient has too little
# history to measure their own interval.
REGIMEN_CADENCE = [
    (("folfox", "folfirinox", "folfiri", "flot"), 14),
    (("temozolomide", "stupp"), 28),
    (("r-chop", "chop", "abvd", "ac-t", "carboplatin", "paclitaxel",
      "pemetrexed", "docetaxel", "pembrolizumab", "adt"), 21),
]
DEFAULT_CADENCE = 21

# Rotation of appointment types for an ongoing treatment course.
CYCLE_ROTATION = ["labs", "chemo", "review"]


def _overlaps(a_start: datetime, a_dur: int, b_start: datetime, b_dur: int) -> bool:
    a_end = a_start + timedelta(minutes=a_dur)
    b_end = b_start + timedelta(minutes=b_dur)
    return a_start < b_end and b_start < a_end


def has_conflict(db: Session, scheduled_for: datetime, duration_min: int,
                 exclude_id: int | None = None) -> bool:
    day = scheduled_for.date()
    start = datetime.combine(day, time(0, 0))
    end = start + timedelta(days=1)
    stmt = select(FollowUp).where(
        FollowUp.scheduled_for >= start,
        FollowUp.scheduled_for < end,
        FollowUp.status == "scheduled",
    )
    for fu in db.scalars(stmt):
        if exclude_id and fu.id == exclude_id:
            continue
        if _overlaps(scheduled_for, duration_min, fu.scheduled_for, fu.duration_min):
            return True
    return False


def infer_cadence(followups: list[FollowUp], regimen: str) -> int:
    """Deterministically infer a patient's follow-up interval (days).

    Primary signal: the median gap between the patient's own past appointments.
    Fallback: a regimen-based cadence. This makes auto-scheduling track each
    patient's actual rhythm rather than a fixed rule.
    """
    dates = sorted(f.scheduled_for for f in followups)
    if len(dates) >= 2:
        gaps = [(b - a).days for a, b in zip(dates, dates[1:]) if (b - a).days > 0]
        if gaps:
            return max(7, int(round(median(gaps))))
    reg = (regimen or "").lower()
    for keywords, days in REGIMEN_CADENCE:
        if any(k in reg for k in keywords):
            return days
    return DEFAULT_CADENCE


def next_slot_on_or_after(db: Session, start: datetime, duration_min: int) -> datetime:
    """First conflict-free clinic slot on/after `start` (skips weekends)."""
    day = start
    for _ in range(0, 30):  # look up to 30 days ahead
        if day.weekday() < 5:  # Mon-Fri
            slots = suggest_slots(db, day, duration_min, limit=1)
            if slots:
                return slots[0]
        day = day + timedelta(days=1)
    # Fallback: clinic open next day
    return datetime.combine((start + timedelta(days=1)).date(), CLINIC_START)


def auto_schedule(db: Session) -> dict:
    """Create the next follow-up for every patient who lacks an upcoming one.

    Deterministic: the appointment date is derived from the patient's last
    appointment plus their inferred cadence, placed in the next free clinic
    slot. Appointment type rotates labs -> chemo -> review.
    """
    now = datetime.now()
    created, skipped = 0, 0
    for patient in db.scalars(select(Patient)):
        fus = list(patient.followups)
        has_upcoming = any(
            f.status == "scheduled" and f.scheduled_for >= now for f in fus
        )
        if has_upcoming:
            skipped += 1
            continue

        cadence = infer_cadence(fus, patient.regimen)
        last = max((f.scheduled_for for f in fus), default=now)
        target = last + timedelta(days=cadence)
        if target < now:
            target = now + timedelta(days=1)
        target = datetime.combine(target.date(), CLINIC_START)

        duration = 60
        completed = [f for f in fus if f.status == "completed"]
        kind = CYCLE_ROTATION[len(completed) % len(CYCLE_ROTATION)]
        duration = 60 if kind == "chemo" else 30

        slot = next_slot_on_or_after(db, target, duration)
        db.add(FollowUp(
            patient_id=patient.id,
            kind=kind,
            title=f"{kind.title()} (auto-scheduled)",
            scheduled_for=slot,
            duration_min=duration,
            status="scheduled",
            priority="high" if patient.risk == "high" else "normal",
        ))
        created += 1
    db.commit()
    return {"created": created, "already_scheduled": skipped}


def suggest_slots(db: Session, day: datetime, duration_min: int = SLOT_MIN,
                  limit: int = 6) -> list[datetime]:
    """Return up to `limit` open slots on `day` within clinic hours."""
    base = day.date()
    cursor = datetime.combine(base, CLINIC_START)
    day_end = datetime.combine(base, CLINIC_END)
    slots: list[datetime] = []
    while cursor + timedelta(minutes=duration_min) <= day_end and len(slots) < limit:
        if not has_conflict(db, cursor, duration_min):
            slots.append(cursor)
        cursor += timedelta(minutes=SLOT_MIN)
    return slots
