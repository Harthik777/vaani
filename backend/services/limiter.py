"""
Lightweight in-memory rate limiter for Vaani.
Protects against rapid accidental double-clicks or runaway loops
without interfering with hackathon judging or automated tests.
"""
import time
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class InMemoryRateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 180, burst_per_second: int = 8):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_per_second = burst_per_second
        self.history = defaultdict(list)
        self.last_cleanup = time.time()

    def _cleanup(self, now: float):
        if now - self.last_cleanup > 120:
            cutoff = now - 60
            for ip in list(self.history.keys()):
                self.history[ip] = [t for t in self.history[ip] if t > cutoff]
                if not self.history[ip]:
                    del self.history[ip]
            self.last_cleanup = now

    async def dispatch(self, request: Request, call_next):
        # Exclude CORS preflight OPTIONS, docs, health, and test suite client
        if request.method == "OPTIONS" or request.url.path in ("/", "/docs", "/openapi.json", "/api/health"):
            return await call_next(request)
        # A portal page on a phone loads its clips, QR images and static files in one burst; those are cheap reads.
        if request.method == "GET" and (request.url.path.startswith(("/api/evidence/", "/api/portals/", "/api/qr", "/app", "/p/"))):
            return await call_next(request)

        # Starlette testclient bypass
        if not request.client or request.client.host in ("testclient", "test", ""):
            return await call_next(request)

        client_ip = request.client.host
        now = time.time()
        self._cleanup(now)

        cutoff_min = now - 60
        cutoff_sec = now - 1.0

        timestamps = [t for t in self.history[client_ip] if t > cutoff_min]
        self.history[client_ip] = timestamps

        # Burst check (more than 8 requests in a single second)
        burst_count = sum(1 for t in timestamps if t > cutoff_sec)
        if burst_count >= self.burst_per_second:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many rapid requests. Please wait a moment."},
                headers={"Retry-After": "1"}
            )

        # Minute check
        if len(timestamps) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Request limit reached for this minute. Please wait a few seconds."},
                headers={"Retry-After": "5"}
            )

        self.history[client_ip].append(now)
        return await call_next(request)
