# Online Upgrade to 11.0.0

This release removes the legacy setup-token path and uses deployment-generated, role-scoped account provisioning.

## Before upgrading

1. Back up PostgreSQL and the existing `/opt/umoja-afya` directory.
2. Preserve `.env`, `secrets/postgres_password`, `secrets/security_secret`, TLS certificates and the PostgreSQL Docker volume.
3. Generate or upgrade the protected account roster without changing existing passwords:

```bash
./scripts/init-production.sh
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
- `platform.admin` is the manifest-designated global superuser and is repaired to all active countries, facilities, functions and departments.
- Country-scoped administrators and operational roles are synchronized from `secrets/preloaded_users.json`.
- Existing database passwords are preserved during an upgrade; the browser never displays or preloads credentials.

## Browser cache

After deployment, perform a hard refresh or clear the old application service-worker cache so the 10.7.0 frontend loads immediately.
