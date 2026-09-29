# syntax=docker/dockerfile:1.7
# Build context: repository root. Paths mirror the repo so uv.lock's relative path to py-common holds.
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy     UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /repo/services/core_api
COPY packages/py-common /repo/packages/py-common
COPY services/core_api/pyproject.toml services/core_api/uv.lock ./

FROM base AS api
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY services/core_api ./
RUN chmod +x docker-entrypoint.sh && useradd -r -u 10001 jingle && chown -R jingle /repo
USER jingle
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=18 CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["api"]

FROM base AS worker
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project --extra ml
COPY services/core_api ./
RUN chmod +x docker-entrypoint.sh && useradd -r -u 10001 jingle && chown -R jingle /repo
USER jingle
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["worker"]
