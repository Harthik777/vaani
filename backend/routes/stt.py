import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from models import Language, Mode
from services import config, sarvam
from routes.evidence import read_audio, MAX_AUDIO
from services import store
import hashlib
import mocks

router = APIRouter()

@router.post("/api/stt")
async def stt(audio: UploadFile | None = File(None), lang: Language = Form("hindi"), mode: Mode = Form("business"), demo: bool = Form(False),
              keyterms: str = Form("")):
    """keyterms: optional JSON array of domain words (product names, units, brands) that bias Saaras v4 recognition."""
    if demo:
        return {"transcript": mocks.MOCKS_BY_MODE[mode]["transcript"][lang], "demo": True}
    if audio is None:
        raise HTTPException(422, "Audio is required")
    data, mime = await read_audio(audio)
    if not config.USE_REAL_SARVAM or not config.SARVAM_API_KEY:
        raise HTTPException(503, "Transcription is not configured. Your recording is preserved; type its transcript or choose Use demo.")
    try:
        terms = []
        try:
            parsed = json.loads(keyterms) if keyterms else []
            terms = parsed if isinstance(parsed, list) else []
        except ValueError:
            terms = [t for t in keyterms.split(",")]
        result = await sarvam.transcribe(data, lang, audio.filename, mime, keyterms=terms)
        if not result.get("transcript"):
            raise ValueError("Empty transcript")
        return {**result, "demo": False, "model": config.SARVAM_STT_MODEL, "mode": config.SARVAM_STT_MODE if sarvam.stt_is_v4() else "transcribe"}
    except Exception as exc:
        if isinstance(exc, sarvam.SarvamError):
            raise HTTPException(exc.status, str(exc) + ' Your audio is preserved.') from exc
        raise HTTPException(502, "Transcription failed. Your audio is preserved. Retry or type the transcript.") from exc


SPEAKER_LABEL = "Speaker {n}"


@router.post("/api/stt/meeting")
async def stt_meeting(audio: UploadFile = File(...), lang: Language = Form("hindi"), num_speakers: int = Form(2), keyterms: str = Form(""),
                      captured_at: str = Form("")):
    """Upload a recorded meeting (call recording, WhatsApp voice note). Sarvam's batch API transcribes it with
    speaker diarization; the audio is kept as evidence so every requirement can play its clip."""
    data, mime = await read_audio(audio)
    if not config.USE_REAL_SARVAM or not config.SARVAM_API_KEY:
        raise HTTPException(503, "Meeting transcription needs Sarvam. Add SARVAM_API_KEY to backend/.env, or type the transcript.")
    try:
        parsed = json.loads(keyterms) if keyterms else []
        terms = parsed if isinstance(parsed, list) else []
    except ValueError:
        terms = keyterms.split(",")
    num_speakers = max(1, min(int(num_speakers or 2), 20))
    try:
        result = await sarvam.transcribe_meeting(data, lang, audio.filename, num_speakers, terms)
    except Exception as exc:
        if isinstance(exc, sarvam.SarvamError):
            raise HTTPException(exc.status, str(exc) + ' Your audio is preserved.') from exc
        raise HTTPException(502, "Sarvam could not transcribe the recording. Try a shorter clip, or type the transcript.") from exc
    if not result["entries"]:
        raise HTTPException(502, "Sarvam returned no speech for this recording.")
    # Evidence: the whole recording, hashed, with chunk timestamps so quotes map to clips.
    metadata = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "captured_at": captured_at, "received_at": store.now()}
    ident, key = store.create("evidence", metadata, data, mime)
    ids = []
    for e in result["entries"]:
        if e["speaker_id"] not in ids:
            ids.append(e["speaker_id"])
    label = {sid: SPEAKER_LABEL.format(n=i + 1) for i, sid in enumerate(ids)}
    lines = [{"speaker": label[e["speaker_id"]], "text": e["transcript"], "start": e["start"], "end": e["end"]} for e in result["entries"]]
    return {
        "transcript": "\n".join(f"[{l['speaker']}] {l['text']}" for l in lines),
        "lines": lines, "speakers": [label[s] for s in ids],
        "evidence": {"id": ident, "key": key, **metadata, "transcript": "\n".join(l["text"] for l in lines),
                     "timestamps": {"words": [l["text"] for l in lines], "start_time_seconds": [l["start"] for l in lines],
                                    "end_time_seconds": [l["end"] for l in lines]}},
        "language_code": result.get("language_code"), "model": config.SARVAM_STT_MODEL, "diarization": "sarvam batch",
    }
