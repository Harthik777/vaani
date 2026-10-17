"""The WhatsApp interview bot: an owner talks to VAANI on WhatsApp, in voice notes or text, in their language.

Flow per sender (state in data/whatsapp_sessions/<number>.json):
  voice note  -> Sarvam Saaras (codemix) -> transcript line -> gap check -> next question back (text + Bulbul voice note)
  text        -> same (Roman-script Hindi/Kannada is transliterated first)
  "brd" / "done" / "बीआरडी" / "ಬಿಆರ್‌ಡಿ" -> extraction -> verifier -> BRD -> published portal -> summary in the owner's
                 register + link + QR image + voice summary
  "new" / "reset" / "नया" / "ಹೊಸ"       -> fresh session
  "lang hindi|kannada|tamil|telugu|marathi|bengali|english" -> switch language
Replies are TwiML, so the webhook needs no outbound credentials beyond those already used for sending.
"""
import base64
import json
import re
import secrets
import time
from pathlib import Path
from xml.sax.saxutils import escape

import httpx
from models import CompileIn, Rule
from services import agent, config, sarvam, store, llm, verify
from services.compiler import document, screens

SESSION_TTL = 6 * 3600
SCRIPT_LANG = [(re.compile(r"[ऀ-ॿ]"), "hindi"), (re.compile(r"[ಀ-೿]"), "kannada"), (re.compile(r"[஀-௿]"), "tamil"),
               (re.compile(r"[ఀ-౿]"), "telugu"), (re.compile(r"[ঀ-৿]"), "bengali")]
DONE_WORDS = {"brd", "done", "finish", "finished", "बीआरडी", "हो गया", "ho gaya", "bas", "बस", "ಬಿಆರ್‌ಡಿ", "ಮುಗಿಯಿತು", "mugiyitu", "complete"}
RESET_WORDS = {"new", "reset", "start", "restart", "नया", "शुरू", "naya", "ಹೊಸ", "hosa", "hi", "hello", "namaste", "नमस्ते", "ನಮಸ್ಕಾರ"}
GREETING = {
    "hindi": "नमस्ते! मैं VAANI हूँ। अपने बिज़नेस के लिए जो ऐप चाहिए, उसके बारे में voice note या message भेजिए। मैं सवाल पूछूँगी, और अंत में 'brd' लिखिए।",
    "kannada": "ನಮಸ್ಕಾರ! ನಾನು VAANI. ನಿಮ್ಮ ವ್ಯಾಪಾರಕ್ಕೆ ಬೇಕಾದ ಆ್ಯಪ್ ಬಗ್ಗೆ voice note ಅಥವಾ message ಕಳುಹಿಸಿ. ನಾನು ಪ್ರಶ್ನೆ ಕೇಳುತ್ತೇನೆ; ಕೊನೆಯಲ್ಲಿ 'brd' ಎಂದು ಬರೆಯಿರಿ.",
    "english": "Hello! I am VAANI. Send a voice note or a message about the app your business needs. I will ask what is missing; type 'brd' when you are done.",
}


def _dir() -> Path:
    d = Path(config.DATA_DIR) / "whatsapp_sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(number: str) -> Path:
    return _dir() / (re.sub(r"[^0-9]", "", number) + ".json")


def load(number: str) -> dict:
    p = _path(number)
    if p.exists():
        try:
            s = json.loads(p.read_text(encoding="utf-8"))
            if time.time() - s.get("updated", 0) < SESSION_TTL:
                return s
        except Exception:
            pass
    return {"number": number, "lang": config.WHATSAPP_BOT_LANG, "tx": "", "answers": [], "asked": [], "created": time.time(), "updated": time.time()}


def save(s: dict):
    s["updated"] = time.time()
    _path(s["number"]).write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")


def reset(number: str) -> dict:
    p = _path(number)
    if p.exists():
        p.unlink()
    return load(number)


def detect_lang(text: str, default: str) -> str:
    for rx, lang in SCRIPT_LANG:
        if rx.search(text or ""):
            return lang
    return default


def twiml(messages: list[dict]) -> str:
    """messages: [{"body": str, "media": [url, ...]}]"""
    parts = ["<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response>"]
    for m in messages:
        parts.append("<Message>")
        if m.get("body"):
            parts.append(f"<Body>{escape(m['body'])}</Body>")
        for u in m.get("media") or []:
            parts.append(f"<Media>{escape(u)}</Media>")
        parts.append("</Message>")
    parts.append("</Response>")
    return "".join(parts)


