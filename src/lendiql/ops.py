"""Operations infrastructure — structured logging, Prometheus metrics, rate limiting, security headers."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import FastAPI, Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from lendiql.config import DB_PATH


# ── Structured Logging ───────────────────────────────────────────

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[logging.StreamHandler()],
    )
    # Quiet noisy libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("gdown").setLevel(logging.WARNING)


logger = logging.getLogger("lendiql")


# ── Prometheus Metrics (minimal /metrics endpoint) ───────────────

_metrics: dict[str, float] = defaultdict(float)
_histograms: dict[str, list[float]] = defaultdict(list)


def inc_counter(name: str, value: float = 1.0) -> None:
    _metrics[name] += value


def observe_histogram(name: str, value: float) -> None:
    _histograms[name].append(value)


def register_metrics_routes(app: FastAPI) -> None:
    @app.get("/metrics")
    def metrics():
        lines = []
        for name, val in sorted(_metrics.items()):
            lines.append(f"# HELP lendiq_{name} counter")
            lines.append(f"# TYPE lendiq_{name} counter")
            lines.append(f"lendiq_{name} {val}")

        for name, vals in sorted(_histograms.items()):
            if not vals:
                continue
            lines.append(f"# HELP lendiq_{name}_seconds histogram")
            lines.append(f"# TYPE lendiq_{name}_seconds histogram")
            for p in [50, 90, 95, 99]:
                idx = int(len(vals) * p / 100)
                sorted_vals = sorted(vals)
                lines.append(f"lendiq_{name}_seconds{{percentile=\"{p}\"}} {sorted_vals[min(idx, len(sorted_vals)-1)]:.4f}")
            lines.append(f"lendiq_{name}_seconds_count {len(vals)}")
            lines.append(f"lendiq_{name}_seconds_sum {sum(vals):.4f}")

        return Response("\n".join(lines), media_type="text/plain")


# ── Timing Middleware ─────────────────────────────────────────────

async def timing_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    observe_histogram(f"http_request_duration", elapsed)
    inc_counter(f"http_requests_total")
    inc_counter(f"http_requests_{request.method}_{request.url.path.replace('/', '_')}")
    response.headers["X-Request-Time-Ms"] = f"{int(elapsed * 1000)}"
    logger.info(
        "%s %s → %d (%.0fms)",
        request.method, request.url.path, response.status_code, elapsed * 1000,
    )
    return response


# ── Rate Limiting (in-memory token bucket) ────────────────────────

class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window
        self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]
        if len(self._buckets[key]) >= self.max_requests:
            return False
        self._buckets[key].append(now)
        return True


rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(client_ip):
        inc_counter("rate_limit_exceeded")
        return Response(
            "Rate limit exceeded. Try again later.",
            status_code=429,
        )
    return await call_next(request)


# ── Security Headers Middleware ──────────────────────────────────

async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
