"""Patient messaging over Telegram: linking, inbound symptom capture, AI reply."""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Patient, Message, Symptom, FollowUp
from ..clients import telegram
from . import ai, scheduling

SYMPTOM_KEYWORDS = (
    "symptom", "pain", "fever", "nausea", "vomit", "bleed", "breathless",
    "tired", "fatigue", "rash", "swelling", "dizzy", "cough", "sore", "ulcer",
    "diarrhoea", "diarrhea", "numb", "tingling", "appetite", "weak",
)
FEEDBACK_KEYWORDS = ("feedback", "thank", "better", "appointment", "reschedule")
SCHEDULE_KEYWORDS = (
    "schedule", "appointment", "book", "reschedule", "meet", "visit",
    "come in", "see the doctor", "see doctor", "slot", "follow up", "follow-up",
)
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday",
            "saturday", "sunday")


def wants_schedule(body: str) -> bool:
    low = body.lower()
    return any(k in low for k in SCHEDULE_KEYWORDS)


def _preferred_start(body: str) -> datetime:
    """Infer a target start date from free text (e.g. 'next monday',
    'tomorrow'). Falls back to the next day."""
    low = body.lower()
    now = datetime.now()
    if "today" in low:
        return now
    if "tomorrow" in low:
        return now + timedelta(days=1)
    for i, name in enumerate(WEEKDAYS):
        if name in low:
            ahead = (i - now.weekday()) % 7
            if ahead == 0 or "next" in low:
                ahead = ahead or 7
            return now + timedelta(days=ahead)
    if "next week" in low:
        return now + timedelta(days=7)
    return now + timedelta(days=1)


def book_from_message(db: Session, patient: Patient, body: str) -> FollowUp:
    """Create a conflict-free follow-up for the patient from a chat request."""
    target = scheduling.next_slot_on_or_after(
        db, _preferred_start(body), duration_min=30)
    fu = FollowUp(
        patient_id=patient.id,
        kind="review",
        title="Review (requested via Telegram)",
        scheduled_for=target,
        duration_min=30,
        status="scheduled",
        priority="high" if patient.risk == "high" else "normal",
        reason="Requested by the patient over Telegram.",
    )
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return fu


class DeliveryError(Exception):
    """Raised when a message can't be delivered (e.g. patient not linked)."""


def classify(body: str) -> str:
    low = body.lower()
    if any(k in low for k in SYMPTOM_KEYWORDS):
        return "symptom"
    if any(k in low for k in FEEDBACK_KEYWORDS):
        return "feedback"
    return "general"


def _digits(raw: str) -> str:
    return "".join(ch for ch in raw if ch.isdigit())


def patient_by_chat(db: Session, chat_id: str) -> Patient | None:
    return db.scalar(select(Patient).where(Patient.telegram_chat_id == str(chat_id)))


def link_patient(db: Session, chat_id: str, identifier: str) -> Patient | None:
    """Link a Telegram chat to a patient by MRN or phone digits."""
    ident = identifier.strip()
    patient = db.scalar(select(Patient).where(Patient.mrn == ident))
    if not patient:
        digits = _digits(ident)
        if digits:
            for p in db.scalars(select(Patient)):
                if _digits(p.phone).endswith(digits) or digits.endswith(_digits(p.phone)):
                    patient = p
                    break
    if patient:
        patient.telegram_chat_id = str(chat_id)
        db.commit()
    return patient


def _record_symptom(db: Session, patient: Patient, body: str) -> Symptom | None:
    analysis = ai.analyze_symptom(body)
    if analysis is not None:
        if not analysis["is_symptom"]:
            return None
        sym = Symptom(patient_id=patient.id, description=analysis["summary"],
                      severity=analysis["severity"], source="telegram")
    else:
        if classify(body) != "symptom":
            return None
        sym = Symptom(patient_id=patient.id, description=body,
                      severity="unknown", source="telegram")
    db.add(sym)
    db.commit()
    db.refresh(sym)
    return sym


def file_inbound(db: Session, patient: Patient, body: str) -> dict:
    """File an inbound message from a linked patient, capture symptom, and
    generate an AI follow-up reply (saved as outbound)."""
    category = classify(body)
    msg = Message(patient_id=patient.id, direction="inbound", channel="telegram",
                  body=body, category=category)
    db.add(msg)
    db.commit()
    db.refresh(msg)

    symptom = _record_symptom(db, patient, body)
    if symptom:
        msg.category = "symptom"
        db.commit()

    db.refresh(patient)

    booking = None
    if wants_schedule(body):
        booking = book_from_message(db, patient, body)
        msg.category = "feedback"
        db.commit()
        doctor = patient.doctor.name if patient.doctor else "your care team"
        when = booking.scheduled_for.strftime("%A, %d %b %Y at %I:%M %p").lstrip("0")
        reply = (
            f"On behalf of {doctor}, your appointment is confirmed for "
            f"{when} at the clinic. You'll get a reminder before then. Please "
            "reach out here if anything changes or your symptoms get worse."
        )
    else:
        reply = ai.generate_reply(patient, body)

    if reply:
        db.add(Message(patient_id=patient.id, direction="outbound",
                       channel="telegram", body=reply, category="general"))
        db.commit()
    return {"patient": patient, "message": msg, "symptom": symptom,
            "reply": reply, "booking": booking}


def _deliver_and_record(db: Session, patient: Patient, body: str) -> Message:
    if not patient.telegram_chat_id:
        raise DeliveryError(
            "This patient hasn't linked Telegram yet. Ask them to open the bot "
            "and send their patient ID (MRN) to connect, then you can message them."
        )
    result = telegram.send(patient.telegram_chat_id, body)
    if result.get("status") == "failed":
        raise DeliveryError(f"Telegram delivery failed: {result.get('error')}")
    msg = Message(patient_id=patient.id, direction="outbound", channel="telegram",
                  body=body, category="general")
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def send_outbound(db: Session, patient: Patient, body: str) -> Message:
    return _deliver_and_record(db, patient, body)


def ai_checkin(db: Session, patient: Patient) -> Message:
    return _deliver_and_record(db, patient, ai.generate_checkin(patient))
