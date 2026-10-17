import re
from pathlib import Path
from html import escape
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import Field
from models import CompileIn, Language
from services import config, store
from services.compiler import document, screens

router = APIRouter()
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

class PublishIn(CompileIn):
    evidence: list[dict] = Field(default_factory=list, max_length=100)
    language: Language = "english"
    app_html: str | None = Field(default=None, max_length=400_000)
    app_generator: str = Field(default="template", max_length=120)

def authorize_publisher(request, authorization):
    if config.PUBLISH_API_KEY:
        import secrets
        if not secrets.compare_digest(authorization, "Bearer " + config.PUBLISH_API_KEY):
            raise HTTPException(401, "Publisher authentication required")
    elif request.client and request.client.host not in ("127.0.0.1", "::1", "testclient"):
        raise HTTPException(403, "Configure PUBLISH_API_KEY before remote publishing")

@router.post("/api/portals")
async def publish(body: PublishIn, request: Request, authorization: str = Header("")):
    authorize_publisher(request, authorization)
    if not body.rules or any(not r.approved_at or not r.approved_by for r in body.rules):
        raise HTTPException(422, "Approve at least one rule before publishing")
    if len({r.id for r in body.rules}) != len(body.rules):
        raise HTTPException(422, "Duplicate rule IDs")
    if any(r.source_quote and r.source_quote not in body.transcript for r in body.rules):
        raise HTTPException(422, "A rule's source quote is not in the transcript")
    evidence = []
    for item in body.evidence:
        row = store.get(item.get("id", ""), "evidence", item.get("key", ""))
        if not row:
            raise HTTPException(422, "Missing or unauthorized recording")
        evidence.append({"id": row["id"], **row["payload"]})
    evidence_ids = {e["id"] for e in evidence}
    if any(r.evidence_id and r.evidence_id not in evidence_ids for r in body.rules):
        raise HTTPException(422, "Rule refers to unavailable evidence")
    compiled_screens = screens(body)
    if body.app_html:
        compiled_screens["appHtml"] = body.app_html
    payload = {"mode": body.mode, "demo": body.demo, "metadata": body.metadata, "language": body.language,
        "rules": [r.model_dump() for r in body.rules], "brd": document(body), **compiled_screens,
        "app_generator": body.app_generator if body.app_html else "template",
        "evidence": evidence, "transcript": body.transcript, "published_at": store.now()}
    ident, key = store.create("portal", payload, public=body.mode == "awareness")
    app_base, api_base, reach = share_base(request)
    url = f"{app_base}?portal={ident}" + (f"#key={key}" if key else "")
    return {"id": ident, "key": key, "url": url, "public": not bool(key), "preview_url": f"{api_base}/p/{ident}" if not key else None, "reach": reach}


_listen_checks: dict = {}


def _listening(host, port) -> bool:
    """True when this process accepts connections on host:port (checked with a real connect, remembered for 30 s)."""
    import socket, time
    now = time.monotonic()
    hit = _listen_checks.get((host, port))
    if hit and now - hit[0] < 30:
        return hit[1]
    try:
        with socket.create_connection((host, int(port)), timeout=0.3):
            ok = True
    except OSError:
        ok = False
    _listen_checks[(host, port)] = (now, ok)
    return ok


def share_base(request):
    """(frontend base, api base, reach). reach: 'public' (PUBLIC_URL), 'configured' (FRONTEND_URL), 'lan' (same Wi-Fi) or 'local'."""
    if config.PUBLIC_URL:
        return config.PUBLIC_URL + "/app/", config.PUBLIC_URL, "public"
    if config.FRONTEND_URL_SET and not re.search(r"//(localhost|127\.0\.0\.1|\[::1\])(:|/|$)", config.FRONTEND_URL):
        return config.FRONTEND_URL.rstrip("/") + "/", config.PUBLIC_API_URL.rstrip("/"), "configured"
    host, port = (request.url.hostname or "localhost"), (request.url.port or (443 if request.url.scheme == "https" else 80))
    if host in ("localhost", "127.0.0.1", "::1"):
        host = config.lan_ip()
    # A phone can only reach this process if it listens beyond loopback (uvicorn --host 0.0.0.0) and has the built frontend to serve.
    if not FRONTEND_DIST.exists() or not _listening(host, port):
        return config.FRONTEND_URL.rstrip("/") + "/", config.PUBLIC_API_URL.rstrip("/"), "local"
    base = f"{request.url.scheme}://{host}:{port}"
    return base + "/app/", base, "lan" if host not in ("127.0.0.1", "localhost") else "local"

