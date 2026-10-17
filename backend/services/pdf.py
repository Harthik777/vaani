"""BRD -> PDF on the server (fpdf2 with HarfBuzz shaping), so the Download button yields a real file on any device.

Fonts: Indic scripts need a font with those glyphs and proper shaping. On Windows the system "Nirmala UI" collection
covers Devanagari, Kannada, Tamil, Telugu and Bengali; its first face is extracted once to data/fonts. A Noto Sans
family placed in backend/fonts/ (NotoSans*.ttf) is used when present. Without either, Latin text still renders
and Indic text falls back to the quote's transliteration note.
"""
import os
from io import BytesIO
from pathlib import Path
from services import config

INDIC_CANDIDATES = ["C:/Windows/Fonts/Nirmala.ttc", "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"]
_font_path: str | None = None
_checked = False


def indic_font() -> str | None:
    """Path to a TTF that covers Indic scripts, extracted from the system collection when needed."""
    global _font_path, _checked
    if _checked and (_font_path is None or os.path.exists(_font_path)):
        return _font_path
    _checked = True
    bundled = sorted(Path(__file__).resolve().parents[1].joinpath("fonts").glob("*.ttf"))
    if bundled:
        _font_path = str(bundled[0])
        return _font_path
    for cand in INDIC_CANDIDATES:
        if not os.path.exists(cand):
            continue
        if cand.lower().endswith(".ttc"):
            try:
                from fontTools.ttLib import TTCollection
                out = Path(__file__).resolve().parents[1] / "data" / "fonts"  # stable location, independent of DATA_DIR
                out.mkdir(parents=True, exist_ok=True)
                target = out / "NirmalaUI.ttf"
                if not target.exists():
                    TTCollection(cand).fonts[0].save(str(target))
                _font_path = str(target)
            except Exception:
                continue
        else:
            _font_path = cand
        break
    return _font_path


def _pdf():
    from fpdf import FPDF
    pdf = FPDF(format="A4")
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    font = indic_font()
    if font:
        pdf.add_font("body", "", font)
        pdf.set_text_shaping(True)
        pdf._vaani_font = "body"
    else:
        pdf._vaani_font = "Helvetica"
    pdf.add_page()
    return pdf


def _text(pdf, text, size=10.5, bold=False, color=(0x15, 0x20, 0x2B), indent=0):
    """Write a paragraph; falls back to Helvetica (Latin only) if the chosen font lacks a glyph."""
    pdf.set_x(pdf.l_margin + indent)
    pdf.set_text_color(*color)
    font = pdf._vaani_font
    try:
        pdf.set_font(font, "", size)
        pdf.multi_cell(0, size * 0.55, text, new_x="LMARGIN", new_y="NEXT")
    except Exception:
        pdf.set_font("Helvetica", "B" if bold else "", size)
        safe = text.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, size * 0.55, safe, new_x="LMARGIN", new_y="NEXT")
    if bold and font != "Helvetica":
        pass  # single-weight Indic face: bold is conveyed by size and color
    pdf.ln(1)


def _heading(pdf, text, size=13):
    pdf.ln(3)
    _text(pdf, text, size=size, bold=True, color=(0x0F, 0x6E, 0x56))


def build_pdf(brd: dict, translations: dict | None = None) -> bytes:
    pdf = _pdf()
    _text(pdf, brd.get("project_name", "Business Requirements Document"), size=20, bold=True)
    _text(pdf, f"{brd.get('document_type', '')}  ·  {brd.get('status', '')}", size=9.5, color=(0x6E, 0x79, 0x85))
    if brd.get("demo"):
        _text(pdf, "DEMONSTRATION: sample content, not a client's signed requirements.", size=9.5, color=(0xB4, 0x57, 0x0A))
    meta = {k: v for k, v in (brd.get("metadata") or {}).items() if v and k not in ("ticketSummary", "review_notes")}
    for k, v in meta.items():
        _text(pdf, f"{k.replace('_', ' ').title()}: {v}", size=9.5, color=(0x3B, 0x46, 0x54))
    n = 0
    tr = translations or {}
    for key, items in (brd.get("sections") or {}).items():
        n += 1
        _heading(pdf, f"{n}. {(brd.get('section_titles') or {}).get(key, key)}")
        if not items:
            _text(pdf, "Not captured yet.", size=9.5, color=(0x6E, 0x79, 0x85), indent=4)
        for item in items:
            tag = "AI suggestion, confirm" if item.get("origin") == "suggested" else "spoken"
            _text(pdf, f"• {item.get('text', '')}  [{tag}]", indent=4)
            if tr.get(item.get("text")):
                _text(pdf, tr[item["text"]], size=10, color=(0x0F, 0x6E, 0x56), indent=8)
            q = item.get("source_quote")
            if q and q != item.get("text"):
                _text(pdf, f"“{q}”", size=9.5, color=(0x3B, 0x46, 0x54), indent=8)
    n += 1
    _heading(pdf, f"{n}. Functional requirements and traceability")
    for r in brd.get("business_rules") or []:
        _text(pdf, f"{r.get('req_id', '')}  {r.get('title', '')}" + (f"  —  {r['speaker']}" if r.get("speaker") else ""), size=11, bold=True)
        _text(pdf, r.get("rule", ""), size=10, indent=4)
        if tr.get(r.get("rule")):
            _text(pdf, tr[r["rule"]], size=10, color=(0x0F, 0x6E, 0x56), indent=4)
        status = (r.get("verification") or {}).get("status")
        if status:
            label = {"verified": "Verified against speech", "needs_confirmation": "Numbers interpreted from spoken words: confirm",
                     "unsupported_number": "Contains a number nobody said", "rejected": "Quote not found in what was said"}.get(status, status)
            _text(pdf, label, size=9, color=(0x0F, 0x6E, 0x56) if status == "verified" else (0xB4, 0x57, 0x0A), indent=4)
        for a in r.get("acceptance") or []:
            _text(pdf, f"✓ {a}", size=9.5, indent=8)
        if r.get("source_quote"):
            _text(pdf, f"“{r['source_quote']}”", size=9.5, color=(0x3B, 0x46, 0x54), indent=4)
        if r.get("start") is not None:
            _text(pdf, f"Original recording {r['start']}s–{r['end']}s", size=8.5, color=(0x6E, 0x79, 0x85), indent=4)
        _text(pdf, f"Approved by {r.get('approved_by') or 'pending'}" + (f" · {r['approved_at']}" if r.get("approved_at") else ""), size=8.5, color=(0x6E, 0x79, 0x85), indent=4)
        pdf.ln(1)
    n += 1
    _heading(pdf, f"{n}. Open questions")
    for q in brd.get("open_questions") or ["None."]:
        _text(pdf, f"• {q}", indent=4)
    if brd.get("rejected"):
        n += 1
        _heading(pdf, f"{n}. Verification report: blocked AI content")
        for r in brd["rejected"]:
            _text(pdf, f"✗ {r.get('text', '')}  ({r.get('reason', '')})", size=9.5, color=(0xB4, 0x23, 0x18), indent=4)
    n += 1
    _heading(pdf, f"{n}. Sign-off")
    _text(pdf, brd.get("authorization", ""), size=10)
    _text(pdf, "Generated by VAANI. Hashes show recordings were not altered; they do not prove speaker identity or replace signatures.", size=8.5, color=(0x6E, 0x79, 0x85))
    out = pdf.output()
    return bytes(out) if not isinstance(out, (bytes, bytearray)) else bytes(out)
