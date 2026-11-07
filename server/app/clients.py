"""External service clients.

Currently: Twilio WhatsApp. Falls back to a mock when credentials are not
configured, so the demo works offline (outbound messages are logged).
"""
import logging

from .config import settings

logger = logging.getLogger("oncoflow.clients")


class WhatsAppClient:
    def __init__(self) -> None:
        self._client = None
        if settings.twilio_configured:
            try:
                from twilio.rest import Client

                if settings.twilio_api_key_sid and settings.twilio_api_key_secret:
                    # API Key auth: (api_key_sid, api_key_secret, account_sid)
                    self._client = Client(
                        settings.twilio_api_key_sid,
                        settings.twilio_api_key_secret,
                        settings.twilio_account_sid,
                    )
                else:
                    # Account SID + Auth Token
                    self._client = Client(
                        settings.twilio_account_sid, settings.twilio_auth_token
                    )
            except Exception as exc:  # pragma: no cover
                logger.warning("Twilio init failed, using mock mode: %s", exc)

    @property
    def live(self) -> bool:
        return self._client is not None

    def send(self, to_phone: str, body: str) -> dict:
        """Send a WhatsApp message. `to_phone` is E.164 (e.g. +15551234567)."""
        to = to_phone if to_phone.startswith("whatsapp:") else f"whatsapp:{to_phone}"
        if not self._client:
            logger.info("[MOCK WhatsApp] to=%s body=%s", to, body)
            return {"status": "mock", "to": to, "body": body}
        try:
            msg = self._client.messages.create(
                from_=settings.twilio_whatsapp_from, to=to, body=body
            )
            return {"status": msg.status, "sid": msg.sid, "to": to}
        except Exception as exc:
            # Common case: outside the WhatsApp 24h session window (business-initiated
            # messages then require an approved template). Don't crash the request.
            logger.warning("WhatsApp send failed to %s: %s", to, exc)
            return {"status": "failed", "to": to, "error": str(exc)}


whatsapp = WhatsAppClient()


class SarvamClient:
    """Sarvam AI chat completions (OpenAI-compatible)."""

    URL = "https://api.sarvam.ai/v1/chat/completions"

    @property
    def live(self) -> bool:
        return bool(settings.sarvam_api_key)

    def chat(self, messages: list[dict], max_tokens: int = 220,
             temperature: float = 0.4) -> str:
        if not self.live:
            return ""
        import urllib.request
        import json

        payload = json.dumps({
            "model": settings.sarvam_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()
        req = urllib.request.Request(
            self.URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "api-subscription-key": settings.sarvam_api_key,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                data = json.loads(resp.read())
            return (data["choices"][0]["message"].get("content") or "").strip()
        except Exception as exc:  # pragma: no cover
            logger.warning("Sarvam chat failed: %s", exc)
            return ""


sarvam = SarvamClient()