def portal(ident, authorization):
    row = store.get(ident, "portal", authorization.removeprefix("Bearer "))
    if not row:
        raise HTTPException(404, "Portal unavailable or access key missing")
    return row["payload"]

@router.get("/api/portals/{ident}")
async def get_portal(ident: str, authorization: str = Header("")):
    return portal(ident, authorization)

@router.get("/api/portals/{ident}/audio/{evidence_id}")
async def portal_audio(ident: str, evidence_id: str, authorization: str = Header("")):
    data = portal(ident, authorization)
    if evidence_id not in {e["id"] for e in data["evidence"]}:
        raise HTTPException(404, "Recording unavailable")
    row = store.get(evidence_id, "evidence", internal=True)
    if not row:
        raise HTTPException(404, "Recording unavailable")
    return Response(row["content"], media_type=row["mime"], headers={"Cache-Control": "private, no-store"})

@router.get("/p/{ident}", response_class=HTMLResponse)
async def preview(ident: str, request: Request):
    data = portal(ident, "")
    title = escape(data["brd"]["project_name"])
    app_base, api_base, _ = share_base(request)
    url = escape(f"{app_base}?portal={ident}", quote=True)
    image = escape(f"{api_base}/p/{ident}/card.png", quote=True)
    return f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{title}</title><meta property="og:title" content="{title}"><meta property="og:description" content="Reviewed advisory and source evidence"><meta property="og:image" content="{image}"><meta property="og:url" content="{url}"></head><body><h1>{title}</h1><p>Reviewed advisory. Issuer authority must be verified independently.</p><a href="{url}">Open interactive advisory</a></body></html>'

@router.get("/p/{ident}/card.svg")
async def card(ident: str):
    data = portal(ident, "")
    title = escape(data["brd"]["project_name"][:65])
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630"><rect width="1200" height="630" fill="#0f172a"/><text x="70" y="140" fill="#67e8f9" font-size="56">Vaani · Public advisory</text><text x="70" y="300" fill="white" font-size="30">{title}</text><text x="70" y="440" fill="white" font-size="26">{len(data["rules"])} reviewed directives · Audio and action portal</text></svg>'
    return Response(svg, media_type="image/svg+xml")

@router.get("/p/{ident}/card.png")
async def card_png(ident: str):
    from io import BytesIO
    from textwrap import wrap
    from PIL import Image, ImageDraw, ImageFont
    from pathlib import Path
    data = portal(ident, "")
    image = Image.new("RGB", (1200, 630), "#0f172a")
    draw = ImageDraw.Draw(image)
    candidates = [Path("C:/Windows/Fonts/nirmala.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")]
    font_path = next((p for p in candidates if p.exists()), None)
    font = lambda size: ImageFont.truetype(str(font_path), size) if font_path else ImageFont.load_default(size=size)
    draw.text((65, 90), "Vaani | Public advisory", fill="#67e8f9", font=font(50))
    draw.multiline_text((65, 230), "\n".join(wrap(data["brd"]["project_name"][:140], 48)), fill="white", font=font(36), spacing=14)
    draw.text((65, 505), f'{len(data["rules"])} reviewed directives | Source and action portal', fill="#d3deed", font=font(28))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return Response(buffer.getvalue(), media_type="image/png")
