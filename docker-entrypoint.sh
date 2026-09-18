#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py run_email_otp_cleanup &

exec gunicorn --chdir backend config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --access-logfile - \
  --error-logfile -
