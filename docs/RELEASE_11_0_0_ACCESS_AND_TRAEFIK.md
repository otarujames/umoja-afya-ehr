# Umoja Afya EHR 11.0.0 — Access and Traefik Deployment Repair

## Corrected login defect

The access-control service queried `Facility` without importing the model. Release 11.0.0 imports `Facility` explicitly, preventing the login access-matrix path from raising `NameError`.

## Tokenless deployment provisioning

The legacy browser setup flow has been removed from the frontend, API, OpenAPI description, runtime settings, Docker Compose files and initialization scripts. Release archives do not contain account passwords.

`scripts/init-production.sh` generates `secrets/preloaded_users.json` locally with mode `0600`. The roster contains:

- `platform.admin`, the single global superuser with all active countries, facilities, functions and departments.
- Country-scoped administrator, registration, physician, nurse, pharmacy, laboratory, finance and operations accounts for Tanzania, Kenya, Nigeria, Pakistan and Rwanda.

Every generated account requires an immediate password change and MFA enrollment. Store the generated credentials in an approved password vault and distribute them individually. Do not commit the generated roster to Git.

Provisioning is idempotent. Existing account passwords and existing manifest passwords are not reset by normal restart or upgrade. The access matrix is repaired to the authoritative role scope on startup.

## Deploy to umojaehr.online

The VPS already owns ports 80 and 443 through `traefik-59qx-traefik-1`. Do not start the bundled nginx proxy.

```bash
cd /opt/umoja-afya-ehr
chmod +x scripts/*.sh
./scripts/init-production.sh
./scripts/deploy-vps-traefik.sh
```

The deployment script:

1. Requires the exact public hostname `umojaehr.online`.
2. Verifies `traefik-59qx-traefik-1` is running.
3. Reuses or creates the external `traefik` Docker network.
4. Builds the application and transcription images.
5. Runs migrations and deployment provisioning before app startup.
6. Starts the application without the bundled proxy or orphan containers.
7. Verifies internal readiness and `https://umojaehr.online/api/v1/health`.

If the public check fails, inspect:

```bash
docker logs --tail=200 traefik-59qx-traefik-1
docker compose --project-name umoja-afya-ehr \
  -f docker-compose.production.yml \
  -f docker-compose.traefik.yml logs --tail=250 app
```

Traefik labels match the `umojaehr.online` host through `websecure`, use the `letsencrypt` resolver, and forward to container port 8000.

## Upgrade behavior

Back up PostgreSQL, `.env` and `secrets/` before upgrading. Keep the existing Docker volumes and existing `secrets/preloaded_users.json`; the generator upgrades its schema without changing stored passwords. After deployment, confirm `platform.admin` can change context across all five countries and that a country administrator cannot cross its assigned country boundary.
