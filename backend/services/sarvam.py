"""Sarvam REST adapters, matched to https://docs.sarvam.ai/api-reference (checked 2026-10-17).

- Speech-to-text (sync REST): multipart, audio under 30 s, chunk-level timestamps.
  saaras:v4 adds `mode` (codemix keeps English words in Latin script inside Indic text) and `keyterms`
  (up to 50 domain words that bias recognition). Both are v4-only: v3 rejects keyterms with 400.
- Text-to-speech: JSON {text, language_code, model, speaker}; at most 2500 chars for bulbul:v3 / v4-flash.
  bulbul:v4-flash speakers are persona ids (name_lang_style) and must match the language.
- Translate: JSON {input, source_language_code, target_language_code, model}; 2000 chars for sarvam-translate:v1.
- Chat completions: OpenAI-compatible (/v1). Reasoning tokens count against max_tokens, so short prompts,
  a generous max_tokens and reasoning_effort=low are what make sarvam-105b answer instead of returning "".
Real speech is never replaced by demos.
"""
import asyncio
import hashlib
import io
import json
import os
import re
import tempfile
import time
import zipfile
import httpx
from services import config, cache

LANG_CODES = {"hindi": "hi-IN", "marathi": "mr-IN", "tamil": "ta-IN", "telugu": "te-IN", "bengali": "bn-IN",
              "kannada": "kn-IN", "english": "en-IN"}
# Bulbul v4-flash persona voices (https://docs.sarvam.ai/api/api-guides-tutorials/text-to-speech/voices).
# One warm "customer"/"narration" voice per language; Hinglish (enhi) personas read mixed Hindi/English naturally.
V4_SPEAKERS = {"hindi": "aparna_hi_customer", "english": "simran_en_customer", "kannada": "chaitra_kn_narration",
               "tamil": "gokul_ta_narration", "telugu": "kavitha_te_narration", "marathi": "ritu_mr_insurance",
               "bengali": "arnab_bn_conversation"}
SARVAM_BASE = "https://api.sarvam.ai"
TTS_LIMIT = 2500
TRANSLATE_LIMIT = 2000
KEYTERM_LIMIT = 50
_translations: dict[str, str] = {}
# Circuit breaker for the optional Sarvam chat model: after repeated failures the agent stops waiting on it.
_chat_failures = 0
_chat_paused_until = 0.0


def enabled() -> bool:
    return bool(config.USE_REAL_SARVAM and config.SARVAM_API_KEY)


class SarvamError(Exception):
    """A Sarvam failure with a message the user can act on, and the HTTP status the API should return."""
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def _check(r):
    """Turn Sarvam's documented error responses (error.code / error.message) into actionable messages.
    Seen live on 17 Oct: 402 insufficient_quota_error (credits used up) and 403 invalid_api_key_error (revoked key)."""
    if r.status_code < 400:
        return
    try:
        code = (r.json().get("error") or {}).get("code", "")
    except ValueError:
        code = ""
    if r.status_code == 402 or code == "insufficient_quota_error":
        raise SarvamError("Sarvam credits are used up (insufficient_quota). Top up at dashboard.sarvam.ai, then retry.", 402)
    if r.status_code == 403 or code == "invalid_api_key_error":
        raise SarvamError("Sarvam rejected the API key (invalid_api_key). Put a current key from dashboard.sarvam.ai in backend/.env and restart the backend.", 403)
    if r.status_code == 429:
        raise SarvamError("Sarvam rate limit reached. Retry in a few seconds.", 429)
    _check(r)


def _headers():
    return {"api-subscription-key": config.SARVAM_API_KEY}


def stt_is_v4() -> bool:
    return (config.SARVAM_STT_MODEL or "").startswith("saaras:v4")


def speaker_for(lang: str) -> str:
    """bulbul:v4-flash needs a persona id per language; bulbul:v3 uses one short name for every language."""
    model = config.SARVAM_TTS_MODEL or ""
    if model.startswith("bulbul:v4"):
        return config.SARVAM_TTS_SPEAKER if "_" in (config.SARVAM_TTS_SPEAKER or "") else V4_SPEAKERS.get(lang, V4_SPEAKERS["english"])
    return config.SARVAM_TTS_SPEAKER or "shubh"


