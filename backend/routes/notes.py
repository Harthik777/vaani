"""Notes as input: a photo or PDF of handwritten/printed notes becomes transcript lines (Sarvam Doc AI)."""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from models import Language
from services import config, sarvam

router = APIRouter()
MAX_BYTES = 15 * 1024 * 1024
MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "application/pdf"}


@router.post("/api/notes")
async def notes(file: UploadFile = File(...), lang: Language = Form("hindi")):
    mime = (file.content_type or "").split(";")[0]
    if mime not in MIMES:
        raise HTTPException(415, "Use a PNG, JPEG or PDF of the notes")
    data = await file.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise HTTPException(413, "The file must be nonempty and at most 15 MB")
    if not config.USE_REAL_SARVAM or not config.SARVAM_API_KEY:
        raise HTTPException(503, "Reading notes needs Sarvam Doc AI. Add SARVAM_API_KEY to backend/.env, or type the notes.")
    try:
        result = await sarvam.digitise_notes(data, file.filename, mime, lang)
    except Exception as exc:
        raise HTTPException(502, "Sarvam Doc AI could not read this file. Try a clearer photo, or type the notes.") from exc
    if not result["lines"]:
        raise HTTPException(502, "Sarvam Doc AI found no text in this file.")
    return {**result, "transcript": "\n".join(f"[Notes] {ln}" for ln in result["lines"]), "provider": "sarvam doc-ai"}