def public_url(path: str) -> str | None:
    base = (config.PUBLIC_API_URL or "").rstrip("/")
    if not base.lower().startswith("https://") or "localhost" in base or "127.0.0.1" in base:
        return None
    return base + path


async def fetch_media(url: str) -> tuple[bytes, str]:
    from services import whatsapp as _wa
    async with httpx.AsyncClient(timeout=60, auth=_wa.auth(), follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "application/octet-stream").split(";")[0]


async def voice_note(text: str, lang: str) -> str | None:
    """Bulbul audio saved under data/media and returned as a public URL (None when the server is not public)."""
    if not public_url("/") or not sarvam.enabled():
        return None
    try:
        clips = await sarvam.synthesize(text, lang)
        ident = secrets.token_urlsafe(18)
        media = Path(config.DATA_DIR) / "media"
        media.mkdir(parents=True, exist_ok=True)
        (media / f"{ident}.wav").write_bytes(base64.b64decode(clips[0]))
        return public_url(f"/api/media/{ident}.wav")
    except Exception:
        return None


async def transcribe_note(data: bytes, mime: str, lang: str) -> str:
    ext = {"audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/amr": "amr", "audio/wav": "wav", "audio/webm": "webm"}.get(mime, "ogg")
    result = await sarvam.transcribe(data, lang, f"note.{ext}", mime)
    return (result.get("transcript") or "").strip()


async def next_question(s: dict) -> tuple[str, str | None]:
    """Run the gap check on the session transcript; return (local question or closing line, audio url)."""
    answered = [a["key"] for a in s["answers"]]
    gaps = await agent.assess(s["tx"], "business", s["lang"], answered, False)
    s["completeness"] = gaps["completeness"]
    pending = [q for q in gaps["questions"] if q["key"] not in s["asked"]] or gaps["questions"]
    if not pending:
        text = {"hindi": "सब कुछ मिल गया। BRD बनाने के लिए 'brd' लिखिए।", "kannada": "ಎಲ್ಲಾ ಸಿಕ್ಕಿದೆ. BRD ಮಾಡಲು 'brd' ಎಂದು ಬರೆಯಿರಿ."}.get(s["lang"], "I have everything I need. Type 'brd' to get the document.")
        s["pending_key"] = None
        return text, await voice_note(text, s["lang"])
    q = pending[0]
    s["pending_key"] = q["key"]
    s["asked"] = (s["asked"] + [q["key"]])[-8:]
    text = q.get("question_local") or q["question"]
    body = f"{text}\n({s['completeness']}% complete · reply by voice or text · 'brd' to finish)"
    return body, await voice_note(text, s["lang"])


async def build_brd(s: dict) -> tuple[list[dict], str | None]:
    """Extract, verify, draft, publish. Returns (messages, error)."""
    from routes.extract import extract as extract_route, ExtractIn
    result = await extract_route(ExtractIn(transcript=s["tx"], domain="Business operations", mode="business", demo=False))
    rules = []
    for r in result["rules"]:
        rules.append(Rule(**{**r, "speaker": r.get("speaker") or "Owner", "approved_at": store.now(), "approved_by": f"{s['number']} (WhatsApp)"}))
    if not rules:
        return [], "no_rules"
    body = CompileIn(rules=rules, mode="business", transcript=s["tx"], answers=[], metadata={"title": s.get("title") or "WhatsApp requirements", "owner": s["number"]})
    sections, acceptance = None, []
    if llm.live():
        try:
            from services import brd_ai
            ai = await brd_ai.draft(body)
            sections, acceptance = ai["sections"], ai["acceptance"]
        except Exception:
            pass
    body = CompileIn(**{**body.model_dump(), "sections": sections, "acceptance": acceptance})
    doc = document(body)
    payload = {"mode": "business", "demo": False, "metadata": body.metadata, "language": s["lang"], "rules": [r.model_dump() for r in rules],
               "brd": doc, **screens(body), "app_generator": "template", "evidence": [], "transcript": s["tx"], "published_at": store.now()}
    ident, key = store.create("portal", payload)
    link = f"{config.FRONTEND_URL.rstrip('/')}?portal={ident}#key={key}"
    n = len(doc["business_rules"])
    checks = [verify.verify_rule(r.model_dump(), s["tx"])["status"] for r in rules]
    verified = sum(1 for c in checks if c == "verified")
    summary_en = f"{doc['project_name']}. {n} requirements, {verified} verified against your words. " + " ".join(
        f"{r['req_id']}: {r['title']}." for r in doc["business_rules"][:6]) + (f" {len(doc['open_questions'])} open questions." if doc["open_questions"] else "")
    summary = summary_en
    if s["lang"] != "english" and sarvam.enabled():
        try:
            summary = await sarvam.translate_colloquial(summary_en, s["lang"])
        except Exception:
            pass
    msgs = [{"body": f"VAANI BRD\n\n{summary}\n\n{link}"}]
    qr = public_url("/api/qr.png?size=6&data=" + httpx.URL(link).__str__().replace("&", "%26").replace("#", "%23"))
    audio = await voice_note(summary, s["lang"])
    media = [u for u in (qr, audio) if u]
    if media:
        msgs.append({"body": "Scan to open the BRD with every quote." if qr else "", "media": media})
    s["portal"] = link
    return msgs, None


