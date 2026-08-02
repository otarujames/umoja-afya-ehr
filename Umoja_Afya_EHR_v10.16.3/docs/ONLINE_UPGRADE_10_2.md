# Online Upgrade to 10.7.0

This release removes runtime demonstration credentials and introduces secure first-run administrator setup.

## Before upgrading

1. Back up PostgreSQL and the existing `/opt/umoja-afya` directory.
2. Preserve `.env`, `secrets/postgres_password`, `secrets/security_secret`, TLS certificates and the PostgreSQL Docker volume.
3. Generate a new one-time setup token when the file is absent:

```bash
mkdir -p secrets
chmod 700 secrets
openssl rand -hex 32 > secrets/bootstrap_token
chmod 600 secrets/bootstrap_token
```

## Deploy

```bash
cd /opt/umoja-afya
docker compose -f docker-compose.production.yml down
# Replace application source with the 10.7.0 release while preserving .env, secrets, TLS and volumes.
docker compose -f docker-compose.production.yml up -d --build --remove-orphans
docker compose -f docker-compose.production.yml logs --tail=200 app proxy db transcription
```

## Account behavior

- Existing legitimate accounts remain in the database.
- Older demonstration accounts are disabled only when their username, display name and role match the legacy seeded signatures.
- When no active administrator remains, the login page displays Secure First-Run Setup.
- Read `secrets/bootstrap_token`, create the authorized administrator, then rotate the token and keep the secret file protected.
- The application never displays or preloads the administrator password.

## Browser cache

After deployment, perform a hard refresh or clear the old application service-worker cache so the 10.7.0 frontend loads immediately.
