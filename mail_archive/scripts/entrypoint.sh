#!/usr/bin/env bash
set -euo pipefail
cmd=${1:-web}
shift || true

python manage.py migrate --noinput
python manage.py check --deploy

case "$cmd" in
  web)
    exec gunicorn mail_archive.wsgi:application \
      --bind 0.0.0.0:8000 \
      --workers ${GUNICORN_WORKERS:-4} \
      --threads ${GUNICORN_THREADS:-2} \
      --timeout ${GUNICORN_TIMEOUT:-120}
    ;;
  celery-worker)
    exec celery -A mail_archive worker -l info
    ;;
  celery-beat)
    exec celery -A mail_archive beat -l info
    ;;
  *)
    exec "$cmd" "$@"
    ;;
esac
