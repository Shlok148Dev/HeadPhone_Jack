"""Service-to-service API (``/internal/*``; never exposed by the edge). CONTRACTS.md §3, §8."""

import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from jingle_common.logging import request_id_var
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError

from ..auth import hash_token, mint_token, require_service_token
from ..db import linked_sources, now, platform_connections, scrobble_tokens
from ..push.service import STREAM, last_key, np_key
from ..resources import Resources, get_resources
from ..stores import LISTENS

log = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", dependencies=[Depends(require_service_token)])


def api_error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "details": {},
                "request_id": request_id_var.get(),
            }
        },
        status_code=status,
    )


MAX_ACTIVE_TOKENS = 5


class MintRequest(BaseModel):
    user_id: UUID
    label: str | None = Field(default=None, max_length=60)


@router.post("/scrobble-tokens", status_code=201)
async def create_scrobble_token(
    body: MintRequest,
    res: Resources = Depends(get_resources),  # noqa: B008
) -> JSONResponse:
    token = mint_token()
    tid = uuid4()
    ts = now()
    try:
        async with res.engine.begin() as conn:
            # At most MAX_ACTIVE_TOKENS per user (SEC M3): minting revokes the oldest extras.
            active: list[UUID] = list(
                (
                    await conn.execute(
                        select(scrobble_tokens.c.id)
                        .where(scrobble_tokens.c.user_id == body.user_id)
                        .where(scrobble_tokens.c.revoked_at.is_(None))
                        .order_by(scrobble_tokens.c.created_at.desc())
                    )
                )
                .scalars()
                .all()
            )
            stale = active[MAX_ACTIVE_TOKENS - 1 :]
            if stale:
                await conn.execute(
                    update(scrobble_tokens)
                    .where(scrobble_tokens.c.id.in_(stale))
                    .values(revoked_at=ts, updated_at=ts)
                )
            await conn.execute(
                scrobble_tokens.insert().values(
                    id=tid,
                    user_id=body.user_id,
                    token_sha256=hash_token(token),
                    label=(body.label or "Jingle Companion").strip() or "Jingle Companion",
                    created_at=ts,
                    updated_at=ts,
                )
            )
    except IntegrityError:
        return api_error(404, "USER_NOT_FOUND", "No such user.")
    log.info("minted scrobble token %s", tid)
    # The plaintext token is returned exactly once and never stored or logged.
    return JSONResponse({"token": token, "id": str(tid)}, status_code=201)


@router.delete("/scrobble-tokens/{token_id}", status_code=204)
async def revoke_scrobble_token(
    token_id: UUID,
    res: Resources = Depends(get_resources),  # noqa: B008
) -> Response:
    ts = now()
    async with res.engine.begin() as conn:
        exists = (
            await conn.execute(select(scrobble_tokens.c.id).where(scrobble_tokens.c.id == token_id))
        ).first()
        if exists is None:
            return api_error(404, "TOKEN_NOT_FOUND", "No such scrobble token.")
        await conn.execute(
            update(scrobble_tokens)
            .where(scrobble_tokens.c.id == token_id)
            .where(scrobble_tokens.c.revoked_at.is_(None))
            .values(revoked_at=ts, updated_at=ts)
        )
    return Response(status_code=204)


@router.get("/healthz")
async def internal_healthz(
    request: Request,
    res: Resources = Depends(get_resources),  # noqa: B008
) -> JSONResponse:
    deps: dict[str, str] = {}
    try:
        async with res.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        deps["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        deps["postgres"] = f"error: {type(exc).__name__}"
    try:
        await res.redis.ping()
        deps["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        deps["redis"] = f"error: {type(exc).__name__}"
    try:
        await res.mongo.command("ping")
        deps["mongo"] = "ok"
    except Exception as exc:  # noqa: BLE001
        deps["mongo"] = f"error: {type(exc).__name__}"
    ok = all(v == "ok" for v in deps.values())
    body: dict[str, Any] = {
        "status": "ok" if ok else "degraded",
        "deps": deps,
        "musicbrainz": "enabled" if res.settings.musicbrainz_active else "disabled",
    }
    return JSONResponse(body, status_code=200 if ok else 503)


@router.delete("/users/{user_id}/data", status_code=204)
async def delete_user_data(
    user_id: UUID,
    res: Resources = Depends(get_resources),  # noqa: B008
) -> Response:
    """Account deletion / consent withdrawal (DPDP; SEC M5). Idempotent.

    Revokes every scrobble token and deletes the user's listens, live/recent state, dedupe keys,
    stream entries, platform connections and routes. Recordings (shared catalog) are kept.
    """
    ts = now()
    async with res.engine.begin() as conn:
        await conn.execute(
            update(scrobble_tokens)
            .where(scrobble_tokens.c.user_id == user_id)
            .where(scrobble_tokens.c.revoked_at.is_(None))
            .values(revoked_at=ts, updated_at=ts)
        )
        await conn.execute(
            delete(platform_connections).where(platform_connections.c.user_id == user_id)
        )
        await conn.execute(delete(linked_sources).where(linked_sources.c.user_id == user_id))
    await res.mongo[LISTENS].delete_many({"meta.user_id": str(user_id)})
    keys = [np_key(user_id), last_key(user_id)]
    async for k in res.redis.scan_iter(match=f"dedupe:{user_id}:*", count=500):
        keys.append(k)
    await res.redis.delete(*keys)
    marker = f'"user_id":"{user_id}"'
    to_drop: list[Any] = []
    last_id = "-"
    while True:
        batch = await res.redis.xrange(STREAM, min=last_id, count=500)
        if not batch:
            break
        for entry_id, fields in batch:
            fields = fields or {}
            data = fields.get("data") or fields.get(b"data") or ""
            if isinstance(data, bytes):
                data = data.decode()
            if marker in data.replace(" ", ""):
                to_drop.append(entry_id)
        if len(batch) < 500:
            break
        eid = batch[-1][0]
        last_id = "(" + (eid.decode() if isinstance(eid, bytes) else str(eid))
    if to_drop:
        await res.redis.xdel(STREAM, *to_drop)
    log.info("deleted ingest data for a user (%d stream entries)", len(to_drop))
    return Response(status_code=204)


@router.post("/identity/drain")
async def drain_identity_queue(
    limit: int = 20,
    res: Resources = Depends(get_resources),  # noqa: B008
) -> JSONResponse:
    """Periodic job hook (Celery beat in core-api): resolve queued unresolved recordings."""
    counts = await res.resolver.drain_pending(max(1, min(limit, 60)))
    return JSONResponse(counts)


@router.get("/budgets")
async def budgets(res: Resources = Depends(get_resources)) -> dict:  # noqa: B008
    """Per-source rate budgets and live usage for the admin console (JNG-12-04)."""
    import time

    from ..ratelimit import usage_key

    now = int(time.time() // 60)
    out = []
    for name, bucket in sorted(res.source_buckets.items()):
        key = f"rl:src:{name}"
        minutes = [usage_key(key, now - i) for i in range(60)]
        rejected = [usage_key(key, now - i, "rejected") for i in range(60)]
        used = [int(v or 0) for v in await res.redis.mget(minutes)]
        rej = [int(v or 0) for v in await res.redis.mget(rejected)]
        out.append(
            {
                "source": name,
                "capacity": bucket.capacity,
                "per_second": round(bucket.rate, 3),
                "used_last_minute": used[0],
                "used_last_hour": sum(used),
                "rejected_last_hour": sum(rej),
            }
        )
    return {"sources": out}
