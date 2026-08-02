#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

./scripts/vps-preflight.sh
COMPOSE=(docker compose -f docker-compose.production.yml)

# Rebuild release images without stale layers. This prevents an older tagged
# application image from surviving an upgrade and reintroducing old migrations.
"${COMPOSE[@]}" build --pull --no-cache app transcription

# Start dependencies, then run controlled prestart once as a deployment job.
"${COMPOSE[@]}" up -d db transcription
for _ in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T db pg_isready -U "${POSTGRES_USER:-umoja}" -d "${POSTGRES_DB:-umoja_afya}" >/dev/null 2>&1; then break; fi
  sleep 2
done
"${COMPOSE[@]}" run --rm app python scripts/prestart.py --mode production

"${COMPOSE[@]}" up -d --force-recreate app proxy --remove-orphans

echo "Waiting for application readiness..."
for _ in $(seq 1 90); do
  if "${COMPOSE[@]}" exec -T app python - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=3)
PY
  then
    "${COMPOSE[@]}" ps
    echo "Umoja Afya is ready."
    exit 0
  fi
  sleep 3
done

"${COMPOSE[@]}" logs --tail=250 app proxy db transcription >&2
exit 1
