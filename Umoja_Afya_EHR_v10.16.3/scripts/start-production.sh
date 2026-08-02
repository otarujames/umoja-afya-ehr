#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
python scripts/prestart.py --mode production
exec uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-4}" \
  --proxy-headers \
  --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}" \
  --timeout-keep-alive "${UMOJA_KEEP_ALIVE_SECONDS:-5}" \
  --timeout-graceful-shutdown "${UMOJA_GRACEFUL_SHUTDOWN_SECONDS:-45}" \
  --limit-concurrency "${UMOJA_LIMIT_CONCURRENCY:-2000}" \
  --backlog "${UMOJA_BACKLOG:-4096}" \
  --no-server-header
