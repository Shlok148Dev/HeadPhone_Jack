"""Monthly F_pairs recalibration (Technical Bible 6.1)."""

from celery import shared_task

from . import compute


@shared_task(ignore_result=True, soft_time_limit=1800)
def recalibrate() -> int:
    return compute.recalibrate()
