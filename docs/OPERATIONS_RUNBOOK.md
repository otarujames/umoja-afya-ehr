# Operations Runbook

## Start and verify

1. Apply database migration: `alembic upgrade head`.
2. Synchronize approved facilities: `python scripts/bootstrap_reference_data.py`.
3. Complete the token-protected first-run administrator setup in the browser.
4. Rotate `secrets/bootstrap_token` after the administrator is created and keep it protected.
5. Start the application service.
6. Verify `/api/v1/health`, authentication and RBAC denial for an unauthorized workflow.
7. Verify one read-only patient search and one non-clinical workqueue.
8. Check interface event queue, telehealth readiness queue and database connection health.

## Backup

Run `scripts/backup_postgres.sh` from an approved backup host with `DATABASE_URL` set. Store backup and checksum in encrypted government-controlled storage. Test restore on a scheduled basis.

## Downtime

- Announce downtime and activate approved downtime forms.
- Preserve read-only emergency summaries where available.
- Queue low-risk transactions when offline mode is approved.
- Reconcile registrations, orders, administrations, results, charges and discharges after restoration.
- Document discrepancies and obtain clinical sign-off.

## Incident priorities

- **P1:** patient-safety risk, national outage, data breach, identity corruption
- **P2:** major hospital workflow unavailable or critical interface failure
- **P3:** degraded module, work-around available
- **P4:** routine defect, request or optimization

## Release management

Every production release requires regression tests, database migration review, clinical-content sign-off, rollback plan, downtime communication, interface verification and post-release monitoring.
