"""Ritual jobs on the default queue."""

from celery import shared_task

from . import services


@shared_task(ignore_result=True, soft_time_limit=50)
def close_due() -> int:
    return services.close_due()


@shared_task(ignore_result=True, soft_time_limit=1800)
def make_recaps() -> int:
    return services.make_recaps()
