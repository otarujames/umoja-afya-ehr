#!/usr/bin/env sh
set -eu
COMPOSE_FILE="${1:-docker-compose.review.yml}"
RESET="${2:-}"
docker compose -f "$COMPOSE_FILE" exec app python scripts/repair_admin_access.py $RESET
echo "Administrator access repair completed. Sign out and sign in again."
