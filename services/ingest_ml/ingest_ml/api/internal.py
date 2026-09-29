"""Service-to-service API (``/internal/*``; never exposed by the edge). CONTRACTS.md §3, §8."""

import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from jingle_common.logging import request_id_var
from pydantic import BaseModel, Field
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError

from ..auth import hash_token, mint_token, require_service_token
from ..db import now, scrobble_tokens
from ..resources import Resources, get_resources

log = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", dependencies=[Depends(require_service_token)])


def api_error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"error": {"code": code, "message": message, "details": {},
                   "request_id": request_id_var.get()}},
        status_code=status,
    )


class MintRequest(BaseModel):
    user_id: UUID
    label: str | None = Field(default=None, max_length=60)


@router.post("/scrobble-tokens", status_code=201)
async def create_scrobble_token(
    body: MintRequest, res: Resources = Depends(get_resources)  # noqa: B008
) -> JSONResponse:
    token = mint_token()
    tid = uuid4()
    ts = now()
    try:
        async with res.engine.begin() as conn:
            await conn.execute(
                scrobble_tokens.insert().values(
                    id=tid, user_id=body.user_id, token_sha256=hash_token(token),
                    label=(body.label or "Jingle Companion").strip() or "Jingle Companion",
                    created_at=ts, updated_at=ts,
                )
            )
    except IntegrityError:
        return api_error(404, "USER_NOT_FOUND", "No such user.")
    log.info("minted scrobble token %s", tid)
    # The plaintext token is returned exactly once and never stored or logged.
    return JSONResponse({"token": token, "id": str(tid)}, status_code=201)


@router.delete("/scrobble-tokens/{token_id}", status_code=204)
async def revoke_scrobble_token(
    token_id: UUID, res: Resources = Depends(get_resources)  # noqa: B008
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
    request: Request, res: Resources = Depends(get_resources)  # noqa: B008
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
