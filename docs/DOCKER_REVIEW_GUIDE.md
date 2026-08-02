# Docker Review Guide — 10.7.0

No fixed usernames, database passwords, application secrets or user passwords are embedded in the archive or frontend. Initialization generates a protected local account roster.

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

Open `http://localhost:8000`, then use a country-appropriate account from `secrets/review_preloaded_users.json`. The file includes a global superuser and role-specific country accounts. Nothing is prefilled in the browser.

Every generated account requires an immediate password change and MFA enrollment. Move the credential roster into an approved password vault after account distribution. Review clinical records remain synthetic.
