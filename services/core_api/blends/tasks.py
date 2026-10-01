"""Blend jobs (default queue)."""

from celery import shared_task

from . import services
from .models import Blend


@shared_task(ignore_result=True, soft_time_limit=120)
def regenerate(blend_id: str) -> int:
    b = Blend.objects.filter(pk=blend_id).first()
    return len(services.generate(b)) if b else 0
