"""Vaani: a voice-first BRD agent with source-backed requirements and durable portals."""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from routes.portals import FRONTEND_DIST, share_base
from fastapi.middleware.cors import CORSMiddleware

from routes import extract, brd, screenspec, tts, upi, stt, evidence, portals, tickets, agent, app_gen, notes, qr, exports, demo, reason, integrations, help as help_routes
from services import config, llm, sarvam, mailer, google_sync
from services.limiter import InMemoryRateLimiter

app = FastAPI(title="Vaani API")

@app.middleware("http")
async def private_responses(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

# Light, optimal rate limiter (180 req/min, burst max 8/sec)
app.add_middleware(InMemoryRateLimiter, requests_per_minute=240, burst_per_second=12)

# allow the Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL.rstrip("/"), "http://localhost:5173", "http://127.0.0.1:5173", "null"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (stt, notes, extract, agent, screenspec, brd, tts, app_gen, upi, evidence, portals, tickets, qr, exports, demo, reason, integrations, help_routes):
    app.include_router(module.router)
# The built frontend (frontend/dist, from `npx vite build`) is served here so one LAN or tunnel address opens the whole app on a phone.
if FRONTEND_DIST.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="app")


@app.get("/")
@app.get("/api/health")
def health(request: Request):
    app_base, _, reach = share_base(request)
    return {
        "ok": True,
        "service": "vaani",
        "live_stt": sarvam.enabled(),
        "live_llm": llm.live(),
        "llm_provider": getattr(config, "LLM_PROVIDER", "mock"),
        "llm_model": config.LLM_MODEL if llm.live() else "mock",
        "sarvam": {
            "stt": config.SARVAM_STT_MODEL if sarvam.enabled() else None,
            "stt_mode": config.SARVAM_STT_MODE if sarvam.enabled() and sarvam.stt_is_v4() else None,
            "tts": config.SARVAM_TTS_MODEL if sarvam.enabled() else None,
            "tts_speakers": sarvam.V4_SPEAKERS if sarvam.enabled() and config.SARVAM_TTS_MODEL.startswith("bulbul:v4") else None,
            "translate": config.SARVAM_TRANSLATE_MODEL if sarvam.enabled() else None,
            "diarization": "batch" if sarvam.enabled() else None,
            "doc_ai": "digitise" if sarvam.enabled() else None,
            "agent_llm": config.SARVAM_LLM_MODEL if sarvam.enabled() and config.AGENT_LLM == "sarvam" else None,
        },
        "payment_provider": "paytm" if config.USE_REAL_PAYTM else "upi-intent",
        "cache": config.CACHE_ENABLED,
        "share": {"base": app_base, "reach": reach},
        "email": mailer.enabled(),
        "google": google_sync.enabled(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
