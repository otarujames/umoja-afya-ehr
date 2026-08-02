# Backup and Restore Control

- PostgreSQL backups must be encrypted, access controlled and monitored.
- At least one copy must be isolated from the production trust boundary.
- Backup success is not sufficient; restore tests must validate schema, row counts, audit continuity and application operation.
- Recovery Point Objective and Recovery Time Objective must be approved by clinical and operational leadership.
- Restore exercises should include reconciliation of queued/offline clinical transactions.

Review scripts: `scripts/backup_postgres.sh` and `scripts/restore_postgres.sh`.
