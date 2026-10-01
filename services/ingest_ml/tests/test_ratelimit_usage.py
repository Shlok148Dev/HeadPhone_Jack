"""Usage counters for the admin budget view (JNG-12-04)."""

import time

import fakeredis.aioredis
import pytest

from ingest_ml.ratelimit import TokenBucket, usage_key


@pytest.mark.asyncio
async def test_source_buckets_count_used_and_rejected():
    r = fakeredis.aioredis.FakeRedis()
    b = TokenBucket(r, 2, 60.0)
    for _ in range(3):
        await b.take("rl:src:lastfm")
    await b.take("rl:push:user:x")  # not a source bucket: not counted
    minute = int(time.time() // 60)
    assert int(await r.get(usage_key("rl:src:lastfm", minute))) == 2
    assert int(await r.get(usage_key("rl:src:lastfm", minute, "rejected"))) == 1
    assert await r.keys("usage:push*") == []
