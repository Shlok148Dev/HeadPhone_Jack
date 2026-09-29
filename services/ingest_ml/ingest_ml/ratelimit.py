"""Redis token bucket (CONTRACTS.md §6 ``rl:{source}``).

One Lua script keeps refill + take atomic across replicas.
"""

import math
import time
from dataclasses import dataclass
from typing import Any, cast

from redis.asyncio import Redis

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
if tokens >= cost then tokens = tokens - cost; allowed = 1 end
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


class TokenBucket:
    def __init__(self, redis: "Redis", capacity: int, per_seconds: float) -> None:
        if capacity <= 0 or per_seconds <= 0:
            raise ValueError("capacity and per_seconds must be positive")
        self._redis = redis
        self.capacity = capacity
        self.rate = capacity / per_seconds  # tokens per second

    async def take(self, key: str, cost: int = 1) -> BucketResult:
        raw = await cast(Any, self._redis.eval(
            _SCRIPT, 1, key, self.capacity, self.rate, repr(time.time()), cost
        ))
        allowed = bool(int(raw[0]))
        tokens = float(raw[1])
        reset_in = math.ceil((self.capacity - tokens) / self.rate)
        retry_after = 0.0 if allowed else max(0.0, (cost - tokens) / self.rate)
        return BucketResult(
            allowed=allowed,
            limit=self.capacity,
            remaining=max(0, math.floor(tokens)),
            reset_in=reset_in,
            retry_after=retry_after,
        )
