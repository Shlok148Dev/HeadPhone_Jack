"""Internal Jingle Connect API, called only by core-api with the service token (ADR-0006)."""

import asyncio
import json
import logging
import os
import tempfile
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from jingle_common.enums import EventKind, Platform, SourceKind, SourceStatus, Via
from pydantic import BaseModel, Field

from ..adapters.base import Capabilities, CompanionRoute
from ..auth import require_service_token
from ..orchestrator import ConnectError, Orchestrator
from ..poller import poll_due
from ..record import record_plays
from ..resources import Resources, get_resources
from ..sources_store import ensure_platform_connection
from ..takeout import MAX_BYTES, TakeoutError, sniff_and_parse
from .internal import api_error

log = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", dependencies=[Depends(require_service_token)])

EXPORT_ROUTE = CompanionRoute(
    kind=SourceKind.YOUTUBE_EXPORT,
    via=Via.EXPORT,
    caps=Capabilities(live=False, recent=True, top=False, playlist_write=False, trainable=True),
)
IMPORT_TTL = 86_400


def _orch(res: Resources) -> Orchestrator:
    return Orchestrator(res)


def _err(exc: ConnectError, status: int = 400) -> JSONResponse:
    return api_error(status, exc.code, exc.message)


class StartRequest(BaseModel):
    user_id: UUID
    platform: Platform
    allowlisted: bool = False
    flags: dict[str, bool] = Field(default_factory=dict)


@router.post("/connect/start")
async def connect_start(
    body: StartRequest, res: Resources = Depends(get_resources)
) -> JSONResponse:  # noqa: B008
    plan = await _orch(res).start(
        body.user_id, body.platform, allowlisted=body.allowlisted, flags=body.flags
    )
    return JSONResponse(plan.as_dict())


class CallbackRequest(BaseModel):
    state: str = Field(max_length=200)
    code: str | None = Field(default=None, max_length=2000)
    token: str | None = Field(default=None, max_length=200)


@router.post("/connect/spotify/callback")
async def spotify_callback(
    body: CallbackRequest, res: Resources = Depends(get_resources)
) -> JSONResponse:  # noqa: B008
    try:
        user_id, platform = await _orch(res).complete_spotify(body.state, body.code or "")
    except ConnectError as exc:
        return _err(exc)
    return JSONResponse({"user_id": str(user_id), "platform": platform.value})


@router.post("/connect/lastfm/callback")
async def lastfm_callback(
    body: CallbackRequest, res: Resources = Depends(get_resources)
) -> JSONResponse:  # noqa: B008
    try:
        user_id, platform = await _orch(res).complete_lastfm(body.state, body.token or "")
    except ConnectError as exc:
        return _err(exc)
    return JSONResponse({"user_id": str(user_id), "platform": platform.value})


class LinkRequest(BaseModel):
    user_id: UUID
    platform: Platform
    token: str | None = Field(default=None, max_length=200)
    username: str | None = Field(default=None, max_length=64)


@router.post("/connect/listenbrainz")
async def link_listenbrainz(
    body: LinkRequest, res: Resources = Depends(get_resources)
) -> JSONResponse:  # noqa: B008
    try:
        await _orch(res).link_listenbrainz(body.user_id, body.platform, body.token or "")
    except ConnectError as exc:
        return _err(exc)
    return JSONResponse({"linked": True}, status_code=201)


@router.post("/connect/lastfm/username")
async def link_lastfm_username(
    body: LinkRequest, res: Resources = Depends(get_resources)
) -> JSONResponse:  # noqa: B008
    try:
        await _orch(res).link_lastfm_username(body.user_id, body.platform, body.username or "")
    except ConnectError as exc:
        return _err(exc)
    return JSONResponse({"linked": True}, status_code=201)


@router.delete("/connections/{user_id}/{platform}", status_code=204)
async def unlink(
    user_id: UUID, platform: Platform, res: Resources = Depends(get_resources)
) -> JSONResponse:  # noqa: B008
    await _orch(res).unlink(user_id, platform)
    return JSONResponse(None, status_code=204)


