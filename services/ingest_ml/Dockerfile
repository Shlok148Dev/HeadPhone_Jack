# syntax=docker/dockerfile:1.7
# Build context: repository root.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy     UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /repo/services/ingest_ml
COPY packages/py-common /repo/packages/py-common
COPY services/ingest_ml/pyproject.toml services/ingest_ml/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY services/ingest_ml ./
RUN useradd -r -u 10001 jingle && chown -R jingle /repo
USER jingle
EXPOSE 8001
HEALTHCHECK --interval=10s --timeout=3s --retries=18 CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/healthz').status==200 else 1)"
CMD ["uvicorn", "ingest_ml.main:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers"]
