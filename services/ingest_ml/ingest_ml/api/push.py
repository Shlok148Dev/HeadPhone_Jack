"""Public ListenBrainz-compatible push API: ``/ingest/1/*`` (ADR-0003).

Errors use ListenBrainz's shape ``{"code": <status>, "error": "<message>"}``.
"""

import json
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from ..auth import TokenPrincipal, lookup_token, parse_token_header
from ..push.schemas import Submission
from ..push.service import PushRejected, ingest_submission
from ..ratelimit import BucketResult
from ..resources import Resources, get_resources

router = APIRouter(prefix="/ingest/1", tags=["push"])

MAX_BODY_BYTES = 2 * 1024 * 1024  # the edge (Caddy) enforces the same cap


def lb_error(status: int, message: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse({"code": status, "error": message}, status_code=status, headers=headers)


def _validation_message(exc: ValidationError) -> str:
    err = exc.errors()[0]
    loc = ".".join(str(p) for p in err.get("loc", ()) if p != "__root__")
    msg = str(err.get("msg", "invalid")).removeprefix("Value error, ")
    return f"{loc}: {msg}" if loc else msg


class _Rejected(Exception):
    def __init__(self, response: JSONResponse) -> None:
        self.response = response


def client_ip(request: Request) -> str:
    """Caddy is the only ingress and appends the peer address to X-Forwarded-For."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[-1].strip() or "unknown"
    return request.client.host if request.client else "unknown"


async def _principal_or_reject(
    res: Resources, request: Request, authorization: str | None, *, missing_status: int = 401
) -> TokenPrincipal:
    """Resolve the token; failed attempts are limited per client IP before any DB lookup."""
    ip_key = f"rl:push:ip:{client_ip(request)}"
    gate = await res.auth_fail_bucket.take(ip_key, cost=0)
    if not gate.allowed:
        headers = {"Retry-After": str(max(1, round(gate.retry_after)))}
        raise _Rejected(lb_error(429, "Too many failed attempts.", headers))
    token = parse_token_header(authorization)
    if token is None:
        raise _Rejected(lb_error(missing_status, "You need to provide an Authorization header."))
    principal = await lookup_token(res.engine, token)
    if principal is None:
        await res.auth_fail_bucket.take(ip_key, force=True)
        raise _Rejected(lb_error(401, "Invalid authorization token."))
    return principal


async def _authorize(
    res: Resources, request: Request, authorization: str | None
) -> tuple[TokenPrincipal, BucketResult]:
    principal = await _principal_or_reject(res, request, authorization)
    bucket = await res.push_bucket.take(f"rl:push:user:{principal.user_id}")
    if not bucket.allowed:
        headers = bucket.headers() | {"Retry-After": str(max(1, round(bucket.retry_after)))}
        raise _Rejected(lb_error(429, "Rate limit exceeded.", headers))
    return principal, bucket


async def _read_json(request: Request) -> Any:
    too_large = _Rejected(lb_error(413, "Payload too large."))
    declared = request.headers.get("content-length")
    if declared is not None and (not declared.isdigit() or int(declared) > MAX_BODY_BYTES):
        raise too_large
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            raise too_large
        chunks.append(chunk)
    body = b"".join(chunks)
    try:
        return json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise _Rejected(lb_error(400, "Cannot parse JSON document.")) from None


async def _submit(res: Resources, principal: TokenPrincipal, bucket: BucketResult,
                  data: Any) -> JSONResponse:
    try:
        sub = Submission.model_validate(data)
    except ValidationError as exc:
        return lb_error(400, _validation_message(exc), bucket.headers())
    listens = await res.listen_bucket.take(
        f"rl:listens:user:{principal.user_id}", len(sub.payload)
    )
    if not listens.allowed:
        headers = bucket.headers() | {"Retry-After": str(max(1, round(listens.retry_after)))}
        return lb_error(429, "Listen budget exceeded.", headers)
    try:
        await ingest_submission(res, principal.user_id, sub)
    except PushRejected as exc:
        return lb_error(400, str(exc), bucket.headers())
    return JSONResponse({"status": "ok"}, headers=bucket.headers())


@router.post("/submit-listens")
async def submit_listens(
    request: Request,
    authorization: str | None = Header(default=None),
    res: Resources = Depends(get_resources),  # noqa: B008
) -> JSONResponse:
    try:
        principal, bucket = await _authorize(res, request, authorization)
        data = await _read_json(request)
    except _Rejected as r:
        return r.response
    return await _submit(res, principal, bucket, data)


@router.post("/playing-now")
async def playing_now(
    request: Request,
    authorization: str | None = Header(default=None),
    res: Resources = Depends(get_resources),  # noqa: B008
) -> JSONResponse:
    """Convenience alias: body is one ``track_metadata`` object (or ``{"track_metadata": …}``)."""
    try:
        principal, bucket = await _authorize(res, request, authorization)
        data = await _read_json(request)
    except _Rejected as r:
        return r.response
    if isinstance(data, dict) and "track_metadata" in data:
        data = data["track_metadata"]
    return await _submit(
        res, principal, bucket,
        {"listen_type": "playing_now", "payload": [{"track_metadata": data}]},
    )


@router.get("/validate-token")
async def validate_token(
    request: Request,
    authorization: str | None = Header(default=None),
    res: Resources = Depends(get_resources),  # noqa: B008
) -> JSONResponse:
    try:
        principal = await _principal_or_reject(res, request, authorization, missing_status=400)
    except _Rejected as r:
        if r.response.status_code == 401:  # ListenBrainz answers an invalid token with 200
            return JSONResponse({"code": 200, "message": "Token invalid.", "valid": False})
        return r.response
    return JSONResponse(
        {
            "code": 200,
            "message": "Token valid.",
            "valid": True,
            "user_name": principal.username or "",
        }
    )
