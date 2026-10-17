"""Send the BRD hand-off to the owner's WhatsApp: portal link + summary text (+ Bulbul audio when public)."""
import base64
import secrets
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from models import Language
from services import config, sarvam, whatsapp

router = APIRouter()


class SendIn(BaseModel):
    to: str = Field(min_length=6, max_length=40)
    portal_url: str = Field(default="", max_length=600)
    title: str = Field(default="", max_length=200)
    summary: str = Field(default="", max_length=3000)       # English summary of the BRD
    lang: Language = "hindi"                                 # spoken + translated version for the owner
    with_audio: bool = True


def _media_dir() -> Path:
    d = Path(config.DATA_DIR) / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.post("/api/whatsapp/send")
async def send(body: SendIn):
    if not whatsapp.enabled():
        raise HTTPException(503, "WhatsApp sending is not configured. Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_WHATSAPP_FROM to backend/.env, or use the WhatsApp link.")
    try:
        to = whatsapp.normalise(body.to)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    summary_local, media_url, audio_note = body.summary, None, None
    if body.summary and body.lang != "english" and sarvam.enabled():
        try:
            summary_local = await sarvam.translate_colloquial(body.summary, body.lang)  # owner's register, not the vendor's
        except Exception:
            summary_local = body.summary
    if body.with_audio and summary_local and sarvam.enabled():
        if whatsapp.public_media_allowed():
            try:
                clips = await sarvam.synthesize(summary_local, body.lang)
                ident = secrets.token_urlsafe(18)
                (_media_dir() / f"{ident}.wav").write_bytes(base64.b64decode(clips[0]))
                media_url = f"{config.PUBLIC_API_URL.rstrip('/')}/api/media/{ident}.wav"
            except Exception:
                audio_note = "Voice summary could not be prepared; text was sent."
        else:
            audio_note = "Voice note skipped: PUBLIC_API_URL must be a public https URL (for example ngrok) for WhatsApp to fetch audio."
    lines = [f"VAANI · {body.title}".strip(" ·"), "", summary_local.strip()]
    if body.portal_url:
        lines += ["", f"Full BRD and voice clips: {body.portal_url}"]
    text = "\n".join(l for l in lines if l is not None)
    try:
        result = await whatsapp.send(to, text, media_url)
    except Exception as exc:
        raise HTTPException(502, f"WhatsApp send failed: {exc}") from exc
    return {**result, "text": text, "audio_note": audio_note}


@router.get("/api/media/{name}")
async def media(name: str):
    if not name.endswith(".wav") or "/" in name or ".." in name:
        raise HTTPException(404)
    path = _media_dir() / name
    if not path.exists():
        raise HTTPException(404)
    return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "private, max-age=3600"})
