# Control Evidence Index

| Control area | Primary evidence |
|---|---|
| Authentication and sessions | `backend/app/security.py`, `backend/app/routers/auth.py`, `user_session` table |
| User access | `backend/app/access_control.py`, user access grants, administration audit |
| Emergency access | `/api/v1/break-glass`, `break_glass_access` table |
| Audit | `backend/app/routers/audit.py`, `audit_event` records, `config/audit-events.yml` |
| Workqueue integrity | `work_queue_item`, `work_queue_event`, workqueue API tests |
| Walk-in workflow | `walk_in_episode`, workflow notifications, `config/walk-in-workflow.yml` |
| Data integrity | Alembic migrations, relational constraints, clinical state histories |
| Security headers and limits | `backend/app/middleware.py`, automated tests |
| Network separation | production/review Compose networks and Nginx profile |
| Availability | container health checks, backup/restore scripts, continuity documentation |
| Secure development | automated tests, YAML/OpenAPI validation, release checksum |
| Privacy | consent/proxy fields, patient-context workflows, DPIA template |
