import logging
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from models import CompileIn
from services import brd_ai, llm
from services.compiler import document

router = APIRouter()
log = logging.getLogger("vaani.brd")


@router.post("/api/brd")
async def brd(body: CompileIn):
    return document(body)


@router.post("/api/brd/draft")
async def draft(body: CompileIn):
    """AI drafts the full BRD sections; only verified content is returned."""
    if not body.rules:
        raise HTTPException(422, "Approve at least one requirement first")
    if not llm.live():
        raise HTTPException(503, "AI drafting is not configured. The BRD is built from your answers and approved requirements only.")
    last = None
    for attempt in range(2):  # one retry on provider errors or malformed JSON
        try:
            return await brd_ai.draft(body)
        except Exception as exc:
            last = exc
            log.warning("BRD draft attempt %d failed: %s: %s", attempt + 1, type(exc).__name__, exc)
    if last:
        raise HTTPException(502, "AI drafting failed. The BRD still contains your answers and approved requirements; retry to add drafted sections.") from last


@router.post("/api/brd/docx")
async def docx(body: CompileIn):
    try:
        from services.export import build_docx  # optional dependency: only Word export needs python-docx
    except ImportError as exc:
        raise HTTPException(501, "Word export needs python-docx. Run: pip install -r requirements.txt") from exc
    compiled = document(body)
    name = re.sub(r"[^A-Za-z0-9]+", "-", compiled["project_name"]).strip("-")[:60] or "BRD"
    return Response(build_docx(compiled, body.translations), media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f'attachment; filename="{name}.docx"'})
