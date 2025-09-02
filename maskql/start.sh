#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT_HTTP="${PORT_HTTP:-8081}"
APP="${APP:-maskql.app:app}"
TEST_ENV="${TEST_ENV:-false}"

SEED_FLAG=""
if [ "$TEST_ENV" = true ]; then
    SEED_FLAG="-x seed=test"
fi

echo "[MaskQL] Migrate Database"
if cd maskql 2>/dev/null; then
    alembic $SEED_FLAG upgrade head || echo "[MaskQL] Alembic migration skipped/failed (continuing)"
    cd - >/dev/null || true
else
    echo "[MaskQL] 'maskql' dir not found; skipping migrations"
fi

echo "[MaskQL] Starting HTTP on ${HOST}:${PORT_HTTP}"
exec uvicorn "$APP" \
    --host "$HOST" \
    --port "$PORT_HTTP" \
    --loop uvloop \
    --http h11 \
    --proxy-headers \
    --forwarded-allow-ips="*"
