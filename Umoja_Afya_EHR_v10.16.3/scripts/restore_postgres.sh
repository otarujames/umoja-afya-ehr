#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
compose_file="${COMPOSE_FILE:-docker-compose.production.yml}"
backup="${1:?Usage: restore_postgres.sh backup.dump}"
[ -f "$backup" ] || { echo "Backup not found: $backup" >&2; exit 2; }

if [ -f "$backup.sha256" ]; then
  sha256sum -c "$backup.sha256"
fi

cat "$backup" | docker compose -f "$compose_file" exec -T db \
  pg_restore --clean --if-exists --no-owner --no-acl \
  -U "${POSTGRES_USER:-umoja}" -d "${POSTGRES_DB:-umoja_afya}"
