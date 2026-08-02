#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
compose_file="${COMPOSE_FILE:-docker-compose.production.yml}"
backup_dir="${BACKUP_DIR:-./backups}"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="$backup_dir/umoja_afya_${stamp}.dump"

docker compose -f "$compose_file" exec -T db \
  pg_dump --format=custom --no-owner --no-acl \
  -U "${POSTGRES_USER:-umoja}" -d "${POSTGRES_DB:-umoja_afya}" > "$file"
sha256sum "$file" > "$file.sha256"
chmod 600 "$file" "$file.sha256"
printf '%s\n' "$file"
