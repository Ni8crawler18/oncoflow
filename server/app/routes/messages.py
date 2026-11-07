from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Message, Patient
from ..schemas import MessageOut, SendMessage
from ..services import messaging
from ..clients import whatsapp

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


# ---- Meta WhatsApp Cloud API webhook ----

@router.get("/webhook", response_class=PlainTextResponse)
def verify_webhook(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
):
    """Meta webhook verification handshake. Echoes the challenge when the
    verify token matches."""
    if hub_mode == "subscribe" and hub_verify_token == settings.meta_verify_token:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(403, "Verification failed")


@router.post("/webhook")
async def inbound_webhook(request: Request, db: Session = Depends(get_db)):
    """Meta WhatsApp inbound webhook.

    Files each inbound message, captures any symptom into post-care symptoms,
    generates an AI follow-up reply (Sarvam), and sends it back over WhatsApp.
    """
    body = await request.json()
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                if msg.get("type") != "text":
                    continue
                from_phone = msg.get("from", "")
                text = (msg.get("text") or {}).get("body", "")
                if not text:
                    continue
                result = messaging.file_inbound(db, from_phone, text)
                reply = result.get("reply")
                if result.get("patient") and reply:
                    whatsapp.send(result["patient"].phone, reply)
    return {"status": "ok"}
