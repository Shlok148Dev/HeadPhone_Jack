"""Run logging (jingle-ml-job skill): MLflow when configured, else JSON under artifacts/ml/."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

log = logging.getLogger(__name__)


def log_run(job: str, params: dict, metrics: dict) -> None:
    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if uri:
        try:
            import mlflow

            mlflow.set_tracking_uri(uri)
            with mlflow.start_run(run_name=job):
                mlflow.log_params(params)
                mlflow.log_metrics({k: float(v) for k, v in metrics.items()})
            return
        except Exception:  # noqa: BLE001
            log.warning("mlflow logging failed; falling back to JSON")
    try:
        out = Path(os.environ.get("ML_ARTIFACTS_DIR", "artifacts/ml")) / job
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{int(time.time())}.json").write_text(
            json.dumps({"params": params, "metrics": metrics})
        )
    except OSError:
        log.info("ml run %s: %s %s", job, params, metrics)
