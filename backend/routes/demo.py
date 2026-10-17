"""Demo voices: Bulbul reads each line of the two-speaker meeting demo in two distinct voices (Owner, Manager), and each
clip is stored as evidence. The demo then plays back like a real recording: every requirement, and both sides of the
stakeholder conflict, can be heard. The clips are labelled as synthesised; nothing claims they are a real person."""
import base64
import hashlib
import io
import wave
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import mocks
from services import config, sarvam, store

router = APIRouter()

# Two voices per language so the Owner and the Manager are told apart by ear (bulbul:v4-flash speaker ids).
DEMO_VOICES = {
    "hindi": {"Owner": "kabir_hi_conversational", "Manager": "sarika_hi_conversation"},
    "english": {"Owner": "shubh_en_narration", "Manager": "ishita_en_customer"},
    "kannada": {"Owner": "chetan_kn_conversation", "Manager": "chaitra_kn_conversation"},
    "tamil": {"Owner": "vijay_ta_narration", "Manager": "gokul_ta_narration"},
    "telugu": {"Owner": "tarun_te_narration", "Manager": "kavitha_te_conversation"},
    "marathi": {"Owner": "nilesh_mr_conversation", "Manager": "ishita_mr_conversational"},
    "bengali": {"Owner": "arnab_bn_conversation", "Manager": "roopa_bn_conversational"},
}
_ready: dict[str, list] = {}   # per language, for this process: the clips are cached on disk, the evidence rows here


class DemoVoicesIn(BaseModel):
    lang: str = "hindi"


def lines_of(transcript: str):
    for line in transcript.split("\n"):
        line = line.strip()
        if not line.startswith("["):
            continue
        speaker, _, text = line[1:].partition("] ")
        if speaker and text.strip():
            yield speaker, text.strip()


def wav_seconds(data: bytes) -> float:
    try:
        with wave.open(io.BytesIO(data)) as w:
            return round(w.getnframes() / float(w.getframerate() or 1), 2)
    except Exception:
        return 0.0


@router.post("/api/demo/voices")
async def demo_voices(body: DemoVoicesIn):
    lang = body.lang if body.lang in mocks.MEETING["transcript"] else "hindi"
    if not sarvam.enabled():
        raise HTTPException(503, "Sarvam voice is not configured, so the demo stays text-only.")
    if lang in _ready:
        return {"evidence": _ready[lang], "cached": True}
    voices = DEMO_VOICES.get(lang) or DEMO_VOICES["hindi"]
    evidence = []
    try:
        for speaker, text in lines_of(mocks.MEETING["transcript"][lang]):
            clips = await sarvam.synthesize(text, lang, speaker=voices.get(speaker))
            data = b"".join(base64.b64decode(c) for c in clips)
            duration = wav_seconds(data)
            captured_at = store.now()
            metadata = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "captured_at": captured_at, "received_at": captured_at,
                        "synthetic": True, "speaker": speaker}
            ident, key = store.create("evidence", metadata, data, "audio/wav")
            evidence.append({"id": ident, "key": key, "sha256": metadata["sha256"], "captured_at": captured_at, "speaker": speaker, "transcript": text,
                             "duration": duration, "local": False, "synthetic": True, "voice": voices.get(speaker),
                             "timestamps": {"words": [text], "start_time_seconds": [0], "end_time_seconds": [duration]}})
    except sarvam.SarvamError as exc:
        raise HTTPException(exc.status, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, "Sarvam Bulbul could not voice the demo. The demo continues as text.") from exc
    _ready[lang] = evidence
    return {"evidence": evidence, "cached": False}
