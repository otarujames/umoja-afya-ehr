#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

command -v openssl >/dev/null 2>&1 || { echo "openssl is required" >&2; exit 2; }
mkdir -p secrets deploy/tls backups
chmod 700 secrets backups

create_secret() {
  local path="$1" bytes="$2"
  if [ ! -s "$path" ]; then
    umask 077
    openssl rand -hex "$bytes" > "$path"
    chmod 600 "$path"
    echo "Created $path"
  else
    echo "Preserved existing $path"
  fi
}

create_secret secrets/postgres_password 32
create_secret secrets/security_secret 64
python scripts/generate_preloaded_users.py --output secrets/preloaded_users.json

if [ ! -f .env ]; then
  cp .env.production.example .env
  chmod 600 .env
  echo "Created .env from .env.production.example"
else
  echo "Preserved existing .env"
fi

cat <<'EOF'

Production secrets are initialized.

Before first start:
1. Edit .env and set UMOJA_PUBLIC_HOST, UMOJA_CORS_ORIGINS and UMOJA_ALLOWED_HOSTS.
2. Protect secrets/ and .env with host-level backup and access controls.
3. For umojaehr.online behind traefik-59qx-traefik-1, run: ./scripts/deploy-vps-traefik.sh
4. For a standalone nginx/TLS host, place fullchain.pem and privkey.pem in deploy/tls/, then run: ./scripts/deploy-production.sh
5. Retrieve the deployment-generated initial credentials from secrets/preloaded_users.json and distribute them individually.
6. Every preloaded user must change the temporary password at first sign-in and complete MFA enrollment.
7. Move the credential manifest to an approved password vault after onboarding; do not leave it in routine operator access.

Do not replace secrets/postgres_password after the database volume is initialized.
Use ./scripts/rotate-database-password.sh for controlled rotation.
EOF
