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
create_secret secrets/bootstrap_token 32
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
2. Place fullchain.pem and privkey.pem in deploy/tls/.
3. Protect secrets/ and .env with host-level backup and access controls.
4. Run: ./scripts/deploy-production.sh
5. Retrieve one-time user credentials from secrets/preloaded_users.json and distribute them individually.
6. Every preloaded user must change the temporary password at first sign-in and complete MFA enrollment.
7. Delete or archive the credential manifest in an approved password vault after onboarding.

Do not replace secrets/postgres_password after the database volume is initialized.
Use ./scripts/rotate-database-password.sh for controlled rotation.
EOF
