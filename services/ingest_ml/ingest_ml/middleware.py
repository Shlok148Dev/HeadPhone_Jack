"""Request-ID propagation and access logging (CONTRACTS.md §8; NFR-OBS-04).

Pure ASGI so the context variable is visible to every handler. Access logs carry method, path
and status only: never headers, bodies or query strings (tokens must never reach logs).
"""

import logging
import re
import time
import uuid
from collections.abc import MutableMapping
from typing import Any

from jingle_common.logging import request_id_var
from starlette.types import ASGIApp, Message, Receive, Scope, Send

log = logging.getLogger("ingest_ml.access")

_VALID_ID = re.compile(r"^[A-Za-z0-9._\-]{1,128}$")
HEADER = b"x-request-id"


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope.get("headers") or []).get(HEADER, b"").decode("latin-1")
        rid = incoming if _VALID_ID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(rid)
        status = 500
        started = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
                headers: list[Any] = list(message.get("headers", []))
                headers.append((HEADER, rid.encode()))
                msg: MutableMapping[str, Any] = dict(message)
                msg["headers"] = headers
                message = msg
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            log.info(
                "%s %s %s %.1fms",
                scope.get("method"),
                scope.get("path"),
                status,
                (time.perf_counter() - started) * 1000,
            )
            request_id_var.reset(token)
