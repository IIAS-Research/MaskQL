#!/usr/bin/env bash
set -euo pipefail

HOST="0.0.0.0"
PORT_HTTP=8081
PORT_HTTPS=8443

if [[ -f "${TLS_CERT}" && -f "${TLS_KEY}" ]]; then
    echo "[MaskQL] Starting with TLS on :${PORT_HTTPS}"
    exec uvicorn maskql.app:app --host "$HOST" --port "$PORT_HTTPS" \
        --loop uvloop --http h11 \
        --ssl-certfile "$TLS_CERT" --ssl-keyfile "$TLS_KEY"
else
    echo "[MaskQL] TLS cert/key not found, starting HTTP on :${PORT_HTTP}"
    exec uvicorn maskql.app:app --host "$HOST" --port "$PORT_HTTP" --loop uvloop --http h11
fi