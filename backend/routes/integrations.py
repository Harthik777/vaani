"""Deadlines (.ics + Google Calendar links), Google Drive/Calendar push through OAuth, and the pack by email."""
import re
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from models import CompileIn
from services import config, deadlines, google_sync
from services.compiler import document
from routes.exports import file_stem

router = APIRouter()


class DeadlinesIn(CompileIn):
    pass


@router.post("/api/brd/deadlines")
async def brd_deadlines(body: DeadlinesIn):
    brd = document(body)
    try:
        found = await deadlines.infer(body.transcript, [a.model_dump() if hasattr(a, "model_dump") else a for a in (body.answers or [])], [r.model_dump() for r in body.rules])
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Deadline detection failed: {exc}") from exc
    project = brd.get("project_name") or "BRD"
    for d in found:
        d["google_link"] = deadlines.google_link(d, project)
    return {"deadlines": found, "project": project, "ics_available": bool(found)}


class IcsIn(BaseModel):
    deadlines: list[dict] = Field(min_length=1, max_length=20)
    project: str = Field(default="BRD", max_length=200)


@router.post("/api/brd/ics")
async def brd_ics(body: IcsIn):
    text = deadlines.ics(body.deadlines, body.project)
    stem = (re.sub(r"[^A-Za-z0-9]+", "-", body.project).strip("-") or "brd")[:60]
    return Response(text, media_type="text/calendar; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{stem}-deadlines.ics"'})


# ── Google OAuth: Drive (Google Doc) + Calendar (events) ──
@router.get("/api/google/status")
async def google_status(email: str = ""):
    return {"configured": google_sync.enabled(), "connected": google_sync.connected(email) if email else False}


@router.get("/api/google/start")
async def google_start(email: str = ""):
    if not google_sync.enabled():
        raise HTTPException(503, "Google is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to backend/.env (free OAuth client).")
    url, _ = google_sync.start_url(email)
    return {"url": url}


@router.get("/api/google/callback", response_class=HTMLResponse)
async def google_callback(code: str = "", state: str = "", error: str = ""):
    if error or not code:
        return HTMLResponse(f"<p>Google sign-in was cancelled ({error or 'no code'}). You can close this tab.</p>", status_code=400)
    try:
        email = await google_sync.finish(code, state)
    except Exception as exc:
        return HTMLResponse(f"<p>Google sign-in failed: {exc}</p>", status_code=400)
    return HTMLResponse("<!doctype html><meta charset='utf-8'><p style='font-family:sans-serif'>Google account <b>" + email +
                        "</b> connected to VAANI. You can close this tab and return to the app.</p><script>try{window.opener&&window.opener.postMessage({vaani_google:'" + email + "'},'*')}catch(e){}</script>")


class PushIn(CompileIn):
    email: str = Field(min_length=3, max_length=200)
    deadlines: list[dict] = Field(default_factory=list, max_length=20)


@router.post("/api/google/push")
async def google_push(body: PushIn):
    if not google_sync.enabled():
        raise HTTPException(503, "Google is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to backend/.env.")
    if not google_sync.connected(body.email):
        raise HTTPException(401, "Connect this Google account first.")
    from services.export import build_docx
    brd = document(body)
    try:
        out = await google_sync.push(body.email, (brd.get("project_name") or "BRD") + " (VAANI BRD)", build_docx(brd, body.translations), body.deadlines, brd.get("project_name") or "BRD")
    except LookupError as exc:
        raise HTTPException(401, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Google push failed: {exc}") from exc
    return out
