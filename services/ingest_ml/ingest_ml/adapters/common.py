"""Shared plumbing for polling adapters: HTTP with backoff, rate budgets, sealed credentials.

Retries: at most 3 attempts with exponential backoff and jitter, honouring ``Retry-After``
(NFR-AVAIL-04). Budgets: a Redis token bucket per source at ≤ 80 % of its limit (NFR-SCAL-06).
"""

import asyncio
import json
import random
from typing import Any
from uuid import UUID

import httpx
from jingle_common.crypto import TokenCipher

from ..ratelimit import TokenBucket


class AdapterError(Exception):
    """The source failed in a way the caller should log and retry later."""


class ReauthRequired(AdapterError):
    """The user must reconnect (token revoked, expired or not allowed)."""

    def __init__(self, reason: str = "reauth") -> None:
        super().__init__(reason)
        self.reason = reason


class RateLimited(AdapterError):
    def __init__(self, retry_after: float) -> None:
        super().__init__(f"rate limited for {retry_after:.0f}s")
        self.retry_after = retry_after


class BudgetExhausted(AdapterError):
    """Our own budget for the source is empty: skip this poll and keep the cached state."""


MAX_ATTEMPTS = 3


def _retry_after(resp: httpx.Response, default: float) -> float:
    try:
        return max(0.0, float(resp.headers.get("Retry-After", default)))
    except ValueError:
        return default


async def request_json(
    http: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    bucket: TokenBucket | None = None,
    bucket_key: str = "",
    reauth_statuses: tuple[int, ...] = (401,),
    sleep: Any = asyncio.sleep,
    **kwargs: Any,
) -> tuple[int, Any]:
    """Return ``(status, json_or_None)``; 204 → ``(204, None)``.

    Raises ReauthRequired, RateLimited (after retries), BudgetExhausted or AdapterError.
    """
    if bucket is not None and not (await bucket.take(bucket_key)).allowed:
        raise BudgetExhausted(bucket_key)
    delay = 1.0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = await http.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            if attempt == MAX_ATTEMPTS:
                raise AdapterError(f"network error: {type(exc).__name__}") from None
            await sleep(delay + random.uniform(0, delay / 2))  # noqa: S311 - jitter
            delay *= 2
            continue
        if resp.status_code in reauth_statuses:
            raise ReauthRequired(f"http_{resp.status_code}")
        if resp.status_code == 429:
            wait = _retry_after(resp, delay)
            if attempt == MAX_ATTEMPTS or wait > 30:
                raise RateLimited(wait)
            await sleep(wait + random.uniform(0, 0.5))  # noqa: S311
            continue
        if resp.status_code >= 500:
            if attempt == MAX_ATTEMPTS:
                raise AdapterError(f"upstream {resp.status_code}")
            await sleep(delay + random.uniform(0, delay / 2))  # noqa: S311
            delay *= 2
            continue
        if resp.status_code == 204 or not resp.content:
            return resp.status_code, None
        try:
            return resp.status_code, resp.json()
        except ValueError:
            raise AdapterError("invalid JSON from source") from None
    raise AdapterError("unreachable")  # pragma: no cover


def seal(cipher: TokenCipher, secret: dict[str, Any], user_id: UUID) -> str:
    """Encrypt a credential bundle, bound to its user (AAD) so ciphertexts can't be swapped."""
    return cipher.encrypt(json.dumps(secret), aad=str(user_id))


def unseal(cipher: TokenCipher, ciphertext: str, user_id: UUID) -> dict[str, Any]:
    data = json.loads(cipher.decrypt(ciphertext, aad=str(user_id)))
    if not isinstance(data, dict):
        raise AdapterError("corrupt credential")
    return data
