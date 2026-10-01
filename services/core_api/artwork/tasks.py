"""Rate-limited artwork resolution (default queue)."""

from celery import shared_task

from . import services


@shared_task(ignore_result=True, soft_time_limit=55)
def drain() -> int:
    return services.drain()
