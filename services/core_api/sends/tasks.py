"""Send status jobs (JNG-06-04, JNG-06-05). Run on the default queue."""

from celery import shared_task

from . import services


@shared_task(ignore_result=True, soft_time_limit=50)
def check_played() -> int:
    return services.check_played()


@shared_task(ignore_result=True, soft_time_limit=600)
def discovery_credits() -> int:
    return services.discovery_credits()
