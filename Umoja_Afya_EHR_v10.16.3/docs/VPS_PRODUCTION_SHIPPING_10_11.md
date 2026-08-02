# Umoja Afya EHR 10.11.0 — VPS Production Shipping Corrections

This release closes the deployment failures observed in v10.10.0.

## Corrected failures

- Alembic graph validation now runs during Docker image build and application prestart. An image with multiple heads, duplicate revisions, missing parents, multiple bases, or cycles cannot ship.
- The activity-lock migration is chained to the multi-country migration, producing one authoritative head: `2c3d4e5f6a7b`.
- Docker image and configuration versions now identify release `10.11.0` rather than the stale `10.7.0` tag.
- The production deploy script performs VPS preflight, builds first, starts PostgreSQL, runs controlled migrations as a one-off job, then starts the application and proxy.
- Production deployment never removes named volumes. Database deletion is not part of an upgrade path.
- Reserved characters in PostgreSQL passwords remain safe because the application builds the SQLAlchemy URL from discrete secret-file fields.
- The application image remains non-root and read-only at runtime.
- The bundled SQLite review snapshot and Python cache files are excluded from the shipping archive.
- Review seeding targets 15,000 synthetic patients.

## VPS deployment

```bash
cd /opt/umoja-afya-ehr
chmod +x scripts/*.sh
./scripts/init-production.sh
# Edit .env and install TLS files.
./scripts/deploy-production.sh
```

Do not run `docker compose down -v` during an installation or upgrade.