async def handle(number: str, text: str, media_url: str | None, media_type: str | None) -> str:
    """Main entry: returns TwiML."""
    s = load(number)
    text = (text or "").strip()
    low = text.lower()
    if low.startswith("lang "):
        lang = low.split(" ", 1)[1].strip()
        if lang in sarvam.LANG_CODES:
            s["lang"] = lang
            save(s)
            return twiml([{"body": GREETING.get(lang, GREETING["english"])}])
    if low in RESET_WORDS or (not text and not media_url):
        s = reset(number)
        save(s)
        return twiml([{"body": GREETING.get(s["lang"], GREETING["english"])}])
    if low in DONE_WORDS:
        if not s["tx"].strip():
            return twiml([{"body": GREETING.get(s["lang"], GREETING["english"])}])
        try:
            msgs, err = await build_brd(s)
        except Exception as exc:
            msgs, err = [], str(exc)
        if err:
            msgs = [{"body": {"hindi": "BRD नहीं बन पाया। थोड़ा और बताइए, फिर 'brd' लिखिए।"}.get(s["lang"], "I could not build the BRD yet. Tell me a little more, then type 'brd'.")}]
        save(s)
        return twiml(msgs)
    # Input: voice note or text
    line = text
    if media_url and (media_type or "").startswith("audio"):
        if not sarvam.enabled():
            return twiml([{"body": "Voice notes need Sarvam. Please type your message."}])
        try:
            data, mime = await fetch_media(media_url)
            line = await transcribe_note(data, mime, s["lang"])
        except Exception:
            return twiml([{"body": {"hindi": "आवाज़ समझ नहीं आई। दोबारा भेजिए या लिखिए।"}.get(s["lang"], "I could not hear that. Please send it again or type it.")}])
        if not line:
            return twiml([{"body": {"hindi": "आवाज़ में कुछ सुनाई नहीं दिया। दोबारा बोलिए।"}.get(s["lang"], "I heard nothing in that note. Please try again.")}])
    else:
        s["lang"] = detect_lang(line, s["lang"])
        if sarvam.enabled() and s["lang"] != "english" and re.search(r"[A-Za-z]{3,}", line) and not re.search(r"[ऀ-෿]", line):
            try:
                line = await sarvam.transliterate(line, s["lang"])
            except Exception:
                pass
    if s.get("pending_key"):
        s["answers"].append({"key": s["pending_key"], "answer": line})
    s["tx"] = (s["tx"] + "\n" if s["tx"] else "") + f"[Owner] {line}"
    if not s.get("title"):
        s["title"] = line[:60]
    try:
        body, audio = await next_question(s)
    except Exception:
        body, audio = {"hindi": "समझ गई। और बताइए, या 'brd' लिखिए।"}.get(s["lang"], "Got it. Tell me more, or type 'brd'."), None
    save(s)
    echo = {"hindi": "✔ सुना", "kannada": "✔ ಕೇಳಿದೆ"}.get(s["lang"], "✔ Heard")
    msgs = [{"body": f"{echo}: “{line[:200]}”\n\n{body}", "media": [audio] if audio else []}]
    return twiml(msgs)
