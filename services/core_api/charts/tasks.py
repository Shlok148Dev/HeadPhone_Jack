from celery import shared_task

from . import services


@shared_task
def refresh() -> int:
    """Hourly: fold new listens into weekly chart rows (D-CHART-03)."""
    return services.refresh_active()
