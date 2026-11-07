from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Message, Patient
from ..schemas import MessageOut, SendMessage
from ..services import messaging
from ..clients import telegram

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("", response_model=list[MessageOut])
def recent_messages(category: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Message).order_by(Message.created_at.desc()).limit(100)
    if category:
        stmt = select(Message).where(Message.category == category) \
            .order_by(Message.created_at.desc()).limit(100)
    return list(db.scalars(stmt))


@router.post("/send", response_model=MessageOut, status_code=201)
def send(payload: SendMessage, db: Session = Depends(get_db)):
    patient = db.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    try:
        return messaging.send_outbound(db, patient, payload.body)
    except messaging.DeliveryError as exc:
        raise HTTPException(409, str(exc))


@router.post("/checkin", response_model=MessageOut, status_code=201)
def checkin(payload: dict, db: Session = Depends(get_db)):
    """Send an AI-generated follow-up check-in to a patient."""
    patient = db.get(Patient, payload.get("patient_id"))
    if not patient:
        raise HTTPException(404, "Patient not found")
    try:
        return messaging.ai_checkin(db, patient)
    except messaging.DeliveryError as exc:
        raise HTTPException(409, str(exc))


# ---- Telegram webhook ----

WELCOME = ("Welcome to OncoFlow. Your Telegram is now linked to your care team. "
           "You can message here anytime to report symptoms or ask questions.")
ASK_ID = ("Welcome to OncoFlow. To link your account, please reply with your "
          "patient ID (for example ONC-1001), which your care team gave you.")
NOT_FOUND = ("Sorry, we couldn't find a patient with that ID. Please check the ID "
             "your care team gave you and try again.")


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
            telegram.send(chat_id, WELCOME if linked else NOT_FOUND)
        else:
            telegram.send(chat_id, ASK_ID)
        return {"ok": True}

    if not patient:
        # Try to interpret the message as a patient ID to link the account.
        linked = messaging.link_patient(db, chat_id, text)
        telegram.send(chat_id, WELCOME if linked else ASK_ID)
        return {"ok": True}

    result = messaging.file_inbound(db, patient, text)
    reply = result.get("reply")
    if reply:
        telegram.send(chat_id, reply)
    return {"ok": True}
