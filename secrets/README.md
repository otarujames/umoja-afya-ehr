# Runtime secrets

Run `./scripts/init-production.sh` to create:

- `postgres_password`
- `security_secret`
- `bootstrap_token` — random one-time first-run setup token; rotate or delete after initial administrator creation

These files are excluded from the application image and source-control patterns.
Do not copy real secrets into support tickets, screenshots, or release archives.
Do not manually replace `postgres_password` after the PostgreSQL volume has been initialized; use `scripts/rotate-database-password.sh`.
