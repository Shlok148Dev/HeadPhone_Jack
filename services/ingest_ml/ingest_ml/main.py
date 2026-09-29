from fastapi import FastAPI

from jingle_common.logging import configure

configure("ingest-ml")

app = FastAPI(title="Jingle ingest-ml", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
