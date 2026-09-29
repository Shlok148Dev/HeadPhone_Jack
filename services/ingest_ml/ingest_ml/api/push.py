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

MAX_BODY_BYTES = 10 * 1024 * 1024


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


async def _authorize(
    res: Resources, authorization: str | None
) -> tuple[TokenPrincipal, BucketResult]:
    token = parse_token_header(authorization)
    if token is None:
        raise _Rejected(lb_error(401, "You need to provide an Authorization header."))
    principal = await lookup_token(res.engine, token)
    if principal is None:
        raise _Rejected(lb_error(401, "Invalid authorization token."))
    bucket = await res.push_bucket.take(f"rl:push:{principal.token_id}")
    if not bucket.allowed:
        headers = bucket.headers() | {"Retry-After": str(max(1, round(bucket.retry_after)))}
        raise _Rejected(lb_error(429, "Rate limit exceeded.", headers))
    return principal, bucket


async def _read_json(request: Request) -> Any:
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise _Rejected(lb_error(400, "Payload too large."))
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
        principal, bucket = await _authorize(res, authorization)
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
        principal, bucket = await _authorize(res, authorization)
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
    authorization: str | None = Header(default=None),
    res: Resources = Depends(get_resources),  # noqa: B008
) -> JSONResponse:
    token = parse_token_header(authorization)
    if token is None:
        return lb_error(400, "You need to provide an Authorization header.")
    principal = await lookup_token(res.engine, token)
    if principal is None:
        return JSONResponse({"code": 200, "message": "Token invalid.", "valid": False})
    return JSONResponse(
        {
            "code": 200,
            "message": "Token valid.",
            "valid": True,
            # ingest-ml has no usernames (users mirror is id-only); the user id identifies them.
            "user_name": str(principal.user_id),
        }
    )
