"""WhatsApp delivery through Twilio's WhatsApp API (sandbox or an approved sender).

Configure in backend/.env:
  TWILIO_ACCOUNT_SID=ACxxxxxxxx
  TWILIO_AUTH_TOKEN=xxxxxxxx
  TWILIO_WHATSAPP_FROM=whatsapp:+14155238886      # the Twilio sandbox number, or your approved sender
Sandbox rule: the recipient must first send the sandbox's "join <word>" message to that number.
Media (the Bulbul summary audio) is attached only when PUBLIC_API_URL is reachable from the internet
(for example an ngrok URL); on localhost the message carries the text and the portal link only.
Without credentials nothing is sent and the UI falls back to the prefilled wa.me link.
"""
import re
import httpx
from services import config

TWILIO_BASE = "https://api.twilio.com/2010-04-01/Accounts"


def enabled() -> bool:
    return bool(config.TWILIO_ACCOUNT_SID and config.TWILIO_AUTH_TOKEN and config.TWILIO_WHATSAPP_FROM)


def normalise(number: str, default_cc: str = "+91") -> str:
    """'98765 43210' -> 'whatsapp:+919876543210'. Accepts 'whatsapp:+91...' and '+91...' as-is."""
    raw = (number or "").strip()
    if raw.startswith("whatsapp:"):
        raw = raw[len("whatsapp:"):]
    digits = re.sub(r"[^\d+]", "", raw)
    if not digits.startswith("+"):
        digits = digits.lstrip("0")
        digits = default_cc + digits if len(digits) <= 10 else "+" + digits
    if not re.fullmatch(r"\+\d{8,15}", digits):
        raise ValueError("Enter a WhatsApp number with country code, for example +91 98765 43210")
    return "whatsapp:" + digits


def public_media_allowed() -> bool:
    url = (config.PUBLIC_API_URL or "").lower()
    return url.startswith("https://") and "localhost" not in url and "127.0.0.1" not in url


async def send(to: str, body: str, media_url: str | None = None) -> dict:
    """Send one WhatsApp message. Returns Twilio's message resource (sid, status)."""
    if not enabled():
        raise RuntimeError("Twilio is not configured")
    data = {"From": config.TWILIO_WHATSAPP_FROM, "To": normalise(to), "Body": body[:1500]}
    if media_url and public_media_allowed():
        data["MediaUrl"] = media_url
    async with httpx.AsyncClient(timeout=30, auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)) as client:
        r = await client.post(f"{TWILIO_BASE}/{config.TWILIO_ACCOUNT_SID}/Messages.json", data=data)
        if r.status_code >= 400:
            detail = r.json().get("message", r.text[:200]) if r.headers.get("content-type", "").startswith("application/json") else r.text[:200]
            raise RuntimeError(f"Twilio {r.status_code}: {detail}")
        out = r.json()
        return {"sid": out.get("sid"), "status": out.get("status"), "to": data["To"], "media": bool(data.get("MediaUrl"))}
