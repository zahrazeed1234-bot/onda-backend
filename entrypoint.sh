#!/bin/bash
set -e

DB_ENGINE="${DB_ENGINE:-postgresql}"
echo "[GMAO-CNS] DB_ENGINE=$DB_ENGINE"

if [ "$DB_ENGINE" != "sqlite" ]; then
  echo "[GMAO-CNS] Waiting for PostgreSQL ($DB_HOST:$DB_PORT)..."
  for i in $(seq 1 60); do
    if PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" 2>/dev/null; then
      echo "[GMAO-CNS] PostgreSQL ready."
      break
    fi
    echo "[GMAO-CNS] Waiting for postgres... ($i/60)"
    sleep 1
  done
else
  echo "[GMAO-CNS] SQLite mode - skipping PostgreSQL wait."
fi

echo "[GMAO-CNS] Running migrations..."
python manage.py makemigrations accounts equipment tickets audit || true
python manage.py migrate --noinput

echo "[GMAO-CNS] Collecting static files..."
python manage.py collectstatic --noinput --clear || true

echo "[GMAO-CNS] Loading demo data (seed)..."
python manage.py seed_demo --reset || true
python manage.py seed_demo || echo "[GMAO-CNS] (warning) seed command returned non-zero."

echo "[GMAO-CNS] Ensuring admin_cns is superuser..."
python - <<'PY'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from accounts.models import User
User.objects.filter(username='admin_cns').update(is_superuser=True, is_staff=True)
PY

PORT="${PORT:-8000}"
echo "[GMAO-CNS] Starting Django server (0.0.0.0:$PORT)..."
exec python manage.py runserver 0.0.0.0:$PORT
