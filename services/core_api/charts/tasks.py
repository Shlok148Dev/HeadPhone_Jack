from celery import shared_task

from . import services


@shared_task
def refresh() -> int:
    """Hourly: fold new listens into weekly chart rows (D-CHART-03)."""
    return services.refresh_active()


@shared_task
def freeze() -> int:
    """Hourly: freeze last week's chart once Monday 06:00 local has passed (D-CHART-05)."""
    return services.freeze_due()
