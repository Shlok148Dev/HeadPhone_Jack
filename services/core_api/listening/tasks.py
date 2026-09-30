"""Session upkeep (JNG-07-08): hand over from a host who dropped off; end empty rooms."""

from celery import shared_task

from . import services


@shared_task(ignore_result=True, soft_time_limit=25)
def sweep() -> dict:
    return services.sweep()
