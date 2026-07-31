#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

fail(){ echo "ERROR: $*" >&2; exit 2; }
command -v docker >/dev/null 2>&1 || fail "Docker is not installed."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is unavailable."
[ -f .env ] || fail ".env is missing; run scripts/init-production.sh and edit it."
for f in secrets/postgres_password secrets/security_secret secrets/bootstrap_token secrets/preloaded_users.json; do
  [ -s "$f" ] || fail "$f is missing or empty."
done
for f in deploy/tls/fullchain.pem deploy/tls/privkey.pem; do
  [ -s "$f" ] || fail "$f is missing or empty."
done
python scripts/check_migrations.py

docker compose -f docker-compose.production.yml config >/dev/null
free_kb=$(df -Pk . | awk 'NR==2 {print $4}')
[ "$free_kb" -ge 5242880 ] || fail "At least 5 GB free disk space is required."
for port in 80 443; do
  if command -v ss >/dev/null 2>&1 && ss -ltn "sport = :$port" | grep -q LISTEN; then
    echo "WARNING: TCP port $port is already in use."
  fi
done
echo "VPS preflight passed."
