#!/bin/sh
set -e
case "$1" in
  api)
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput >/dev/null
    if [ "${JINGLE_DEMO:-0}" = "1" ] && python manage.py help seed_demo >/dev/null 2>&1; then
      python manage.py seed_demo || echo "seed_demo failed (continuing)"
    fi
    # WSGI + threads: every view is synchronous, and under ASGI Django serialised them onto one
    # thread per worker (~2 requests at a time). Load test 2026-10: 59 req/s ceiling, p95 12 s.
    exec gunicorn core_api.wsgi:application -k gthread \
      -b 0.0.0.0:8000 --workers "${WEB_CONCURRENCY:-4}" --threads "${WEB_THREADS:-8}" \
      --timeout 30 --graceful-timeout 20 --keep-alive 5 --access-logfile -
    ;;
  worker)
    exec celery -A core_api worker -Q poll,ingest,ml,notify,default -c "${WORKER_CONCURRENCY:-2}" -l info
    ;;
  beat)
    exec celery -A core_api beat -l info
    ;;
  *)
    exec "$@"
    ;;
esac
