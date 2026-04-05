#!/bin/sh
set -e

TIMEOUT="${TIMEOUT:-30}"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

wait_for_service() {
  SERVICE="$1"
  shift

  log "Waiting for ${SERVICE} (timeout: ${TIMEOUT}s)..."
  COUNT=0
  until "$@" >/dev/null 2>&1; do
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge "$TIMEOUT" ]; then
      log "ERROR: ${SERVICE} not ready after ${TIMEOUT}s. Aborting."
      exit 1
    fi
    sleep 1
  done
  log "${SERVICE} is ready."
}

wait_for_service \
  "PostgreSQL at ${DB_HOST}:${DB_PORT}" \
  pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"

exec "$@"
