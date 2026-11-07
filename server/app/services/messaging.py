"""Patient messaging over Telegram: linking, inbound symptom capture, AI reply."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Patient, Message, Symptom
from ..clients import telegram
from . import ai

SYMPTOM_KEYWORDS = (
    "symptom", "pain", "fever", "nausea", "vomit", "bleed", "breathless",
    "tired", "fatigue", "rash", "swelling", "dizzy", "cough", "sore", "ulcer",
    "diarrhoea", "diarrhea", "numb", "tingling", "appetite", "weak",
)
FEEDBACK_KEYWORDS = ("feedback", "thank", "better", "appointment", "reschedule")


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
    reply = ai.generate_reply(patient, body)
    if reply:
        db.add(Message(patient_id=patient.id, direction="outbound",
                       channel="telegram", body=reply, category="general"))
        db.commit()
    return {"patient": patient, "message": msg, "symptom": symptom, "reply": reply}


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
