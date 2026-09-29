"""Token-bucket rate limits on the Django cache (Redis in Compose, locmem in tests). NFR-SEC-04.

Usage on a DRF view method::

    @ratelimit(key="ip", rate="5/m", scope="register")
    def post(self, request): ...

``key`` is ``"ip"``, ``"user"``, ``"ip+email"`` or a callable ``(request) -> str``. Keys are
hashed so no email or IP is stored in clear in the cache. Exceeding the limit raises
``RATE_LIMITED`` (429) with ``Retry-After``, ``X-RateLimit-Limit`` and ``X-RateLimit-Remaining``.
"""

from __future__ import annotations

import functools
import hashlib
import math
import time
from collections.abc import Callable

from django.core.cache import cache

from .errors import ApiError

_PERIODS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_rate(rate: str) -> tuple[int, int]:
    """``"10/m"`` -> (10, 60)."""
    count, _, period = rate.partition("/")
    return int(count), _PERIODS[period.strip().lower()[0]]


def client_ip(request) -> str:
    """Client IP as seen by the edge.

    Caddy appends the peer address to X-Forwarded-For, so the right-most entry is the one our
    proxy observed (left-most entries are client-controlled).
    """
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[-1].strip()
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def _email(request) -> str:
    data = getattr(request, "data", None) or {}
    try:
        return str(data.get("email", "")).strip().lower()
    except AttributeError:
        return ""


def _key_for(request, key: str | Callable) -> str:
    if callable(key):
        return key(request)
    if key == "ip":
        return client_ip(request)
    if key == "user":
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return f"u:{user.pk}"
        return f"ip:{client_ip(request)}"
    if key == "ip+email":
        return f"{client_ip(request)}|{_email(request)}"
    raise ValueError(f"unknown ratelimit key {key!r}")


class RateLimited(ApiError):
    def __init__(self, wait: int, limit: int):
        super().__init__(
            code="RATE_LIMITED",
            message="Too many attempts. Please wait a moment and try again.",
            status_code=429,
            details={"retry_after": wait},
        )
        self.wait = wait
        self.extra_headers = {"X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": "0"}


def hit(scope: str, ident: str, rate: str, now: float | None = None) -> tuple[bool, int, int]:
    """Consume one token. Returns (allowed, remaining, retry_after_seconds)."""
    capacity, period = parse_rate(rate)
    refill_per_sec = capacity / period
    now = time.time() if now is None else now
    digest = hashlib.sha256(ident.encode()).hexdigest()[:32]
    cache_key = f"rl:{scope}:{digest}"
    tokens, ts = cache.get(cache_key) or (float(capacity), now)
    tokens = min(float(capacity), tokens + max(0.0, now - ts) * refill_per_sec)
    if tokens < 1:
        wait = math.ceil((1 - tokens) / refill_per_sec)
        cache.set(cache_key, (tokens, now), timeout=period)
        return False, 0, max(wait, 1)
    tokens -= 1
    cache.set(cache_key, (tokens, now), timeout=period)
    return True, int(tokens), 0


def ratelimit(*, key: str | Callable = "ip", rate: str, scope: str | None = None):
    """Decorate a DRF view method with a token-bucket limit."""

    def decorator(fn):
        name = scope or fn.__qualname__

        @functools.wraps(fn)
        def wrapper(self, request, *args, **kwargs):
            allowed, _remaining, wait = hit(name, _key_for(request, key), rate)
            if not allowed:
                raise RateLimited(wait=wait, limit=parse_rate(rate)[0])
            return fn(self, request, *args, **kwargs)

        return wrapper

    return decorator
