#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT_HTTP="${PORT_HTTP:-8081}"
APP="${APP:-maskql.app:app}"
TEST_ENV="${TEST_ENV:-false}"
RETRIES="${RETRIES:-20}"
SLEEP_SECS="${SLEEP_SECS:-3}"
FAIL_FAST="${FAIL_FAST:-false}"
UVICORN_RELOAD="${UVICORN_RELOAD:-false}"
RELOAD_DIR="${RELOAD_DIR:-/app/maskql}"
LOG_TS() { printf '[%s] ' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"; }

SEED_FLAG=""
if [ "$TEST_ENV" = true ]; then
    SEED_FLAG="-x seed=test"
fi

LOG_TS; echo "[MaskQL] Running DB migrations (retry up to ${RETRIES}x)"
if cd maskql 2>/dev/null; then
    n=0
    until alembic $SEED_FLAG upgrade head; do
        n=$((n+1))
        if [ "$FAIL_FAST" = "true" ]; then
        LOG_TS; echo "[MaskQL] Alembic migration failed (fail-fast)."; exit 1
        fi
        if [ "$n" -ge "$RETRIES" ]; then
        LOG_TS; echo "[MaskQL] Alembic migration failed after ${RETRIES} retries. Exiting."
        exit 1
        fi
        LOG_TS; echo "[MaskQL] Migration not ready (try ${n}/${RETRIES}). Waiting ${SLEEP_SECS}s..."
        sleep "${SLEEP_SECS}"
    done
    cd - >/dev/null || true
else
    LOG_TS; echo "[MaskQL] 'maskql' dir not found; skipping migrations"
fi

LOG_TS; echo "[MaskQL] Starting HTTP ${HOST}:${PORT_HTTP}"
UVICORN_ARGS=(
    --host "$HOST"
    --port "$PORT_HTTP"
    --loop uvloop
    --http h11
    --proxy-headers
    --forwarded-allow-ips="*"
)

if [ "$UVICORN_RELOAD" = "true" ]; then
    LOG_TS; echo "[MaskQL] Uvicorn reload enabled for ${RELOAD_DIR}"
    UVICORN_ARGS+=(--reload --reload-dir "$RELOAD_DIR")
fi

_term() {
    LOG_TS; echo "[MaskQL] Caught SIGTERM, shutting down…"
}
trap _term TERM INT

exec uvicorn "$APP" "${UVICORN_ARGS[@]}"
