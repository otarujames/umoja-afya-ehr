#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

secret_file="secrets/postgres_password"
[ -s "$secret_file" ] || { echo "Missing $secret_file" >&2; exit 2; }
command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 2; }

new_password="$(openssl rand -hex 32)"
db_user="${POSTGRES_USER:-umoja}"

# Run the role change through the local database socket inside the container.
docker compose -f docker-compose.production.yml exec -T db \
  psql -v ON_ERROR_STOP=1 -U "$db_user" -d "${POSTGRES_DB:-umoja_afya}" \
  -c "ALTER ROLE \"$db_user\" WITH PASSWORD '$new_password';"

umask 077
printf '%s\n' "$new_password" > "${secret_file}.new"
chmod 600 "${secret_file}.new"
mv "${secret_file}.new" "$secret_file"
docker compose -f docker-compose.production.yml restart app

echo "Database password rotated and application restarted."
