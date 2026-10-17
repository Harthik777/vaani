"""Environment configuration; external calls are opt-in."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()

# Smart activation: active if key is present and not explicitly set to false
_sarvam_flag = os.getenv("USE_REAL_SARVAM", "").strip().lower()
USE_REAL_SARVAM = (_sarvam_flag == "true" and bool(SARVAM_API_KEY)) or (_sarvam_flag != "false" and bool(SARVAM_API_KEY))

_llm_flag = os.getenv("USE_REAL_LLM", "").strip().lower()
USE_REAL_LLM = (_llm_flag == "true" and bool(LLM_API_KEY)) or (_llm_flag != "false" and bool(LLM_API_KEY))

USE_REAL_PAYTM = os.getenv("USE_REAL_PAYTM", "false").strip().lower() == "true"

# Smart defaults: if user leaves LLM_URL or LLM_MODEL blank, auto-detect provider from key
_raw_url = os.getenv("LLM_URL", "").strip()
_raw_model = os.getenv("LLM_MODEL", "").strip()
_norm_model = _raw_model.lower().replace(" ", "-") if _raw_model else ""
LLM_PROVIDER = "custom" if _raw_url else "none"

if not _raw_url:
    if _norm_model.startswith("gemini") or LLM_API_KEY.startswith("AIzaSy") or LLM_API_KEY.startswith("AQ."):
        _raw_url = "https://generativelanguage.googleapis.com/v1beta/models"
        if not _norm_model or _norm_model in {"gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash", "gemini-pro", "gemini-3.5-flash", "gemini-3.6-flash"}:
            _norm_model = "gemini-3.8-flash"
        _raw_model = _norm_model
        LLM_PROVIDER = "gemini"
    elif LLM_API_KEY.startswith("gsk_"):
        _raw_url = "https://api.groq.com/openai/v1/chat/completions"
        _raw_model = _norm_model or "llama-3.3-70b-versatile"
        LLM_PROVIDER = "groq"
    elif LLM_API_KEY.startswith("sk-or-"):
        _raw_url = "https://openrouter.ai/api/v1/chat/completions"
        _raw_model = _norm_model or "google/gemini-2.0-flash-001"
        LLM_PROVIDER = "openrouter"
    elif LLM_API_KEY.startswith("sk-ant-"):
        _raw_url = "https://api.anthropic.com/v1/messages"
        _raw_model = _norm_model or "claude-3-5-sonnet-20241022"
        LLM_PROVIDER = "anthropic"
    elif LLM_API_KEY:
        _raw_url = "https://api.openai.com/v1/chat/completions"
        _raw_model = _norm_model or "gpt-4o-mini"
        LLM_PROVIDER = "openai"
    else:
        _raw_url = ""
        _raw_model = _norm_model or "gpt-4o-mini"
        LLM_PROVIDER = "mock"

LLM_URL = _raw_url
LLM_MODEL = _norm_model or _raw_model or "gpt-4o-mini"
# Speed (teammate's measurements, 17 Oct): short structured tasks (gap check, extraction + conflicts) use the fast model;
# long writing (BRD draft, app) uses LLM_MODEL with thinking set to low.
LLM_FAST_MODEL = os.getenv("LLM_FAST_MODEL", "gemini-3.5-flash-lite").strip().lower()
LLM_THINKING = os.getenv("LLM_THINKING", "low").strip().lower()
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "45"))        # seconds per model call before trying the next model
TRANSLATE_CONCURRENCY = int(os.getenv("TRANSLATE_CONCURRENCY", "10"))  # 10 is safe; 40 hit Sarvam's 429 rate limit
# Sarvam models (checked against docs.sarvam.ai on 2026-10-17): saaras:v4 is the current STT default,
# bulbul:v4-flash the recommended TTS model, sarvam-105b-conversations the 32K chat model built for short turns.
SARVAM_STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v4")
SARVAM_STT_MODE = os.getenv("SARVAM_STT_MODE", "codemix")  # v4 only: transcribe | codemix | verbatim | translit
SARVAM_TTS_MODEL = os.getenv("SARVAM_TTS_MODEL", "bulbul:v4-flash")
SARVAM_TTS_SPEAKER = os.getenv("SARVAM_TTS_SPEAKER", "").strip()  # blank = per-language persona (v4) or shubh (v3)
SARVAM_TRANSLATE_MODEL = os.getenv("SARVAM_TRANSLATE_MODEL", "sarvam-translate:v1")
SARVAM_LLM_MODEL = os.getenv("SARVAM_LLM_MODEL", "sarvam-105b-conversations")
SARVAM_LLM_MAX_TOKENS = int(os.getenv("SARVAM_LLM_MAX_TOKENS", "3000"))  # Starter plan caps at 4096; reasoning counts
SARVAM_LLM_TIMEOUT = float(os.getenv("SARVAM_LLM_TIMEOUT", "8"))
CACHE_ENABLED = os.getenv("VAANI_CACHE", "on").strip().lower() not in {"off", "false", "0"}
# The two-speaker meeting demo runs through the real agent and extraction when a model is configured (the fixture is the
# offline path and the safety net if a call fails). VAANI_DEMO_LIVE=off pins the demo to the fixture.
DEMO_LIVE = os.getenv("VAANI_DEMO_LIVE", "on").strip().lower() not in {"off", "false", "0"}

# LLM_PROVIDER=sarvam makes Sarvam's own chat model the main brain (no second key needed).
if os.getenv("LLM_PROVIDER", "").strip().lower() == "sarvam" and SARVAM_API_KEY:
    LLM_PROVIDER, LLM_MODEL, LLM_URL = "sarvam", SARVAM_LLM_MODEL, "https://api.sarvam.ai/v1/chat/completions"
    USE_REAL_LLM = _llm_flag != "false"

# AGENT_LLM=sarvam routes the interview agent (gap questions, conflict check) to Sarvam's chat model first,
# falling back to the main LLM on any failure. A circuit breaker (services.sarvam) stops waiting on it after
# two consecutive failures, so a bad key or outage costs at most two short timeouts.
AGENT_LLM = os.getenv("AGENT_LLM", "sarvam").strip().lower()
# Google Drive (BRD as a Google Doc) and Google Calendar (deadlines): a free OAuth client from Google Cloud Console.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT = os.getenv("GOOGLE_REDIRECT", "http://localhost:8000/api/google/callback").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = os.getenv("SMTP_PORT", "587").strip()
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()
PAYTM_MID = os.getenv("PAYTM_MID", "")
PAYTM_KEY = os.getenv("PAYTM_KEY", "")
PAYTM_ENV = os.getenv("PAYTM_ENV", "staging")
DATA_DIR = Path(os.getenv("VAANI_DATA_DIR", str(Path(__file__).resolve().parents[1] / "data")))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
FRONTEND_URL_SET = bool(os.getenv("FRONTEND_URL"))
# Share links must open on a phone. PUBLIC_URL (e.g. a Cloudflare quick tunnel: `cloudflared tunnel --url http://localhost:8000`)
# wins; otherwise the backend serves the built frontend at /app on the laptop's LAN address for phones on the same Wi-Fi.
PUBLIC_URL = os.getenv("PUBLIC_URL", "").strip().rstrip("/")


def lan_ip() -> str:
    """The address other devices on this network use to reach this machine (no packet is sent)."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"
PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://localhost:8000")
PUBLISH_API_KEY = os.getenv("PUBLISH_API_KEY", "")
WORK_ORDER_URL = os.getenv("WORK_ORDER_URL", "")
WORK_ORDER_API_KEY = os.getenv("WORK_ORDER_API_KEY", "")
