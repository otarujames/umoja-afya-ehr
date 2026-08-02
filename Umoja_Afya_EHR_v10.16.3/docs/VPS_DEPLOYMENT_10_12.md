# Umoja Afya EHR 10.12.0 — VPS deployment

## Minimum production baseline

- Ubuntu 24.04 LTS or another supported Linux distribution
- Docker Engine with Docker Compose v2
- 4 CPU cores, 8 GB RAM and 30 GB free disk for the default CPU transcription profile
- A DNS hostname pointing to the VPS
- A valid TLS certificate and private key

Do not expose PostgreSQL or the transcription service publicly. The supplied
Compose file publishes only ports 80 and 443 through Nginx.

## First deployment

```bash
unzip Umoja_Afya_Enterprise_EHR_Production_v10.12.0.zip
cd Umoja_Afya_Enterprise_EHR_Production_v10.12.0
chmod +x scripts/*.sh
./scripts/init-production.sh
```

Edit `.env`, replacing the example hostname with the real HTTPS hostname.
Install the TLS certificate as:

```text
deploy/tls/fullchain.pem
deploy/tls/privkey.pem
```

Complete the generated `secrets/preloaded_users.json` only when centrally
provisioning accounts. Never store production passwords in `.env`, Compose YAML,
source control, or chat.

Deploy:

```bash
./scripts/deploy-production.sh
```

The deployment script validates the migration graph, performs a clean image
build, starts dependencies, applies migrations under a PostgreSQL advisory
lock, and waits for application readiness.

## Upgrade from an older release

Back up first:

```bash
./scripts/backup_postgres.sh
```

Copy the existing production `.env`, `secrets/`, `deploy/tls/`, backups, and
named PostgreSQL volume configuration into the new release directory. Then run:

```bash
./scripts/deploy-production.sh
```

Never run `docker compose down -v` during an upgrade. The `-v` option deletes
the database volume.

## Transcription model

Version 10.12 uses `small` as the CPU-VPS default to reduce first-start download
time and memory pressure. Change `UMOJA_WHISPER_MODEL` to `medium` or `large-v3`
only after confirming adequate RAM, disk and clinical validation. The model
service has outbound network access for model retrieval but publishes no host
port and cannot access PostgreSQL through the application public network.

## Verification

```bash
docker compose -f docker-compose.production.yml ps
docker compose -f docker-compose.production.yml logs --tail=200 app proxy db transcription
curl -I https://YOUR_HOSTNAME/
```

Expected results:

- `db` is healthy.
- `app` is healthy and uses image tag `10.12.0`.
- `proxy` is running on ports 80/443.
- `transcription` becomes healthy after its first model download.
- HTTPS responses include HSTS, frame denial, content-type protection,
  cross-origin isolation and restrictive permissions headers.