def clean_keyterms(terms) -> list[str]:
    seen, out = set(), []
    for t in terms or []:
        t = str(t).strip()[:64]
        if len(t) >= 2 and t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
        if len(out) >= KEYTERM_LIMIT:
            break
    return out


async def transcribe(audio_bytes, lang, filename="recording.webm", content_type="audio/webm", keyterms=None):
    data = {"language_code": LANG_CODES[lang], "model": config.SARVAM_STT_MODEL, "with_timestamps": "true"}
    if stt_is_v4():
        data["mode"] = config.SARVAM_STT_MODE  # codemix: "मुझे stock alert चाहिए" stays readable
        terms = clean_keyterms(keyterms)
        if terms:
            data["keyterms"] = json.dumps(terms, ensure_ascii=False)
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{SARVAM_BASE}/speech-to-text", headers=_headers(),
            files={"file": (filename, audio_bytes, content_type)}, data=data)
        _check(r)
        return r.json()


def split_text(text: str, limit: int) -> list[str]:
    """Split on sentence/line boundaries so no piece exceeds the provider's character limit."""
    text = (text or "").strip()
    if len(text) <= limit:
        return [text] if text else []
    pieces, current = [], ""
    for sentence in _sentences(text):
        while len(sentence) > limit:  # a single overlong sentence is cut on a space
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            if current:
                pieces.append(current)
                current = ""
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if len(current) + len(sentence) + 1 > limit:
            pieces.append(current)
            current = sentence
        else:
            current = (current + " " + sentence).strip()
    if current:
        pieces.append(current)
    return [p for p in pieces if p]


def _sentences(text):
    out, start = [], 0
    for i, ch in enumerate(text):
        if ch in ".!?।\n":
            out.append(text[start:i + 1].strip())
            start = i + 1
    if text[start:].strip():
        out.append(text[start:].strip())
    return [s for s in out if s]


async def synthesize(text, lang):
    """Returns base64 WAV clips, one per <=2500-char piece, in order. Clips are cached on disk, so a
    rehearsal makes the same sentence instant on stage."""
    clips = []
    speaker = speaker_for(lang)
    async with httpx.AsyncClient(timeout=60) as client:
        for piece in split_text(text, TTS_LIMIT):
            key = cache.key(config.SARVAM_TTS_MODEL, speaker, LANG_CODES[lang], piece)
            hit = cache.get("tts", key)
            if hit:
                clips.extend(hit)
                continue
            r = await client.post(f"{SARVAM_BASE}/text-to-speech", headers=_headers(),
                json={"text": piece, "language_code": LANG_CODES[lang], "model": config.SARVAM_TTS_MODEL, "speaker": speaker})
            _check(r)
            audios = r.json()["audios"]
            cache.put("tts", key, audios)
            clips.extend(audios)
    return clips


async def translate(text, target, source="english", client=None):
    """English -> Indian language with sarvam-translate:v1. Results are cached in memory and on disk."""
    if not text.strip() or target == source:
        return text
    key = hashlib.sha256(f"{source}|{target}|{text}".encode()).hexdigest()
    if key in _translations:
        return _translations[key]
    hit = cache.get("translate", key)
    if hit:
        _translations[key] = hit
        return hit
    if client is None:
        async with httpx.AsyncClient(timeout=30) as own:
            return await translate(text, target, source, own)
    out = []
    for piece in split_text(text, TRANSLATE_LIMIT):
        for attempt in range(3):  # Sarvam rate limits (429) are retried with a short backoff
            r = await client.post(f"{SARVAM_BASE}/translate", headers=_headers(),
                json={"input": piece, "source_language_code": LANG_CODES[source], "target_language_code": LANG_CODES[target],
                      "model": config.SARVAM_TRANSLATE_MODEL, "mode": "formal"})
            if r.status_code != 429 or attempt == 2:
                break
            await asyncio.sleep(0.6 * (attempt + 1))
        _check(r)
        out.append(r.json()["translated_text"])
    result = " ".join(out)
    _translations[key] = result
    cache.put("translate", key, result)
    return result


