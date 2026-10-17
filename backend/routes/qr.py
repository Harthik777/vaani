"""QR codes for the hand-off: the owner or a judge scans the portal link or the WhatsApp message onto a phone."""
import io
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

router = APIRouter()


@router.get("/api/qr.png")
def qr_png(data: str = Query(min_length=1, max_length=1500), size: int = Query(default=6, ge=2, le=12)):
    if not (data.startswith("http://") or data.startswith("https://") or data.startswith("upi://")):
        raise HTTPException(422, "QR data must be a link")
    try:
        import qrcode
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(503, "QR generation needs the qrcode package (pip install qrcode[pil])") from exc
    img = qrcode.make(data, box_size=size, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})
