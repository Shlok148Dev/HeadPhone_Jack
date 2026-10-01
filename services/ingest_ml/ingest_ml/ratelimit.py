"""Redis token bucket (CONTRACTS.md §6 ``rl:{source}``).

One Lua script keeps refill + take atomic across replicas.
"""

import logging
import math
import time
from dataclasses import dataclass
from typing import Any, cast

from redis.asyncio import Redis

log = logging.getLogger(__name__)

_SCRIPT = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local state = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(state[1])
local ts = tonumber(state[2])
if tokens == nil then tokens = capacity; ts = now end
local elapsed = math.max(0, now - ts)
tokens = math.min(capacity, tokens + elapsed * rate)
local allowed = 0
local need = math.max(cost, 1)
if tokens >= need then tokens = tokens - cost; allowed = 1
elseif ARGV[5] == '1' then tokens = math.max(0, tokens - cost) end
redis.call('HSET', key, 'tokens', tostring(tokens), 'ts', tostring(now))
redis.call('EXPIRE', key, math.ceil(capacity / rate) + 1)
return {allowed, tostring(tokens)}
"""


@dataclass(frozen=True)
class BucketResult:
    allowed: bool
    limit: int
    remaining: int
    reset_in: int  # seconds until the bucket is full again
    retry_after: float  # seconds until one token is available (0 when allowed)

    def headers(self) -> dict[str, str]:
        """ListenBrainz-style rate-limit headers."""
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset-In": str(self.reset_in),
            "X-RateLimit-Reset": str(int(time.time()) + self.reset_in),
        }


SOURCE_PREFIX = "rl:src:"
USAGE_TTL = 2 * 3600


def usage_key(bucket_key: str, minute: int, kind: str = "used") -> str:
    """Per-minute counters for the admin budget view (JNG-12-04)."""
    return f"usage:{bucket_key[len(SOURCE_PREFIX) :]}:{kind}:{minute}"


class TokenBucket:
    def __init__(self, redis: "Redis", capacity: int, per_seconds: float) -> None:
        if capacity <= 0 or per_seconds <= 0:
            raise ValueError("capacity and per_seconds must be positive")
        self._redis = redis
        self.capacity = capacity
        self.rate = capacity / per_seconds  # tokens per second

    async def _record_usage(self, key: str, allowed: bool) -> None:
        k = usage_key(key, int(time.time() // 60), "used" if allowed else "rejected")
        try:
            pipe = self._redis.pipeline()
            pipe.incr(k)
            pipe.expire(k, USAGE_TTL)
            await pipe.execute()
        except Exception:  # noqa: BLE001 - usage stats must never break a request
            log.debug("usage counter unavailable")

    async def take(self, key: str, cost: int = 1, *, force: bool = False) -> BucketResult:
        """Take ``cost`` tokens. ``cost=0`` only checks that one token is available;
        ``force`` charges even when the bucket is short (used to record failures)."""
        raw = await cast(
            Any,
            self._redis.eval(
                _SCRIPT,
                1,
                key,
                self.capacity,
                self.rate,
                repr(time.time()),
                cost,
                "1" if force else "0",
            ),
        )
        allowed = bool(int(raw[0]))
        tokens = float(raw[1])
        if key.startswith(SOURCE_PREFIX) and cost > 0:
            await self._record_usage(key, allowed)
        reset_in = math.ceil((self.capacity - tokens) / self.rate)
        retry_after = 0.0 if allowed else max(0.0, (max(cost, 1) - tokens) / self.rate)
        return BucketResult(
            allowed=allowed,
            limit=self.capacity,
            remaining=max(0, math.floor(tokens)),
            reset_in=reset_in,
            retry_after=retry_after,
        )