def chat_available() -> bool:
    return enabled() and time.time() >= _chat_paused_until


def _note_chat_result(ok: bool):
    global _chat_failures, _chat_paused_until
    if ok:
        _chat_failures = 0
        return
    _chat_failures += 1
    if _chat_failures >= 2:  # stop waiting on it for 10 minutes; the main LLM takes over
        _chat_paused_until = time.time() + 600


async def chat_json(prompt, system=None, schema=None, max_tokens=None):
    """Sarvam's own LLM (OpenAI-compatible chat completions) in JSON mode. Returns raw text.

    schema: optional JSON schema -> strict structured output (response_format json_schema).
    Reasoning is kept low and max_tokens generous because reasoning tokens are billed against max_tokens;
    an exhausted budget returns content "" with finish_reason "length"."""
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    response_format = ({"type": "json_schema", "json_schema": {"name": "vaani", "strict": True, "schema": schema}}
                       if schema else {"type": "json_object"})
    payload = {"model": config.SARVAM_LLM_MODEL, "messages": messages, "temperature": 0,
               "max_tokens": max_tokens or config.SARVAM_LLM_MAX_TOKENS, "reasoning_effort": "low", "response_format": response_format}
    key = cache.key(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    hit = cache.get("chat", key)
    if hit:
        return hit
    try:
        async with httpx.AsyncClient(timeout=config.SARVAM_LLM_TIMEOUT) as client:
            r = await client.post(f"{SARVAM_BASE}/v1/chat/completions", headers=_headers(), json=payload)
            r.raise_for_status()
            choice = r.json()["choices"][0]
            content = (choice["message"].get("content") or "").strip()
            if not content:
                raise RuntimeError(f"sarvam chat returned no content (finish_reason={choice.get('finish_reason')})")
    except Exception:
        _note_chat_result(False)
        raise
    _note_chat_result(True)
    cache.put("chat", key, content)
    return content


# ── Batch speech-to-text with speaker diarization (recorded meetings) ──────────────────────────
# Sarvam's diarization is batch-only: create a job, upload the file, start, poll, download one JSON per file.
# The official SDK (`sarvamai`) wraps the storage handshake; it is synchronous, so it runs in a thread.
# Verified live on 2026-10-17: a 30 s two-voice Hindi file came back diarized in ~8 s.
MEETING_TIMEOUT = 600


def _sdk():
    from sarvamai import SarvamAI  # imported lazily: the SDK is only needed for batch jobs and Doc AI
    return SarvamAI(api_subscription_key=config.SARVAM_API_KEY)


def _meeting_job(path, language_code, num_speakers, keyterms):
    """Blocking SDK call. Returns the parsed output JSON for the single uploaded file."""
    client = _sdk()
    params = {"model": config.SARVAM_STT_MODEL if stt_is_v4() else "saaras:v4", "language_code": language_code,
              "with_timestamps": True, "with_diarization": True}
    if num_speakers:
        params["num_speakers"] = num_speakers
    if stt_is_v4():
        params["mode"] = config.SARVAM_STT_MODE
        terms = clean_keyterms(keyterms)
        if terms:
            params["keyterms"] = terms
    job = client.speech_to_text_job.create_job(**params)
    if not job.upload_files(file_paths=[path]):
        raise RuntimeError("upload failed")
    job.start()
    status = job.wait_until_complete(poll_interval=2, timeout=MEETING_TIMEOUT)
    state = getattr(status, "job_state", "")
    if str(state).lower() != "completed":
        raise RuntimeError(f"batch job ended in state {state}: {getattr(status, 'error_message', '')}")
    out_dir = tempfile.mkdtemp(prefix="vaani-batch-")
    job.download_outputs(output_dir=out_dir)
    files = [f for f in os.listdir(out_dir) if f.endswith(".json")]
    if not files:
        raise RuntimeError("batch job produced no output")
    with open(os.path.join(out_dir, files[0]), encoding="utf-8") as fh:
        return json.load(fh)


async def transcribe_meeting(audio_bytes, lang, filename="meeting.wav", num_speakers=2, keyterms=None):
    """Diarized transcript of a recorded meeting (any length up to Sarvam's 2 h batch limit).
    Returns {"transcript", "timestamps", "entries": [{"speaker_id","transcript","start","end"}], "language_code"}."""
    language_code = LANG_CODES.get(lang, "unknown") if lang else "unknown"
    suffix = os.path.splitext(filename or "")[1] or ".wav"
    fd, path = tempfile.mkstemp(prefix="vaani-meeting-", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(audio_bytes)
        raw = await asyncio.to_thread(_meeting_job, path, language_code, num_speakers, keyterms)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    entries = []
    for e in (raw.get("diarized_transcript") or {}).get("entries") or []:
        text = (e.get("transcript") or "").strip()
        if text:
            entries.append({"speaker_id": str(e.get("speaker_id", "0")), "transcript": text,
                            "start": e.get("start_time_seconds"), "end": e.get("end_time_seconds")})
    if not entries and raw.get("transcript"):  # diarization unavailable: one speaker
        entries = [{"speaker_id": "0", "transcript": raw["transcript"].strip(), "start": None, "end": None}]
    return {"transcript": raw.get("transcript", ""), "timestamps": raw.get("timestamps"), "entries": entries,
            "language_code": raw.get("language_code")}


# ── Document intelligence: a photo or PDF of handwritten/printed notes → text (Sarvam Doc AI digitise) ──
# Verified live on 2026-10-17: a 1-page Hindi/English note image came back in ~5 s.
NOTES_TIMEOUT = 180


def _digitise_job(file_bytes, filename, content_type, language_code):
    client = _sdk()
    start = client.doc_ai.digitise(file=[(filename, file_bytes, content_type)], language=language_code, content_type="mixed")
    job_id = start.job_id
    deadline = time.time() + NOTES_TIMEOUT
    while True:
        st = client.doc_ai.get_status(job_id)
        if st.status in ("completed", "partially_completed", "failed", "rejected"):
            break
        if time.time() > deadline:
            raise RuntimeError("Doc AI job timed out")
        time.sleep(1.5)
    if st.status in ("failed", "rejected"):
        raise RuntimeError(f"Doc AI job {st.status}")
    url = client.doc_ai.get_download_url(job_id).url
    data = httpx.get(url, timeout=60).content
    return parse_digitise_zip(data)


def parse_digitise_zip(data: bytes) -> dict:
    """The download is a zip: <doc>/metadata/page_NNN.json holds layout blocks in reading order (plus an HTML render)."""
    pages = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = sorted(n for n in z.namelist() if "/metadata/" in n and n.endswith(".json"))
        for n in names:
            page = json.loads(z.read(n).decode("utf-8"))
            blocks = sorted(page.get("blocks") or [], key=lambda b: b.get("reading_order", 0))
            pages.append("\n".join((b.get("text") or "").strip() for b in blocks if (b.get("text") or "").strip()))
    text = "\n\n".join(p for p in pages if p)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    return {"text": text, "lines": [ln for ln in lines if ln], "pages": len(pages)}


async def digitise_notes(file_bytes, filename, content_type, lang):
    language_code = LANG_CODES.get(lang, "en-IN") if lang else "en-IN"
    return await asyncio.to_thread(_digitise_job, file_bytes, filename or "notes.png", content_type or "image/png", language_code)


async def translate_many(texts, target, concurrency=None):
    """Translate many lines at once on ONE shared connection pool. A new connection per line (TLS handshake each time)
    made 26 lines take ~12 s; shared, 10 lines in parallel take ~0.9 s (measured 17 Oct). Returns {original: translated}."""
    unique = [t for t in dict.fromkeys(texts) if t and t.strip()]
    limit = concurrency or config.TRANSLATE_CONCURRENCY
    gate = asyncio.Semaphore(limit)  # created per call: safe across event loops
    async with httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=limit)) as client:
        async def one(text):
            async with gate:
                return text, await translate(text, target, client=client)
        return dict(await asyncio.gather(*(one(t) for t in unique)))
