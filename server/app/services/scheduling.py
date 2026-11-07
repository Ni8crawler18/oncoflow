"""Conflict-free follow-up scheduling.

Keeps the doctor's calendar free of overlaps and surfaces the next open slots
so follow-ups make the best use of clinic time.
"""
from datetime import datetime, timedelta, time
from statistics import median
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import FollowUp, Patient, Symptom, Message
from ..clients import telegram

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


def _open_symptoms(db: Session, patient: Patient) -> list[Symptom]:
    return list(db.scalars(
        select(Symptom).where(Symptom.patient_id == patient.id,
                              Symptom.status == "open")
    ))


def _plan_next(db: Session, patient: Patient, now: datetime) -> dict | None:
    """Decide the next appointment for a patient and *why*.

    Returns a plan dict (kind, duration, target date, reason, priority,
    patient_reason) or None if the patient already has an upcoming visit.
    The reason makes auto-scheduling explainable instead of a magic date.
    """
    fus = list(patient.followups)
    if any(f.status == "scheduled" and f.scheduled_for >= now for f in fus):
        return None

    cadence = infer_cadence(fus, patient.regimen)
    completed = [f for f in fus if f.status == "completed"]
    kind = CYCLE_ROTATION[len(completed) % len(CYCLE_ROTATION)]
    priority = "high" if patient.risk == "high" else "normal"

    symptoms = _open_symptoms(db, patient)
    severe = [s for s in symptoms if s.severity in ("severe", "moderate")]

    # Driver 1 — an open symptom brings the review forward.
    if severe:
        kind = "review"
        priority = "high"
        target = now + timedelta(days=1)
        top = severe[0]
        reason = (f"Open {top.severity} symptom reported "
                  f"({top.description[:60]}) — review brought forward.")
        patient_reason = ("we'd like to check in on the symptoms you reported")
    else:
        last = max((f.scheduled_for for f in fus), default=None)
        if last is None:
            # Driver 2 — brand-new patient, first follow-up after diagnosis.
            target = now + timedelta(days=min(cadence, 14))
            reason = (f"First follow-up after diagnosis "
                      f"({patient.cancer_type}); no prior visits on record.")
            patient_reason = "this is your first scheduled follow-up with the clinic"
        elif last < now:
            # Driver 3 — patient is overdue; pull them back into care now.
            days_over = (now - last).days
            target = now + timedelta(days=1)
            reason = (f"Overdue: last visit was {days_over} day(s) ago on "
                      f"{last.strftime('%d %b')}; rescheduled to the next open slot.")
            patient_reason = "it's been a while since your last visit"
        else:
            # Driver 4 — routine cadence from the patient's own rhythm / regimen.
            target = last + timedelta(days=cadence)
            reason = (f"Routine {kind}: {cadence}-day cadence "
                      f"({patient.regimen or 'standard'}) after "
                      f"{last.strftime('%d %b')}.")
            patient_reason = "this is your routine follow-up"

    duration = 60 if kind == "chemo" else 30
    target = datetime.combine(target.date(), CLINIC_START)
    slot = next_slot_on_or_after(db, target, duration)
    return {"kind": kind, "duration": duration, "slot": slot, "reason": reason,
            "priority": priority, "patient_reason": patient_reason}


def _notify_patient(db: Session, patient: Patient, fu: FollowUp,
                    patient_reason: str) -> bool:
    """Tell the patient over Telegram that a visit was booked. Records the
    outbound message so it shows in their thread. Returns True if sent."""
    when = fu.scheduled_for.strftime("%A, %d %b at %I:%M %p").replace(" 0", " ")
    first = patient.name.split()[0]
    text = (f"Hi {first}, this is your OncoFlow care team. We've scheduled your "
            f"next {fu.kind} for {when} at the clinic — {patient_reason}. "
            "Reply here if that time doesn't work and we'll find another slot.")
    db.add(Message(patient_id=patient.id, direction="outbound",
                   channel="telegram", body=text, category="general"))
    if not patient.telegram_chat_id:
        return False
    result = telegram.send(patient.telegram_chat_id, text)
    return result.get("status") in ("sent", "mock")


def auto_schedule(db: Session, doctor_id: int | None = None) -> dict:
    """Book the next follow-up for every patient who lacks an upcoming one, each
    with an explicit clinical reason, and notify the patient over Telegram.

    Scoped to `doctor_id` when given, so each doctor only schedules their own
    panel. Returns a per-patient summary so the doctor can see *what* was booked,
    *why*, and *whether the patient was told* — a reviewable flow, not a silent
    batch.
    """
    now = datetime.now()
    items: list[dict] = []
    skipped = 0
    stmt = select(Patient)
    if doctor_id is not None:
        stmt = stmt.where(Patient.doctor_id == doctor_id)
    for patient in db.scalars(stmt):
        plan = _plan_next(db, patient, now)
        if plan is None:
            skipped += 1
            continue

        fu = FollowUp(
            patient_id=patient.id,
            kind=plan["kind"],
            title=f"{plan['kind'].title()} (auto-scheduled)",
            scheduled_for=plan["slot"],
            duration_min=plan["duration"],
            status="scheduled",
            priority=plan["priority"],
            reason=plan["reason"],
        )
        db.add(fu)
        db.flush()  # assign fu.id before notifying
        notified = _notify_patient(db, patient, fu, plan["patient_reason"])
        items.append({
            "patient_id": patient.id,
            "patient_name": patient.name,
            "kind": fu.kind,
            "scheduled_for": fu.scheduled_for.isoformat(),
            "reason": fu.reason,
            "priority": fu.priority,
            "notified": notified,
            "linked": bool(patient.telegram_chat_id),
        })
    db.commit()
    return {
        "created": len(items),
        "already_scheduled": skipped,
        "notified": sum(1 for i in items if i["notified"]),
        "items": items,
    }


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
