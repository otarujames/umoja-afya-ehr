#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 2; }
mkdir -p secrets
chmod 700 secrets
create_secret(){ local path="$1" bytes="$2"; if [ ! -s "$path" ]; then umask 077; openssl rand -hex "$bytes" > "$path"; chmod 600 "$path"; echo "Created $path"; fi; }
create_secret secrets/review_postgres_password 32
create_secret secrets/review_security_secret 64
python scripts/generate_preloaded_users.py --output secrets/review_preloaded_users.json
echo
echo "Review secrets and the preloaded user roster are ready."
echo "Temporary credentials: secrets/review_preloaded_users.json"
echo "All accounts require a password change and MFA enrollment."
