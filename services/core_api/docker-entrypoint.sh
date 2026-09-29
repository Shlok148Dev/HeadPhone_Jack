#!/bin/sh
set -e
case "$1" in
  api)
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput >/dev/null
    if [ "${JINGLE_DEMO:-0}" = "1" ] && python manage.py help seed_demo >/dev/null 2>&1; then
      python manage.py seed_demo || echo "seed_demo failed (continuing)"
    fi
    exec gunicorn core_api.asgi:application -k uvicorn.workers.UvicornWorker \
      -b 0.0.0.0:8000 --workers "${WEB_CONCURRENCY:-2}" --access-logfile -
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
