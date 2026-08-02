#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
python scripts/prestart.py --mode review
exec uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --proxy-headers \
  --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}" \
  --timeout-keep-alive "${UMOJA_KEEP_ALIVE_SECONDS:-5}" \
  --timeout-graceful-shutdown "${UMOJA_GRACEFUL_SHUTDOWN_SECONDS:-30}" \
  --limit-concurrency "${UMOJA_LIMIT_CONCURRENCY:-1000}" \
  --backlog "${UMOJA_BACKLOG:-2048}"
