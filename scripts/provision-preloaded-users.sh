#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
mkdir -p secrets
chmod 700 secrets
python scripts/generate_preloaded_users.py --output secrets/preloaded_users.json
chmod 600 secrets/preloaded_users.json
COMPOSE_FILE="${1:-docker-compose.production.yml}"
docker compose -f "$COMPOSE_FILE" up -d --build app
docker compose -f "$COMPOSE_FILE" exec app python scripts/preload_users.py
echo "Provisioning complete. Deployment-generated initial credentials remain in secrets/preloaded_users.json."
echo "Distribute individually, require immediate password change/MFA, then move the file to an approved vault or securely delete it."
