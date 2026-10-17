import hashlib
from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import Response
from services import store

router = APIRouter()
MAX_AUDIO = 20 * 1024 * 1024
MIMES = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav"}

async def read_audio(audio):
    mime = (audio.content_type or "").split(";")[0]
    if mime not in MIMES:
        raise HTTPException(415, "Use WebM, Ogg, MP4, MP3 or WAV audio")
    data = await audio.read(MAX_AUDIO + 1)
    if not data or len(data) > MAX_AUDIO:
        raise HTTPException(413, "Audio must be nonempty and at most 20 MB")
    return data, mime

@router.post("/api/evidence")
async def upload(audio: UploadFile = File(...), captured_at: str = Form("")):
    data, mime = await read_audio(audio)
    metadata = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "captured_at": captured_at, "received_at": store.now()}
    ident, key = store.create("evidence", metadata, data, mime)
    return {"id": ident, "key": key, **metadata}

@router.get("/api/evidence/{ident}")
async def audio(ident: str, authorization: str = Header("")):
    row = store.get(ident, "evidence", authorization.removeprefix("Bearer "))
    if not row:
        raise HTTPException(404, "Recording unavailable")
    return Response(row["content"], media_type=row["mime"], headers={"Cache-Control": "private, no-store"})
