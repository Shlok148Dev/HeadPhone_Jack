"""One Celery app, five queues (Tech Bible 7.4, ADR-0012)."""

import os

from celery import Celery
from kombu import Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core_api.settings")

app = Celery("jingle")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.task_queues = [Queue(q) for q in ("poll", "ingest", "ml", "notify", "default")]
app.conf.task_default_queue = "default"
app.conf.timezone = "Asia/Kolkata"
app.autodiscover_tasks()
app.autodiscover_tasks(['jingle_ml'], related_name='tasks', force=False)
