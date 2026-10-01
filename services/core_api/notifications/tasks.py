"""Web push delivery on the notify queue."""

from celery import shared_task

from . import services


@shared_task(queue="notify", ignore_result=True, soft_time_limit=30)
def push(notification_id: str) -> int:
    return services.send_push(notification_id)
