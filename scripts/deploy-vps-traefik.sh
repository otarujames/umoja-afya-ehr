#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

fail(){ echo "ERROR: $*" >&2; exit 2; }
[ -f .env ] || fail ".env is missing; run ./scripts/init-production.sh first."
command -v curl >/dev/null 2>&1 || fail "curl is required for the public HTTPS readiness check."

set -a
# .env is a root-managed deployment file created by init-production.sh.
. ./.env
set +a

export UMOJA_USE_TRAEFIK=true
TRAEFIK_CONTAINER="${TRAEFIK_CONTAINER:-traefik-59qx-traefik-1}"
TRAEFIK_NETWORK="${TRAEFIK_NETWORK:-traefik}"
UMOJA_PUBLIC_HOST="${UMOJA_PUBLIC_HOST:-umojaehr.online}"
PROJECT="umoja-afya-ehr"

[ "$UMOJA_PUBLIC_HOST" = "umojaehr.online" ] || fail "UMOJA_PUBLIC_HOST must be umojaehr.online for this VPS release."
[ "$(docker inspect -f '{{.State.Running}}' "$TRAEFIK_CONTAINER" 2>/dev/null || true)" = "true" ] || fail "Traefik container $TRAEFIK_CONTAINER is not running."

network_mode="$(docker inspect -f '{{.HostConfig.NetworkMode}}' "$TRAEFIK_CONTAINER")"
if [ "$network_mode" != "host" ]; then
  docker inspect -f '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}}{{"\n"}}{{end}}' "$TRAEFIK_CONTAINER" | grep -Fxq "$TRAEFIK_NETWORK" \
    || fail "Traefik is not in host mode and is not attached to Docker network $TRAEFIK_NETWORK."
fi
docker network inspect "$TRAEFIK_NETWORK" >/dev/null 2>&1 || docker network create "$TRAEFIK_NETWORK" >/dev/null

./scripts/vps-preflight.sh

COMPOSE=(
  docker compose
  --project-name "$PROJECT"
  -f docker-compose.production.yml
  -f docker-compose.traefik.yml
)

"${COMPOSE[@]}" config --quiet
"${COMPOSE[@]}" build --pull app transcription
"${COMPOSE[@]}" up -d db transcription

for _ in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T db pg_isready -U "${POSTGRES_USER:-umoja}" -d "${POSTGRES_DB:-umoja_afya}" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

"${COMPOSE[@]}" run --rm app python scripts/prestart.py --mode production
"${COMPOSE[@]}" up -d --force-recreate --remove-orphans app

echo "Waiting for Umoja Afya application readiness..."
for _ in $(seq 1 90); do
  if "${COMPOSE[@]}" exec -T app python - <<'PY' >/dev/null 2>&1
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=3)
PY
  then
    break
  fi
  sleep 3
done

"${COMPOSE[@]}" exec -T app python - <<'PY' >/dev/null 2>&1 || {
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=5)
PY
  "${COMPOSE[@]}" logs --tail=250 app db transcription >&2
  fail "The application did not become ready."
}

for _ in $(seq 1 30); do
  if curl -fsS --max-time 10 "https://${UMOJA_PUBLIC_HOST}/api/v1/health" >/dev/null; then
    "${COMPOSE[@]}" ps
    echo "Umoja Afya 11.0.0 is live at https://${UMOJA_PUBLIC_HOST}/"
    echo "Initial account credentials are stored in secrets/preloaded_users.json."
    exit 0
  fi
  sleep 3
done

docker logs --tail=200 "$TRAEFIK_CONTAINER" >&2 || true
"${COMPOSE[@]}" logs --tail=250 app >&2
fail "The application is healthy internally but https://${UMOJA_PUBLIC_HOST}/ did not resolve through Traefik."
