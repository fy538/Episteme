#!/bin/sh
set -e

echo "Starting Episteme backend..."

# Run database migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Start gunicorn with optimized settings for Fly.io
echo "Starting gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 1 \
  --worker-class sync \
  --timeout 300 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --log-level info \
  --access-logfile - \
  --error-logfile -
