# Release 4.0 Data Model

## Identity and care delivery

- `patient` — national MPI identity, facility MRN, demographics, contact, coverage and consent status
- `encounter` — clinical/operational visit, location, status, service, provider and discharge
- `facility` — institution and campus registry
- `appointment` and `referral` — access and closed-loop referral workflows
- `bed` — capacity, assignment, occupancy and EVS state
- `telehealth_session` — patient-linked remote visit, modality, schedule, provider, lifecycle controls and secure join code

## Clinical record

- `clinical_note` — draft, signed and cosign-aware documentation
- `clinical_order` and `diagnostic_result` — CPOE and results
- `flowsheet`, `flowsheet_event`, `flowsheet_observation` — timed monitoring and complete control history
- `medication_order`, `medication_administration` — pharmacist verification and eMAR
- `module_activity` — configurable patient/encounter-linked specialty and ancillary workqueue

## Enterprise operations

- `work_item` — Clinical and operational work queues
- `charge`, `claim`, `payment` — revenue cycle
- `inventory_item`, `inventory_transaction` — supply chain
- `quality_incident` — safety reporting
- `public_health_event` — surveillance and registries
- `integration_event` — transactional outbox for national/external interfaces

## Security and governance

- `user_account` — authenticated user, role, facility and MFA requirement
- `audit_event` — user, action, resource, patient, facility, outcome and details

The full 28-table development reference is generated in `database/schema.sql`. PostgreSQL deployments are created and upgraded exclusively through the Alembic revisions under `migrations/versions/`.
