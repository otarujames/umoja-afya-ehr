# Record-Centric Workflow

## Clinical navigation rule

Clinical actions start from patient lookup or registration and operate within a selected longitudinal record. The selected patient context is retained across chart, documentation, orders, results, flowsheets, medication, specialty, telehealth and revenue workflows.

## Worklist rule

Operational worklists may display only the identifiers and status required to perform the task. A user opens the patient record before reviewing full clinical detail or entering clinical documentation.

## Core sequence

```text
Patient lookup / registration
        ↓
Select longitudinal record
        ↓
Select or create encounter
        ↓
Document / order / administer / refer / charge
        ↓
Result, task or status returns to the same record
        ↓
Acknowledge, reconcile, discharge and follow up
```

## Status-history controls

- Orders: hold, resume, cancel and reinstate
- Appointments: confirm, arrive, cancel, reinstate and no-show
- Flowsheets: start, pause, resume, change and stop
- Telehealth: start, pause, resume, complete and cancel
- Notes: draft, sign, cosign and addendum handling

Course changes retain the original transaction and append an actor, reason and timestamp.

## Summary screens

Command-center and analytics screens use aggregate counts and indicators. The provider patient tracker is an operational exception: it displays current patient flow status but routes clinical detail into the selected chart.