@router.delete("/sources/{user_id}/{kind}", status_code=204)
async def remove_route(
    user_id: UUID, kind: SourceKind, res: Resources = Depends(get_resources)
) -> JSONResponse:
    """Consent withdrawal for one route (e.g. ``lastfm_link``): stop reading it at once."""
    from ..sources_store import delete_sources, get_source

    src = await get_source(res.engine, user_id, kind)
    if src is not None:
        await res.redis.zrem("poll:next", str(src.id))
        if kind is SourceKind.SPOTIFY:
            await _orch(res).purge_direct_spotify(user_id)
        await delete_sources(res.engine, user_id, [kind])
    return JSONResponse(None, status_code=204)


class PollRequest(BaseModel):
    flags: dict[str, bool] = Field(default_factory=dict)
    limit: int = Field(default=50, ge=1, le=200)


@router.post("/poll/due")
async def poll(body: PollRequest, res: Resources = Depends(get_resources)) -> JSONResponse:  # noqa: B008
    return JSONResponse(await poll_due(_orch(res), body.flags, body.limit))


# ---- YouTube Takeout import (JNG-01-06) ---------------------------------------------------


def _job_key(job_id: str) -> str:
    return f"import:{job_id}"


async def _run_import(res: Resources, job_id: str, user_id: UUID, path: str) -> None:
    status: dict[str, Any] = {"status": "processing", "imported": 0, "user_id": str(user_id)}
    try:
        plays = await asyncio.to_thread(sniff_and_parse, path)
        if not plays:
            raise TakeoutError("No YouTube Music plays were found in that file.")
        written = 0
        for i in range(0, len(plays), 500):
            chunk = plays[i : i + 500]
            events = await record_plays(
                res,
                user_id,
                chunk,
                kind=EventKind.LISTEN,
                route=EXPORT_ROUTE,
                via=Via.EXPORT,
                allow_remote=False,
            )
            written += len(events)
            status["imported"] = written
            await res.redis.set(_job_key(job_id), json.dumps(status), ex=IMPORT_TTL)
        await ensure_platform_connection(
            res.engine, user_id, Platform.YOUTUBE_MUSIC, SourceStatus.CONNECTED
        )
        status.update(status="done", imported=written, found=len(plays))
    except TakeoutError as exc:
        status.update(status="failed", error=str(exc))
    except Exception:  # noqa: BLE001 - never leak internals to the user
        log.exception("takeout import failed")
        status.update(status="failed", error="We couldn't read that file. Try exporting it again.")
    finally:
        try:
            os.remove(path)  # uploads are deleted right after parsing (NFR-SEC-07)
        except OSError:
            log.warning("could not delete a takeout upload")
    await res.redis.set(_job_key(job_id), json.dumps(status), ex=IMPORT_TTL)


@router.post("/imports/youtube", status_code=202)
async def import_youtube(
    user_id: UUID = Form(...),  # noqa: B008
    file: UploadFile = File(...),  # noqa: B008
    res: Resources = Depends(get_resources),  # noqa: B008
) -> JSONResponse:
    job_id = uuid4().hex
    fd, path = tempfile.mkstemp(prefix="takeout-", suffix=".upload")
    size = 0
    with os.fdopen(fd, "wb") as out:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            if size > MAX_BYTES:
                out.close()
                os.remove(path)
                return api_error(413, "FILE_TOO_LARGE", "That file is over 50 MB.")
            out.write(chunk)
    status = {"status": "queued", "imported": 0, "user_id": str(user_id)}
    await res.redis.set(_job_key(job_id), json.dumps(status), ex=IMPORT_TTL)
    task = asyncio.create_task(_run_import(res, job_id, user_id, path))
    res.background.add(task)
    task.add_done_callback(res.background.discard)
    return JSONResponse({"job_id": job_id, "status": "queued"}, status_code=202)


@router.get("/imports/{job_id}")
async def import_status(
    job_id: str, user_id: UUID, res: Resources = Depends(get_resources)
) -> JSONResponse:  # noqa: B008
    raw = await res.redis.get(_job_key(job_id[:64]))
    data = json.loads(raw) if raw else None
    if not data or data.get("user_id") != str(user_id):
        return api_error(404, "NOT_FOUND", "No such import.")
    data.pop("user_id", None)
    return JSONResponse(data)
