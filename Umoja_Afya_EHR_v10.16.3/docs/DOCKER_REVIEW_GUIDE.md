# Docker Review Guide — 10.7.0

No usernames, administrator accounts, database passwords, application secrets or user passwords are preloaded.

## Linux/macOS

```bash
chmod +x scripts/*.sh
./scripts/init-review.sh
docker compose -f docker-compose.review.yml up --build
```

## Windows PowerShell

```powershell
Set-ExecutionPolicy -Scope Process Bypass
./scripts/init-review.ps1
docker compose -f docker-compose.review.yml up --build
```

Open `http://localhost:8000`. The first-run screen asks for the random setup token printed by the initialization script, then lets the authorized installer choose the first administrator username and password. Nothing is prefilled.

After setup, rotate `secrets/review_bootstrap_token` and keep it protected. Review clinical records are synthetic; accounts are created by the reviewer through the normal IT administration workflow.
