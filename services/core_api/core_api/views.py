from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """Liveness + DB readiness for Compose health checks."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        db = "ok"
    except Exception:  # noqa: BLE001
        db = "down"
    return JsonResponse({"status": "ok" if db == "ok" else "degraded", "db": db}, status=200 if db == "ok" else 503)
