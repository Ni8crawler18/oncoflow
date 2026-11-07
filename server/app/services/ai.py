"""AI-driven patient follow-up and symptom understanding (Sarvam)."""
from __future__ import annotations

import json

from ..clients import sarvam
from ..models import Patient, Message

CARE_SYSTEM = (
    "You are OncoFlow, a warm, concise Telegram care assistant for an oncology "
    "clinic, messaging on behalf of the patient's care team. Keep every reply to "
    "1-2 short, plain-language sentences. Be reassuring, never alarmist, and never "
    "give a diagnosis or change medication. When a patient reports a symptom, "
    "acknowledge it and ask ONE specific follow-up question (onset, severity, "
    "duration, or associated symptoms). If a symptom sounds severe (e.g. chest "
    "pain, trouble breathing, high fever, uncontrolled bleeding), advise them to "
    "seek urgent care. Do not mention that you are an AI."
)


def _patient_context(patient: Patient) -> str:
    return (
        f"Patient: {patient.name}, {patient.age}y {patient.sex}. "
        f"Diagnosis: {patient.cancer_type} ({patient.stage}). "
        f"Regimen: {patient.regimen or 'n/a'} ({patient.treatment_line})."
    )


def _history_messages(patient: Patient, limit: int = 8) -> list[dict]:
    msgs = sorted(patient.messages, key=lambda m: m.id)[-limit:]
    out = []
    for m in msgs:
        role = "user" if m.direction == "inbound" else "assistant"
        out.append({"role": role, "content": m.body})
    return out


def generate_checkin(patient: Patient) -> str:
    """Proactive AI check-in message to open a follow-up conversation."""
    prompt = [
        {"role": "system", "content": CARE_SYSTEM},
        {"role": "user", "content": (
            f"{_patient_context(patient)}\n\n"
            "Write a brief, friendly check-in that greets the patient by "
            "first name and asks how they have been feeling since their last "
            "treatment, inviting them to share any new symptoms."
        )},
    ]
    reply = sarvam.chat(prompt, max_tokens=160)
    if not reply:
        first = patient.name.split()[0]
        reply = (f"Hi {first}, this is your OncoFlow care team. How have you been "
                 "feeling since your last treatment? Let us know about any new "
                 "symptoms or concerns.")
    return reply


def generate_reply(patient: Patient, incoming: str) -> str:
    """Generate a contextual follow-up reply to an inbound patient message."""
    prompt = [{"role": "system", "content": CARE_SYSTEM},
              {"role": "system", "content": _patient_context(patient)}]
    prompt += _history_messages(patient)
    prompt.append({"role": "user", "content": incoming})
    reply = sarvam.chat(prompt, max_tokens=180)
    if not reply:
        reply = ("Thank you for letting us know. Could you tell us when this started "
                 "and how severe it feels on a scale of 1 to 10?")
    return reply


def analyze_symptom(text: str) -> dict | None:
    """Decide whether `text` reports a clinical symptom; extract a summary + severity.

    Returns {"is_symptom": bool, "summary": str, "severity": mild|moderate|severe}
    or None if the model is unavailable (caller falls back to keywords).
    """
    if not sarvam.live:
        return None
    prompt = [
        {"role": "system", "content": (
            "You are a clinical triage assistant. Given a patient's "
            "message, decide if it reports a physical symptom or side effect. "
            "Respond with ONLY compact JSON: "
            '{"is_symptom": true/false, "summary": "<short clinical summary>", '
            '"severity": "mild|moderate|severe"}. '
            "If it is not a symptom, set is_symptom false and severity mild."
        )},
        {"role": "user", "content": text},
    ]
    raw = sarvam.chat(prompt, max_tokens=120, temperature=0.0)
    if not raw:
        return None
    try:
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start:end + 1])
        return {
            "is_symptom": bool(data.get("is_symptom")),
            "summary": str(data.get("summary") or text)[:300],
            "severity": data.get("severity")
            if data.get("severity") in ("mild", "moderate", "severe") else "unknown",
        }
    except Exception:
        return None
