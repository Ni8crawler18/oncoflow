from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import settings
from ..models import Message, Patient, Doctor
from ..schemas import MessageOut, SendMessage
from ..services import messaging
from ..clients import telegram
from .auth import current_doctor

router = APIRouter(prefix="/api/messages", tags=["messages"])


def _owned(db: Session, doctor: Doctor, patient_id) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient or patient.doctor_id != doctor.id:
        raise HTTPException(404, "Patient not found")
    return patient


@router.get("", response_model=list[MessageOut])
def recent_messages(category: str | None = None,
                    doctor: Doctor = Depends(current_doctor),
                    db: Session = Depends(get_db)):
    stmt = (select(Message).join(Patient)
            .where(Patient.doctor_id == doctor.id)
            .order_by(Message.created_at.desc()).limit(100))
    if category:
        stmt = stmt.where(Message.category == category)
    return list(db.scalars(stmt))


@router.post("/send", response_model=MessageOut, status_code=201)
def send(payload: SendMessage, doctor: Doctor = Depends(current_doctor),
         db: Session = Depends(get_db)):
    patient = _owned(db, doctor, payload.patient_id)
    try:
        return messaging.send_outbound(db, patient, payload.body)
    except messaging.DeliveryError as exc:
        raise HTTPException(409, str(exc))


@router.post("/checkin", response_model=MessageOut, status_code=201)
def checkin(payload: dict, doctor: Doctor = Depends(current_doctor),
            db: Session = Depends(get_db)):
    """Send an AI-generated follow-up check-in to a patient."""
    patient = _owned(db, doctor, payload.get("patient_id"))
    try:
        return messaging.ai_checkin(db, patient)
    except messaging.DeliveryError as exc:
        raise HTTPException(409, str(exc))


@router.post("/run-checkins")
def run_checkins(doctor: Doctor = Depends(current_doctor),
                 db: Session = Depends(get_db)):
    """Doctor-triggered: send AI check-ins to this doctor's due patients now."""
    return messaging.run_checkins(db, doctor_id=doctor.id)


@router.post("/run-checkins/cron")
def run_checkins_cron(x_cron_key: str = Header(default=""),
                      db: Session = Depends(get_db)):
    """Autonomous daily run across all doctors. Guarded by a shared secret so a
    scheduler (e.g. Render Cron) can call it without a user session."""
    if not settings.cron_secret or x_cron_key != settings.cron_secret:
        raise HTTPException(403, "Invalid cron key")
    return messaging.run_checkins(db)


# ---- Telegram webhook ----

WELCOME = ("Welcome to OncoFlow. Your Telegram is now linked to your care team. "
           "You can message here anytime to report symptoms or ask questions.")
ASK_ID = ("Welcome to OncoFlow. To link your account, please reply with your "
          "patient ID (for example ONC-1001), which your care team gave you.")
NOT_FOUND = ("Sorry, we couldn't find a patient with that ID. Please check the ID "
             "your care team gave you and try again.")


def _welcome_and_checkin(db, chat_id, patient):
    """On first link, greet the patient and have the care team open the
    conversation with a personalized AI check-in (clinic speaks first)."""
    telegram.send(chat_id, WELCOME)
    try:
        messaging.ai_checkin(db, patient)
    except messaging.DeliveryError:
        pass


@router.post("/telegram")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Telegram inbound webhook. Links new chats by patient ID, then runs the
    AI symptom-capture + follow-up loop for linked patients."""
    update = await request.json()
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return {"ok": True}
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = (msg.get("text") or "").strip()
    if not chat_id or not text:
        return {"ok": True}

    patient = messaging.patient_by_chat(db, chat_id)

    # /start [<MRN>] linking flow
    if text.startswith("/start"):
        payload = text[len("/start"):].strip()
        if patient:
            telegram.send(chat_id, WELCOME)
        elif payload:
            linked = messaging.link_patient(db, chat_id, payload)
            if linked:
                _welcome_and_checkin(db, chat_id, linked)
            else:
                telegram.send(chat_id, NOT_FOUND)
        else:
            telegram.send(chat_id, ASK_ID)
        return {"ok": True}

    if not patient:
        # Try to interpret the message as a patient ID to link the account.
        linked = messaging.link_patient(db, chat_id, text)
        if linked:
            _welcome_and_checkin(db, chat_id, linked)
        else:
            telegram.send(chat_id, ASK_ID)
        return {"ok": True}

    result = messaging.file_inbound(db, patient, text)
    reply = result.get("reply")
    if reply:
        telegram.send(chat_id, reply)
    return {"ok": True}
