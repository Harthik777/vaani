"""Sarvam voice and language routes: Bulbul text-to-speech and Sarvam Translate."""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from models import Language
from services import sarvam

router = APIRouter()

class TtsIn(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    lang: Language = "hindi"
    translate: bool = False  # True: the text is English and should be spoken in `lang`

class TranslateIn(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=80)
    target: Language


def _require_sarvam():
    if not sarvam.enabled():
        raise HTTPException(503, "Sarvam is not configured. Add SARVAM_API_KEY to backend/.env.")


@router.post("/api/tts")
async def tts(body: TtsIn):
    """Speak text with Sarvam Bulbul, optionally translating English -> `lang` first with Sarvam Translate."""
    _require_sarvam()
    try:
        text = await sarvam.translate(body.text, body.lang) if body.translate else body.text
        audios = await sarvam.synthesize(text, body.lang)
        return {"text": text, "audios": audios, "provider": "sarvam", "translated": body.translate and body.lang != "english"}
    except Exception as exc:
        raise HTTPException(502, "Sarvam voice failed. Retry, or read the text on screen.") from exc


@router.post("/api/translate")
async def translate(body: TranslateIn):
    _require_sarvam()
    try:
        results = []
        for start in range(0, len(body.texts), 4):  # at most 4 requests in flight
            batch = body.texts[start:start + 4]
            results += await asyncio.gather(*(sarvam.translate(t, body.target) for t in batch))
        return {"translations": results, "provider": "sarvam"}
    except Exception as exc:
        raise HTTPException(502, "Sarvam Translate failed. Retry in a moment.") from exc
