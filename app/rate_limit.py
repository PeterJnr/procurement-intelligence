import math
import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, Response, status

from app.config import feature_enabled


class SlidingWindowRateLimiter:
    """Thread-safe per-process limiter for a single-server MVP deployment."""

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._last_cleanup = time.monotonic()

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()
            self._last_cleanup = time.monotonic()

    def check(self, key: str, *, limit: int, window_seconds: int) -> tuple[int, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            if now - self._last_cleanup >= window_seconds:
                empty_keys = []
                for existing_key, timestamps in self._requests.items():
                    while timestamps and timestamps[0] <= cutoff:
                        timestamps.popleft()
                    if not timestamps:
                        empty_keys.append(existing_key)
                for existing_key in empty_keys:
                    self._requests.pop(existing_key, None)
                self._last_cleanup = now

            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= limit:
                retry_after = max(1, math.ceil(timestamps[0] + window_seconds - now))
                return 0, retry_after
            timestamps.append(now)
            return limit - len(timestamps), 0


ai_rate_limiter = SlidingWindowRateLimiter()


def _client_identifier(request: Request) -> str:
    if feature_enabled("TRUST_PROXY_HEADERS"):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client is not None else "unknown-client"


def enforce_ai_rate_limit(request: Request, response: Response) -> None:
    if not feature_enabled("ENABLE_RATE_LIMITING", "true"):
        return
    limit = int(os.getenv("AI_RATE_LIMIT_REQUESTS", "20"))
    window_seconds = int(os.getenv("AI_RATE_LIMIT_WINDOW_SECONDS", "60"))
    remaining, retry_after = ai_rate_limiter.check(
        _client_identifier(request),
        limit=limit,
        window_seconds=window_seconds,
    )
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many AI requests; please try again shortly",
            headers={"Retry-After": str(retry_after)},
        )
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
