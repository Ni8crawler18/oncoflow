from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Message, Patient
from ..schemas import MessageOut, SendMessage
from ..services import messaging

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


@router.post("/webhook")
def twilio_webhook(
    From: str = Form(""),
    Body: str = Form(""),
    db: Session = Depends(get_db),
):
    """Twilio WhatsApp inbound webhook.

    Files the patient's message, captures any symptom into post-care symptoms,
    and replies (via TwiML) with an AI-generated follow-up question.
    """
    result = messaging.file_inbound(db, From, Body)
    reply = result.get("reply") or ""
    if not result.get("patient"):
        twiml = ("<?xml version='1.0' encoding='UTF-8'?><Response></Response>")
    elif reply:
        twiml = (f"<?xml version='1.0' encoding='UTF-8'?><Response>"
                 f"<Message>{escape(reply)}</Message></Response>")
    else:
        twiml = ("<?xml version='1.0' encoding='UTF-8'?><Response></Response>")
    return Response(content=twiml, media_type="application/xml")
