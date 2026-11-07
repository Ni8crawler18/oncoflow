"""External service clients: Meta WhatsApp Cloud API and Sarvam AI.

Both fall back to a mock (log instead of call) when credentials are absent, so
the app always runs.
"""
import logging
import json
import urllib.request
import urllib.error

from .config import settings

logger = logging.getLogger("oncoflow.clients")


class WhatsAppClient:
    """Meta WhatsApp Cloud API (Graph API)."""

    @property
    def live(self) -> bool:
        return bool(settings.meta_phone_number_id and settings.meta_access_token)

    @staticmethod
    def _digits(phone: str) -> str:
        return "".join(ch for ch in phone if ch.isdigit())

    def send(self, to_phone: str, body: str) -> dict:
        """Send a WhatsApp text message. `to_phone` is any E.164 form."""
        to = self._digits(to_phone)
        if not self.live:
            logger.info("[MOCK WhatsApp] to=%s body=%s", to, body)
            return {"status": "mock", "to": to, "body": body}

        url = (f"https://graph.facebook.com/{settings.meta_graph_version}/"
               f"{settings.meta_phone_number_id}/messages")
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {settings.meta_access_token}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            mid = (data.get("messages") or [{}])[0].get("id")
            return {"status": "sent", "id": mid, "to": to}
        except urllib.error.HTTPError as exc:
            err = exc.read().decode(errors="replace")
            logger.warning("WhatsApp send failed to %s: %s", to, err)
            return {"status": "failed", "to": to, "error": err}
        except Exception as exc:  # pragma: no cover
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
