"""WhatsApp messaging: inbound classification, symptom capture, AI follow-up."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Patient, Message, Symptom
from ..clients import whatsapp
from . import ai

SYMPTOM_KEYWORDS = (
    "symptom", "pain", "fever", "nausea", "vomit", "bleed", "breathless",
    "tired", "fatigue", "rash", "swelling", "dizzy", "cough", "sore", "ulcer",
    "diarrhoea", "diarrhea", "numb", "tingling", "appetite", "weak",
)
FEEDBACK_KEYWORDS = ("feedback", "thank", "better", "appointment", "reschedule")


def classify(body: str) -> str:
    low = body.lower()
    if any(k in low for k in SYMPTOM_KEYWORDS):
        return "symptom"
    if any(k in low for k in FEEDBACK_KEYWORDS):
        return "feedback"
    return "general"


def normalize_phone(raw: str) -> str:
    return raw.replace("whatsapp:", "").strip()


def _digits(raw: str) -> str:
    return "".join(ch for ch in raw if ch.isdigit())


def match_patient(db: Session, from_phone: str) -> Patient | None:
    """Match an inbound sender to a patient by phone digits (provider-agnostic:
    Twilio sends '+<e164>', Meta sends '<e164>' without the plus)."""
    target = _digits(from_phone)
    if not target:
        return None
    for p in db.scalars(select(Patient)):
        pd = _digits(p.phone)
        if pd and (pd == target or pd.endswith(target) or target.endswith(pd)):
            return p
    return None


def _record_symptom(db: Session, patient: Patient, body: str) -> Symptom | None:
    """Use AI (fallback: keywords) to capture a post-care symptom."""
    analysis = ai.analyze_symptom(body)
    if analysis is not None:
        if not analysis["is_symptom"]:
            return None
        sym = Symptom(
            patient_id=patient.id,
            description=analysis["summary"],
            severity=analysis["severity"],
            source="whatsapp",
        )
    else:
        if classify(body) != "symptom":
            return None
        sym = Symptom(patient_id=patient.id, description=body,
                      severity="unknown", source="whatsapp")
    db.add(sym)
    db.commit()
    db.refresh(sym)
    return sym


def file_inbound(db: Session, from_phone: str, body: str) -> dict:
    """Match an inbound WhatsApp message to a patient, file it, capture any
    symptom, and generate an AI follow-up reply.

    Returns {"patient": Patient|None, "message": Message|None,
             "symptom": Symptom|None, "reply": str}
    """
    patient = match_patient(db, from_phone)
    if not patient:
        return {"patient": None, "message": None, "symptom": None, "reply": ""}

    category = classify(body)
    msg = Message(patient_id=patient.id, direction="inbound", channel="whatsapp",
                  body=body, category=category)
    db.add(msg)
    db.commit()
    db.refresh(msg)

    symptom = _record_symptom(db, patient, body)
    if symptom:
        msg.category = "symptom"
        db.commit()

    # AI generates the follow-up question/reply.
    db.refresh(patient)
    reply = ai.generate_reply(patient, body)
    if reply:
        db.add(Message(patient_id=patient.id, direction="outbound",
                       channel="whatsapp", body=reply, category="general"))
        db.commit()
    return {"patient": patient, "message": msg, "symptom": symptom, "reply": reply}


class DeliveryError(Exception):
    """Raised when WhatsApp delivery fails (e.g. outside the 24h window)."""


def _deliver_and_record(db: Session, patient: Patient, body: str) -> Message:
    result = whatsapp.send(patient.phone, body)
    if result.get("status") == "failed":
        err = result.get("error", "")
        # Meta error 131047/131026: outside the 24h customer-service window —
        # business-initiated messages then require an approved message template.
        if "131047" in err or "131026" in err or "24 hours" in err or "re-engag" in err.lower():
            raise DeliveryError(
                "WhatsApp won't deliver this: the patient hasn't messaged in the "
                "last 24 hours, so a business-initiated message needs an approved "
                "template. Ask the patient to send a message first, then reply."
            )
        raise DeliveryError(f"WhatsApp delivery failed: {err}")
    msg = Message(patient_id=patient.id, direction="outbound", channel="whatsapp",
                  body=body, category="general")
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def send_outbound(db: Session, patient: Patient, body: str) -> Message:
    return _deliver_and_record(db, patient, body)


def ai_checkin(db: Session, patient: Patient) -> Message:
    """Generate and send a proactive AI follow-up check-in."""
    return _deliver_and_record(db, patient, ai.generate_checkin(patient))
