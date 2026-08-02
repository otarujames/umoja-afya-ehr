#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
compose_file="${1:-docker-compose.production.yml}"

echo "== Compose validation =="
docker compose -f "$compose_file" config >/dev/null && echo "Compose configuration: OK" || exit 1

echo "== Container status =="
docker compose -f "$compose_file" ps

echo "== Readiness =="
docker compose -f "$compose_file" exec -T app python - <<'PY' || true
import urllib.request
try:
    print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=5).read().decode())
except Exception as exc:
    print(f"Readiness failed: {exc}")
PY

echo "== Transcription readiness =="
docker compose -f "$compose_file" exec -T transcription curl -fsS http://127.0.0.1:8090/health/ready || true

echo "== Recent service logs =="
docker compose -f "$compose_file" logs --tail=100 app db transcription proxy
