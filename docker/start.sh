#!/bin/sh
set -e

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Running migrations..."
python manage.py migrate --noinput
log "Migrations complete."

# ─── Seed dev users (opt-in via ALLOW_SETUP_ADMIN=true) ───────────────────────
if [ "${ALLOW_SETUP_ADMIN:-false}" = "true" ]; then
  log "Seeding dev users (ALLOW_SETUP_ADMIN=true)..."
  python manage.py setup_admin
  log "Dev user seeding complete."
else
  log "Skipping dev user seeding (ALLOW_SETUP_ADMIN not set)."
fi

# ─── Start server ─────────────────────────────────────────────────────────────
log "Starting gunicorn..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8001 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-30}"
