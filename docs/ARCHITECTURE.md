# Architecture

## Record-centric interaction model

```text
User authentication
        |
Per-user function/department/facility matrix
        |
Patient search or registration ---- Operational worklists and aggregate dashboards
        |                                      |
Selected longitudinal record                   | open patient context
        |                                      |
Encounter + chart context <---------------------+
        |
Notes | orders/results | flowsheets | medications | referrals | charges | specialty activities
        |
Audit events + workflow events + national/facility interface outbox
```

Clinical APIs require a patient or encounter identifier. Operational worklists may show limited identifiers and status information needed to perform a task; opening clinical detail resolves to the selected longitudinal record.

## Runtime components

- Responsive provider EHR web client
- FastAPI application service
- SQLAlchemy transactional domain model
- PostgreSQL production database; SQLite demonstration profile
- Alembic schema migration chain
- FHIR R4 starter service
- Interface outbox for DHIS2, eIDSR, NHIF/UHI, GePG, eLMIS/MSD, HFR, HRHIS, NIDA, diagnostic systems and devices
- Audit-event service
- Feature-gated integration adapters

## Access model

Job titles are optional provisioning templates. Runtime access is based on the account's saved matrix:

- Functions: what the account can do
- Departments: where the account may work
- Facilities: which organizations the account may access

The matrix supports cross-functional and cross-department personnel while avoiding a proliferation of rigid role profiles.

## Workflow event model

Appointment arrival creates a durable `PATIENT_ARRIVED` event and a one-second transient notification. Order and appointment course changes create history rows rather than overwriting or deleting prior state.

Flowsheet `CHANGE` updates monitoring interval, title or parameters without deleting observations or control events. `STOP` prevents additional observations unless a new flowsheet is started.

## Deferred scope

Patient portal, consumer mobile application and direct patient messaging UI are deferred. The provider EHR and enterprise workflows remain the active scope.
