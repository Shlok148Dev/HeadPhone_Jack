"""``@idempotent``: replay the stored response for a repeated ``Idempotency-Key`` (CONTRACTS.md §8).

Responses are stored per (user, path, key) in the Django cache (Redis in Compose) for 24 hours.
A concurrent duplicate gets ``409 IDEMPOTENCY_IN_PROGRESS``; a missing key gets
``400 IDEMPOTENCY_KEY_REQUIRED`` when ``required=True``.
"""

from __future__ import annotations

import functools
import hashlib

from django.core.cache import cache
from rest_framework.response import Response

from .errors import ApiError

TTL_SECONDS = 24 * 3600
HEADER = "Idempotency-Key"


def _cache_key(request, key: str) -> str:
    user = getattr(request, "user", None)
    uid = str(user.pk) if user is not None and user.is_authenticated else "anon"
    digest = hashlib.sha256(f"{uid}:{request.path}:{key}".encode()).hexdigest()
    return f"idem:{uid}:{digest}"


def idempotent(fn=None, *, required: bool = True):
    """Decorate a DRF view method (``post``) so retries with the same key are replayed."""

    def decorator(view_fn):
        @functools.wraps(view_fn)
        def wrapper(self, request, *args, **kwargs):
            key = request.headers.get(HEADER, "").strip()
            if not key:
                if required:
                    raise ApiError(
                        "IDEMPOTENCY_KEY_REQUIRED", "An Idempotency-Key header is required.", 400
                    )
                return view_fn(self, request, *args, **kwargs)
            if len(key) > 200:
                raise ApiError("VALIDATION_ERROR", "Idempotency-Key is too long.", 400)
            ckey = _cache_key(request, key)
            stored = cache.get(ckey)
            if stored is not None:
                resp = Response(stored["data"], status=stored["status"])
                resp["Idempotent-Replayed"] = "true"
                return resp
            lock = f"{ckey}:lock"
            if not cache.add(lock, 1, timeout=30):
                raise ApiError(
                    "IDEMPOTENCY_IN_PROGRESS", "This request is already being processed.", 409
                )
            try:
                response = view_fn(self, request, *args, **kwargs)
                if 200 <= response.status_code < 300:
                    cache.set(
                        ckey, {"status": response.status_code, "data": response.data}, TTL_SECONDS
                    )
                return response
            finally:
                cache.delete(lock)

        return wrapper

    if fn is not None:
        return decorator(fn)
    return decorator
