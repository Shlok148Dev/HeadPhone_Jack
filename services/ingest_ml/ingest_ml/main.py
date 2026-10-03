"""Jingle ingest-ml: adapters, Connection Orchestrator, push endpoint, identity resolver."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from jingle_common.logging import configure, request_id_var

from .api import connect, internal, push
from .middleware import RequestIdMiddleware
from .resources import Resources
from .settings import Settings, settings
from .stores import ensure_mongo_indexes

configure("ingest-ml")
log = logging.getLogger(__name__)


def create_app(resources: Resources | None = None, app_settings: Settings | None = None) -> FastAPI:
    cfg = app_settings or settings

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = resources is None
        res = resources or Resources.build(cfg)
        app.state.resources = res
        if owned:
            try:
                await ensure_mongo_indexes(res.mongo)
            except Exception:
                log.exception("could not ensure mongo indexes; /internal/healthz will report it")
        try:
            yield
        finally:
            if owned:
                await res.close()

    app = FastAPI(title="Jingle ingest-ml", version="0.1.0", lifespan=lifespan)
    if resources is not None:
        app.state.resources = resources
    app.add_middleware(RequestIdMiddleware)
    app.include_router(push.router)
    app.include_router(connect.router)
    app.include_router(internal.router)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        if request.url.path.startswith("/ingest/1/"):
            return JSONResponse(
                {"code": exc.status_code, "error": str(exc.detail)}, status_code=exc.status_code
            )
        code = exc.detail if isinstance(exc.detail, str) and exc.detail.isupper() else "HTTP_ERROR"
        return JSONResponse(
            {
                "error": {
                    "code": code,
                    "message": str(exc.detail),
                    "details": {},
                    "request_id": request_id_var.get(),
                }
            },
            status_code=exc.status_code,
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
