#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT_HTTP="${PORT_HTTP:-8081}"
PORT_HTTPS="${PORT_HTTPS:-8443}"
APP="${APP:-maskql.app:app}"

echo "[MaskQL] Migrate Database"
cd maskql
alembic upgrade head || exit 1
cd ..

if [[ -n "${TLS_CERT:-}" && -n "${TLS_KEY:-}" && -f "${TLS_CERT}" && -f "${TLS_KEY}" ]]; then
    echo "[MaskQL] Starting HTTPS on :${PORT_HTTPS}"
    uvicorn "$APP" --host "$HOST" --port "$PORT_HTTPS" \
        --loop uvloop --http h11 \
        --ssl-certfile "$TLS_CERT" --ssl-keyfile "$TLS_KEY" \
        --access-log --log-level info &

    echo "[MaskQL] Starting HTTP on :${PORT_HTTP}"
    uvicorn "$APP" --host "$HOST" --port "$PORT_HTTP" \
        --loop uvloop --http h11 \
        --access-log --log-level info &

    wait -n || true
    
    pkill -TERM -f "uvicorn $APP" || true
    wait || true
else
    echo "[MaskQL] TLS cert/key not found, starting HTTP on :${PORT_HTTP}"
    exec uvicorn "$APP" --host "$HOST" --port "$PORT_HTTP" \
        --loop uvloop --http h11 \
        --access-log --log-level info
fi
